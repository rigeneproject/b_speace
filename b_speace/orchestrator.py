"""BioOrchestrator — top-level B-SPEACE runtime wiring bio-electric, organoid,
and q_speace hybrid quantum layers under explicit safety & Sevo gates (T001).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .bioelectric import (
    BioSignalDecoder,
    BioSignalEncoder,
    EncodedBioFeatures,
    PopulationRateCodec,
)
from .interop import (
    BaseBioQuantumAdapter,
    BioQuantumAdapter,
    HybridBindingSpec,
    HybridTickResult,
    QuantumKernelPort,
    make_quantum_kernel_adapter,
)
from .organoid import (
    OrganoidInterface,
    OrganoidLifecycleState,
    SimulatedOrganoidAdapter,
    StimulationCommand,
)


@dataclass(frozen=True)
class BioTickReport:
    """Single closed-loop tick record combining organoid, bio-signal, and quantum data."""

    tick: int
    total_spikes: int
    firing_rate_hz: float
    synchrony_index: float
    shannon_entropy_bits: float
    coherence_phi: float
    sevo: float
    estimated_energy_w: float
    gate_blocked: bool
    backend_name: str
    viability_index: float


class BioOrchestrator:
    """Async orchestrator running Wetware-in-the-loop <-> Quantum hybrid ticks."""

    def __init__(
        self,
        organoid: OrganoidInterface | None = None,
        encoder: BioSignalEncoder | None = None,
        decoder: BioSignalDecoder | None = None,
        bio_quantum: BioQuantumAdapter | None = None,
        *,
        num_channels: int = 4,
        record_duration_ms: float = 2.0,
        prefer_qspeace: bool = True,
        seed: int | None = None,
    ) -> None:
        if num_channels < 1:
            raise ValueError(f"num_channels must be >= 1 (got {num_channels})")
        if not math.isfinite(record_duration_ms) or record_duration_ms <= 0.0:
            raise ValueError(
                f"record_duration_ms must be finite and > 0 (got {record_duration_ms})"
            )

        self._organoid: OrganoidInterface = organoid or SimulatedOrganoidAdapter(
            num_channels=num_channels,
            seed=seed,
        )
        codec = PopulationRateCodec(max_pulse_amplitude_ua=10.0, default_pulse_duration_ms=1.0)
        self._encoder: BioSignalEncoder = encoder or codec
        self._decoder: BioSignalDecoder = decoder or codec
        self._bio_quantum: BioQuantumAdapter | None = bio_quantum
        self._prefer_qspeace = prefer_qspeace
        self._seed = seed
        self._record_duration_ms = float(record_duration_ms)
        self._tick_count = 0
        self._last_feedback: tuple[float, ...] | None = None
        self._history: list[BioTickReport] = []

    @property
    def organoid(self) -> OrganoidInterface:
        return self._organoid

    @property
    def history(self) -> list[BioTickReport]:
        return list(self._history)

    def _ensure_quantum_adapter(self) -> BioQuantumAdapter:
        if self._bio_quantum is not None:
            return self._bio_quantum
        channels = self._organoid.channels()
        bound_chs = channels[: min(len(channels), 8)]
        channel_to_role = tuple((ch.channel_id, f"q_{ch.channel_id}") for ch in bound_chs)
        entangled_pairs = tuple(
            (bound_chs[i].channel_id, bound_chs[i + 1].channel_id)
            for i in range(0, len(bound_chs) - 1, 2)
        )
        binding = HybridBindingSpec(
            channel_to_role=channel_to_role,
            entangled_pairs=entangled_pairs,
            max_qubits=max(len(bound_chs), 1),
        )
        kernel: QuantumKernelPort = make_quantum_kernel_adapter(
            binding=binding,
            prefer_qspeace=self._prefer_qspeace,
            seed=self._seed,
        )
        self._bio_quantum = BaseBioQuantumAdapter(kernel=kernel)
        return self._bio_quantum

    async def start(self) -> None:
        """Connect and calibrate the underlying OrganoidInterface."""
        state = self._organoid.lifecycle_state()
        if state is OrganoidLifecycleState.OFFLINE:
            await self._organoid.connect()
        if self._organoid.lifecycle_state() is OrganoidLifecycleState.CALIBRATING:
            await self._organoid.calibrate()
        self._ensure_quantum_adapter()

    async def stop(self) -> None:
        """Safely shut down the OrganoidInterface."""
        await self._organoid.shutdown()

    def _build_command(self) -> StimulationCommand:
        channels = self._organoid.channels()
        n_ch = len(channels)
        if self._last_feedback is not None and len(self._last_feedback) == n_ch:
            control = self._last_feedback
        else:
            control = tuple(0.4 for _ in range(n_ch))

        pulses = self._decoder.decode(control, n_ch)
        env = self._organoid.safety_envelope
        if pulses:
            # Pick target channels from decoded pulses and bound safely within envelope.
            target_indices = sorted({idx for p in pulses for idx in p.channel_indices})
            amp = min(
                max(p.amplitude_ua for p in pulses),
                env.max_current_ua * 0.5,
            )
            dur = min(pulses[0].duration_ms, env.max_pulse_duration_ms * 0.5)
        else:
            target_indices = [0]
            amp = min(2.0, env.max_current_ua * 0.25)
            dur = min(1.0, env.max_pulse_duration_ms * 0.25)

        targets = tuple(channels[i].channel_id for i in target_indices if channels[i].active)
        if not targets:
            targets = (channels[0].channel_id,)
        # Bound amplitude by both current limit and per-phase charge-density envelope.
        min_area = min(channels[i].surface_area_cm2 for i in target_indices)
        max_safe_charge_uc = env.max_charge_density_uc_cm2 * min_area * 0.8
        phase_ms = 0.5 * dur
        max_amp_from_charge = max_safe_charge_uc / (phase_ms * 1e-3)
        amp = min(amp, max_amp_from_charge)
        # Ensure voltage respects envelope (approx V = I * R_mean, capped safely).
        mean_imp_kohm = sum(channels[i].impedance_kohm for i in target_indices) / max(
            len(target_indices), 1
        )
        voltage_mv = min(amp * mean_imp_kohm * 0.5, env.max_voltage_mv * 0.5)
        return StimulationCommand(
            target_channels=targets,
            amplitude_ua=float(amp),
            voltage_mv=float(voltage_mv),
            duration_ms=float(dur),
            frequency_hz=min(10.0, env.max_frequency_hz),
            biphasic=True,
        )

    async def tick(self, *, enforce_sevo_gate: bool = True) -> BioTickReport:
        """Execute a single closed-loop bio -> organoid -> quantum tick."""
        if self._organoid.lifecycle_state() is not OrganoidLifecycleState.READY:
            await self.start()
        bio_quantum = self._ensure_quantum_adapter()
        command = self._build_command()
        step_res = await self._organoid.closed_loop_step(command, self._record_duration_ms)
        features: EncodedBioFeatures = self._encoder.encode(step_res.recording.frames)

        # Construct bounded utility / informational entropy proxy for Sevo evaluation.
        delta_entropy = max(features.shannon_entropy_bits, 0.25)
        delta_utility = float(
            max(
                0.5 + features.synchrony_index * 1.5 + 0.1 * step_res.recording.total_spikes,
                delta_entropy * 2.0,
            )
        )
        hybrid: HybridTickResult = bio_quantum.step_hybrid(
            tick=self._tick_count,
            features=features,
            delta_utility=delta_utility,
            delta_entropy_info=delta_entropy,
            num_spikes=step_res.recording.total_spikes,
            enforce_gate=enforce_sevo_gate,
        )
        if not hybrid.gate_blocked:
            self._last_feedback = hybrid.feedback_modulation

        report = BioTickReport(
            tick=self._tick_count,
            total_spikes=step_res.recording.total_spikes,
            firing_rate_hz=features.firing_rate_hz,
            synchrony_index=features.synchrony_index,
            shannon_entropy_bits=features.shannon_entropy_bits,
            coherence_phi=hybrid.coherence_phi,
            sevo=hybrid.sevo.sevo,
            estimated_energy_w=hybrid.sevo.estimated_energy_w,
            gate_blocked=hybrid.gate_blocked,
            backend_name=hybrid.backend_name,
            viability_index=step_res.health.viability_index,
        )
        self._history.append(report)
        self._tick_count += 1
        return report

    async def run(self, ticks: int, *, enforce_sevo_gate: bool = True) -> list[BioTickReport]:
        """Run ``ticks`` closed-loop ticks and return their reports."""
        if ticks < 0:
            raise ValueError(f"ticks must be >= 0 (got {ticks})")
        await self.start()
        out: list[BioTickReport] = []
        for _ in range(ticks):
            out.append(await self.tick(enforce_sevo_gate=enforce_sevo_gate))
        return out

    def report(self) -> dict[str, float | int | str]:
        """Return aggregate telemetry summary across all completed ticks."""
        if not self._history:
            return {
                "ticks": 0,
                "mean_coherence_phi": 0.0,
                "mean_sevo": 0.0,
                "blocked_ticks": 0,
                "backend": "uninitialized",
            }
        n = len(self._history)
        return {
            "ticks": n,
            "total_spikes": sum(r.total_spikes for r in self._history),
            "mean_coherence_phi": sum(r.coherence_phi for r in self._history) / n,
            "mean_sevo": sum(r.sevo for r in self._history) / n,
            "blocked_ticks": sum(1 for r in self._history if r.gate_blocked),
            "backend": self._history[-1].backend_name,
        }
