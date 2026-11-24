"""Abstract base adapter, safety gate, and in-silico MEA twin for organoids (T001)."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Sequence

import numpy as np

from b_speace.bioelectric.adapters import FitzHughNagumoAdapter
from b_speace.bioelectric.protocols import BioElectricSimulator
from b_speace.bioelectric.types import StimulationPulse

from .protocols import WetwareSafetyGate, WetwareTelemetrySink
from .types import (
    ClosedLoopStepResult,
    ElectrodeChannel,
    MEARecording,
    OrganoidCalibrationError,
    OrganoidHealthError,
    OrganoidHealthSnapshot,
    OrganoidLifecycleState,
    OrganoidSafetyViolationError,
    OrganoidUnavailableError,
    StimulationCommand,
    WetwareSafetyEnvelope,
)


class ChargeDensitySafetyGate:
    """Fail-closed WetwareSafetyGate enforcing electrical & viability bounds."""

    def __init__(self, envelope: WetwareSafetyEnvelope | None = None) -> None:
        self.envelope: WetwareSafetyEnvelope = envelope or WetwareSafetyEnvelope()
        self.envelope.validate()

    def validate_command(
        self,
        command: StimulationCommand,
        channels: Sequence[ElectrodeChannel],
        health: OrganoidHealthSnapshot,
    ) -> None:
        command.validate()
        env = self.envelope

        if not health.safe_to_stimulate:
            raise OrganoidHealthError("organoid health snapshot marks substrate unsafe")
        if not (env.temp_min_c <= health.temperature_c <= env.temp_max_c):
            raise OrganoidHealthError(
                f"temperature {health.temperature_c:.2f} C outside "
                f"[{env.temp_min_c}, {env.temp_max_c}]"
            )
        if not (env.ph_min <= health.ph <= env.ph_max):
            raise OrganoidHealthError(f"pH {health.ph:.2f} outside [{env.ph_min}, {env.ph_max}]")
        if health.viability_index < env.min_viability:
            raise OrganoidHealthError(
                f"viability {health.viability_index:.3f} < min_viability {env.min_viability:.3f}"
            )

        if env.require_biphasic and not command.biphasic:
            raise OrganoidSafetyViolationError("monophasic stimulation rejected by safety envelope")
        if abs(command.voltage_mv) > env.max_voltage_mv:
            raise OrganoidSafetyViolationError(
                f"|voltage_mv| {abs(command.voltage_mv)} > max {env.max_voltage_mv}"
            )
        if abs(command.amplitude_ua) > env.max_current_ua:
            raise OrganoidSafetyViolationError(
                f"|amplitude_ua| {abs(command.amplitude_ua)} > max {env.max_current_ua}"
            )
        if command.duration_ms > env.max_pulse_duration_ms:
            raise OrganoidSafetyViolationError(
                f"duration_ms {command.duration_ms} > max {env.max_pulse_duration_ms}"
            )
        if command.frequency_hz > env.max_frequency_hz:
            raise OrganoidSafetyViolationError(
                f"frequency_hz {command.frequency_hz} > max {env.max_frequency_hz}"
            )

        by_id = {ch.channel_id: ch for ch in channels}
        charge_uc = command.charge_per_phase_uc()
        for cid in command.target_channels:
            ch = by_id.get(cid)
            if ch is None:
                raise OrganoidSafetyViolationError(f"unknown electrode channel: {cid!r}")
            if not ch.active:
                raise OrganoidSafetyViolationError(f"electrode channel {cid!r} is inactive")
            charge_density = charge_uc / ch.surface_area_cm2
            if charge_density > env.max_charge_density_uc_cm2:
                raise OrganoidSafetyViolationError(
                    f"channel {cid!r} charge density {charge_density:.2f} uC/cm^2 "
                    f"> max {env.max_charge_density_uc_cm2:.2f} uC/cm^2"
                )


class InMemoryTelemetrySink:
    """Simple in-memory WetwareTelemetrySink for logging and tests."""

    def __init__(self) -> None:
        self.recordings: list[MEARecording] = []
        self.health_snapshots: list[OrganoidHealthSnapshot] = []

    def emit_recording(self, recording: MEARecording) -> None:
        self.recordings.append(recording)

    def emit_health(self, health: OrganoidHealthSnapshot) -> None:
        self.health_snapshots.append(health)


class BaseOrganoidAdapter(ABC):
    """Template base class enforcing lifecycle transitions and safety interlocks.

    Concrete wetware adapters (in-silico twins or future lab MEA drivers)
    subclass this and implement the protected transport/hardware hooks:
    ``_on_connect``, ``_on_calibrate``, ``_dispatch_stimulation``,
    ``_acquire_recording``, ``_measure_health``, and ``_on_shutdown``.
    """

    adapter_name: str = "abstract_organoid"
    is_simulated: bool = True
    supports_closed_loop: bool = True

    def __init__(
        self,
        safety_gate: WetwareSafetyGate | None = None,
        telemetry_sink: WetwareTelemetrySink | None = None,
    ) -> None:
        self._safety_gate: WetwareSafetyGate = safety_gate or ChargeDensitySafetyGate()
        self.safety_envelope: WetwareSafetyEnvelope = self._safety_gate.envelope
        self._telemetry = telemetry_sink
        self._state: OrganoidLifecycleState = OrganoidLifecycleState.OFFLINE
        self._channels: tuple[ElectrodeChannel, ...] = ()

    def lifecycle_state(self) -> OrganoidLifecycleState:
        return self._state

    def channels(self) -> tuple[ElectrodeChannel, ...]:
        return self._channels

    async def connect(self) -> None:
        if self._state is OrganoidLifecycleState.SHUTDOWN:
            raise OrganoidUnavailableError("cannot connect after shutdown")
        if self._state in (OrganoidLifecycleState.CALIBRATING, OrganoidLifecycleState.READY):
            return
        chs = tuple(await self._on_connect())
        if not chs:
            self._state = OrganoidLifecycleState.FAULT
            raise OrganoidCalibrationError("connect returned zero electrode channels")
        for ch in chs:
            ch.validate()
        self._channels = chs
        self._state = OrganoidLifecycleState.CALIBRATING

    async def calibrate(self) -> OrganoidHealthSnapshot:
        if self._state not in (
            OrganoidLifecycleState.CALIBRATING,
            OrganoidLifecycleState.READY,
        ):
            raise OrganoidUnavailableError(
                f"cannot calibrate from lifecycle state {self._state.value!r}"
            )
        self._state = OrganoidLifecycleState.CALIBRATING
        snap = await self._on_calibrate()
        if snap.active_channels == 0 or snap.viability_index < self.safety_envelope.min_viability:
            self._state = OrganoidLifecycleState.FAULT
            raise OrganoidCalibrationError(
                f"calibration failed: active_channels={snap.active_channels}, "
                f"viability={snap.viability_index:.3f}"
            )
        self._state = OrganoidLifecycleState.READY
        ready_snap = OrganoidHealthSnapshot(
            lifecycle=self._state,
            temperature_c=snap.temperature_c,
            ph=snap.ph,
            viability_index=snap.viability_index,
            mean_impedance_kohm=snap.mean_impedance_kohm,
            active_channels=snap.active_channels,
            total_channels=snap.total_channels,
            safe_to_stimulate=snap.safe_to_stimulate,
        )
        if self._telemetry is not None:
            self._telemetry.emit_health(ready_snap)
        return ready_snap

    async def stimulate(self, command: StimulationCommand) -> None:
        if self._state is not OrganoidLifecycleState.READY:
            raise OrganoidUnavailableError(
                f"cannot stimulate from lifecycle state {self._state.value!r}"
            )
        snap = await self.health()
        self._safety_gate.validate_command(command, self._channels, snap)
        self._state = OrganoidLifecycleState.STIMULATING
        try:
            await self._dispatch_stimulation(command)
        finally:
            if self._state is OrganoidLifecycleState.STIMULATING:
                self._state = OrganoidLifecycleState.READY

    async def record(self, duration_ms: float) -> MEARecording:
        if self._state not in (
            OrganoidLifecycleState.READY,
            OrganoidLifecycleState.STIMULATING,
        ):
            raise OrganoidUnavailableError(
                f"cannot record from lifecycle state {self._state.value!r}"
            )
        if not math.isfinite(duration_ms) or duration_ms <= 0.0:
            raise OrganoidSafetyViolationError(
                f"duration_ms must be finite and > 0 (got {duration_ms!r})"
            )
        rec = await self._acquire_recording(duration_ms)
        if self._telemetry is not None:
            self._telemetry.emit_recording(rec)
        return rec

    async def closed_loop_step(
        self, command: StimulationCommand, record_duration_ms: float
    ) -> ClosedLoopStepResult:
        await self.stimulate(command)
        rec = await self.record(record_duration_ms)
        snap = await self.health()
        return ClosedLoopStepResult(
            command=command,
            recording=rec,
            health=snap,
            safety_approved=True,
            blocked_reason=None,
        )

    async def health(self) -> OrganoidHealthSnapshot:
        snap = await self._measure_health()
        if self._telemetry is not None:
            self._telemetry.emit_health(snap)
        return snap

    async def shutdown(self) -> None:
        if self._state is OrganoidLifecycleState.SHUTDOWN:
            return
        await self._on_shutdown()
        self._state = OrganoidLifecycleState.SHUTDOWN

    @abstractmethod
    async def _on_connect(self) -> Sequence[ElectrodeChannel]:
        """Connect to hardware/simulator and discover electrode channels."""

    @abstractmethod
    async def _on_calibrate(self) -> OrganoidHealthSnapshot:
        """Run impedance and environmental checks."""

    @abstractmethod
    async def _dispatch_stimulation(self, command: StimulationCommand) -> None:
        """Apply a safety-validated stimulation command."""

    @abstractmethod
    async def _acquire_recording(self, duration_ms: float) -> MEARecording:
        """Acquire multi-channel MEA frames over ``duration_ms``."""

    @abstractmethod
    async def _measure_health(self) -> OrganoidHealthSnapshot:
        """Collect current culture environmental & viability telemetry."""

    @abstractmethod
    async def _on_shutdown(self) -> None:
        """Disarm electrodes and release resources."""


class SimulatedOrganoidAdapter(BaseOrganoidAdapter):
    """Deterministic in-silico MEA organoid twin backed by a BioElectricSimulator.

    Provides a zero-hardware Wetware-in-the-loop testbed adhering strictly to
    :class:`OrganoidInterface` and :class:`WetwareSafetyEnvelope`.
    """

    adapter_name = "simulated_mea_organoid"
    is_simulated = True
    supports_closed_loop = True

    def __init__(
        self,
        num_channels: int = 8,
        simulator: BioElectricSimulator | None = None,
        safety_gate: WetwareSafetyGate | None = None,
        telemetry_sink: WetwareTelemetrySink | None = None,
        temperature_c: float = 37.0,
        ph: float = 7.38,
        viability_index: float = 0.96,
        seed: int | None = None,
    ) -> None:
        super().__init__(safety_gate=safety_gate, telemetry_sink=telemetry_sink)
        if simulator is not None:
            self._sim: BioElectricSimulator = simulator
        else:
            self._sim = FitzHughNagumoAdapter(
                num_channels=num_channels,
                dt_ms=0.25,
                channel_ids=tuple(f"mea_{i:02d}" for i in range(num_channels)),
                seed=seed,
            )
        self._seed = seed
        self._rng = np.random.default_rng(seed)
        self._temperature_c = float(temperature_c)
        self._ph = float(ph)
        self._viability_index = float(viability_index)
        self._pending_pulses: list[StimulationPulse] = []

    def set_environment(
        self,
        *,
        temperature_c: float | None = None,
        ph: float | None = None,
        viability_index: float | None = None,
    ) -> None:
        """Inject environmental conditions (e.g., for fault/safety drill testing)."""
        if temperature_c is not None:
            self._temperature_c = float(temperature_c)
        if ph is not None:
            self._ph = float(ph)
        if viability_index is not None:
            self._viability_index = float(viability_index)

    async def _on_connect(self) -> Sequence[ElectrodeChannel]:
        self._sim.reset(seed=self._seed)
        channels: list[ElectrodeChannel] = []
        for idx, cid in enumerate(self._sim.channel_ids):
            impedance = float(45.0 + self._rng.uniform(0.0, 15.0))
            channels.append(
                ElectrodeChannel(
                    channel_id=cid,
                    index=idx,
                    impedance_kohm=impedance,
                    surface_area_cm2=7.0e-5,  # ~94 um pad, realistic MEA site
                    active=True,
                )
            )
        return channels

    async def _on_calibrate(self) -> OrganoidHealthSnapshot:
        return await self._measure_health()

    async def _dispatch_stimulation(self, command: StimulationCommand) -> None:
        id_to_idx = {ch.channel_id: ch.index for ch in self._channels}
        indices = tuple(id_to_idx[cid] for cid in command.target_channels)
        t_now = self._sim.state_snapshot().time_ms
        self._pending_pulses.append(
            StimulationPulse(
                channel_indices=indices,
                amplitude_ua=command.amplitude_ua,
                duration_ms=command.duration_ms,
                start_ms=t_now,
                frequency_hz=command.frequency_hz,
                biphasic=command.biphasic,
            )
        )

    async def _acquire_recording(self, duration_ms: float) -> MEARecording:
        steps = max(1, int(math.ceil(duration_ms / self._sim.dt_ms)))
        pulses = tuple(self._pending_pulses)
        self._pending_pulses.clear()
        frames = tuple(self._sim.run(steps=steps, pulses=pulses))

        n_ch = self._sim.num_channels
        counts = [0] * n_ch
        energy_uj = 0.0
        for frame in frames:
            for i, fired in enumerate(frame.spike_mask):
                if fired:
                    counts[i] += 1
            # uW * ms * 1e-3 = uJ
            energy_uj += frame.instantaneous_power_uw * self._sim.dt_ms * 1e-3

        sample_rate_hz = 1000.0 / self._sim.dt_ms
        mean_snr_db = float(12.0 + 3.0 * self._viability_index)
        return MEARecording(
            timestamp_ms=frames[-1].timestamp_ms,
            sample_rate_hz=sample_rate_hz,
            channel_ids=self._sim.channel_ids,
            frames=frames,
            spike_counts=tuple(counts),
            mean_snr_db=mean_snr_db,
            estimated_energy_uj=energy_uj,
        )

    async def _measure_health(self) -> OrganoidHealthSnapshot:
        active = sum(1 for c in self._channels if c.active)
        total = len(self._channels)
        mean_imp = (
            float(np.mean([c.impedance_kohm for c in self._channels])) if self._channels else 0.0
        )
        env = self.safety_envelope
        safe = (
            active > 0
            and env.temp_min_c <= self._temperature_c <= env.temp_max_c
            and env.ph_min <= self._ph <= env.ph_max
            and self._viability_index >= env.min_viability
            and self._state not in (OrganoidLifecycleState.FAULT, OrganoidLifecycleState.SHUTDOWN)
        )
        return OrganoidHealthSnapshot(
            lifecycle=self._state,
            temperature_c=self._temperature_c,
            ph=self._ph,
            viability_index=self._viability_index,
            mean_impedance_kohm=mean_imp,
            active_channels=active,
            total_channels=total,
            safe_to_stimulate=safe,
        )

    async def _on_shutdown(self) -> None:
        self._pending_pulses.clear()
