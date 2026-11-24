"""Adapters bridging B-SPEACE bio-electric/organoid layers with q_speace (T001).

Provides:
- :class:`StandaloneQuantumKernelAdapter`: self-contained deterministic numpy
  hybrid kernel implementing :class:`QuantumKernelPort` without requiring
  ``q_speace`` to be installed.
- :class:`QSpeaceKernelAdapter`: lazy-importing native adapter binding directly
  to ``q_speace.QuantumNeuralBridge``, ``BrainQuantumCircuit``,
  ``QuantumBrainSimulator``, and ``QuantumCostModel``.
- :class:`BaseBioQuantumAdapter`: concrete high-level bridge converting
  :class:`EncodedBioFeatures` into :class:`QuantumBioPacket` and invoking any
  :class:`QuantumKernelPort`.
"""

from __future__ import annotations

import importlib
import math
from typing import Any

import numpy as np

from b_speace.bioelectric.types import EncodedBioFeatures

from .protocols import QuantumKernelPort
from .types import (
    HybridBindingSpec,
    HybridTickResult,
    InteropError,
    InteropValidationError,
    QuantumBioPacket,
    SevoAssessment,
)


def _compute_sevo(delta_utility: float, delta_entropy_info: float) -> float:
    """Fail-closed entropic efficiency Sevo = dU / dS_info (mirrors q_speace)."""
    if not (math.isfinite(delta_utility) and math.isfinite(delta_entropy_info)):
        return float("-inf")
    if delta_entropy_info <= 0.0:
        return float("-inf") if delta_utility > 0.0 else 0.0
    return float(delta_utility / delta_entropy_info)


def _estimate_energy_watts(
    num_qubits: int,
    num_gates: int,
    entanglement_depth: int,
    num_spikes: int,
) -> float:
    """Baseline energy proxy aligned with q_speace QuantumCostModel (T10/T205)."""
    base = (
        num_qubits * 0.5
        + num_gates * 0.001
        + entanglement_depth * 0.01
        + max(num_spikes, 0) * 0.001
    )
    return float(base * 30.94)


def _feedback_from_measurements(
    measurements: list[tuple[str, str]],
    activities: tuple[float, ...],
    coherence_phi: float,
) -> tuple[float, ...]:
    """Compute bounded [0, 1] feedback modulation vector from classical measurement bits."""
    scale = min(max(0.25 + 0.5 * min(coherence_phi, 1.5) / 1.5, 0.0), 1.0)
    modulation: list[float] = []
    for (_, bit), act in zip(measurements, activities, strict=True):
        bit_boost = 0.65 if bit == "1" else 0.25
        val = min(max(scale * (0.5 * bit_boost + 0.5 * act), 0.0), 1.0)
        modulation.append(float(val))
    return tuple(modulation)


class StandaloneQuantumKernelAdapter:
    """Zero-dependency deterministic numpy hybrid kernel implementing QuantumKernelPort.

    Performs single-qubit RY/RZ rotations and pairwise CNOT entangling gates on a
    complex state vector, computes a bipartite mutual-information ``phi_proxy``,
    and evaluates the same metabolic/Sevo gate contract as ``q_speace``.
    """

    backend_name: str = "standalone_numpy_quantum"

    def __init__(self, binding: HybridBindingSpec, seed: int | None = None) -> None:
        binding.validate()
        self.binding: HybridBindingSpec = binding
        self._rng = np.random.default_rng(seed)
        self._role_order: tuple[str, ...] = tuple(role for _, role in binding.channel_to_role)
        self._channel_order: tuple[str, ...] = tuple(ch for ch, _ in binding.channel_to_role)
        self._channel_index: dict[str, int] = {ch: i for i, ch in enumerate(self._channel_order)}

    def assess_metabolic_gate(self, packet: QuantumBioPacket) -> SevoAssessment:
        packet.validate()
        n_q = len(self._role_order)
        n_ent = len(self.binding.entangled_pairs)
        # 2 single-qubit gates per channel (RY, RZ) + CNOTs for entangled pairs.
        n_gates = 2 * n_q + n_ent
        energy_w = _estimate_energy_watts(
            num_qubits=n_q,
            num_gates=n_gates,
            entanglement_depth=n_ent,
            num_spikes=packet.num_spikes,
        )
        sevo = _compute_sevo(packet.delta_utility, packet.delta_entropy_info)
        if energy_w > self.binding.max_energy_w:
            return SevoAssessment(
                sevo=sevo,
                threshold=self.binding.sevo_threshold,
                estimated_energy_w=energy_w,
                max_energy_w=self.binding.max_energy_w,
                approved=False,
                reason="energy_budget_exceeded",
            )
        if sevo <= self.binding.sevo_threshold:
            return SevoAssessment(
                sevo=sevo,
                threshold=self.binding.sevo_threshold,
                estimated_energy_w=energy_w,
                max_energy_w=self.binding.max_energy_w,
                approved=False,
                reason="sevo_below_threshold",
            )
        return SevoAssessment(
            sevo=sevo,
            threshold=self.binding.sevo_threshold,
            estimated_energy_w=energy_w,
            max_energy_w=self.binding.max_energy_w,
            approved=True,
            reason="ok",
        )

    @staticmethod
    def _apply_single_qubit(
        state: np.ndarray, gate: np.ndarray, qubit: int, n_qubits: int
    ) -> np.ndarray:
        reshaped = state.reshape((2,) * n_qubits)
        moved = np.moveaxis(reshaped, qubit, 0)
        flat = moved.reshape(2, -1)
        out = (gate @ flat).reshape(moved.shape)
        return np.asarray(np.moveaxis(out, 0, qubit).reshape(-1), dtype=np.complex128)

    @staticmethod
    def _apply_cnot(state: np.ndarray, control: int, target: int, n_qubits: int) -> np.ndarray:
        reshaped = state.reshape((2,) * n_qubits)
        # Swap target basis components wherever control == 1.
        idx_c1 = [slice(None)] * n_qubits
        idx_c1[control] = 1  # type: ignore[call-overload]
        sub = reshaped[tuple(idx_c1)].copy()
        target_axis = target if target < control else target - 1
        swapped = np.flip(sub, axis=target_axis)
        result = reshaped.copy()
        result[tuple(idx_c1)] = swapped
        return result.reshape(-1)

    @staticmethod
    def _bipartite_phi_proxy(state: np.ndarray, n_qubits: int) -> float:
        if n_qubits < 2:
            return 0.0
        k = n_qubits // 2
        mat = state.reshape(1 << k, 1 << (n_qubits - k))
        singular_vals = np.linalg.svd(mat, compute_uv=False)
        probs = np.square(singular_vals)
        probs = probs[probs > 1e-12]
        if probs.size == 0:
            return 0.0
        s_a = float(-np.sum(probs * np.log2(probs)))
        # For a pure bipartite state, I(A:B) = 2 * S(rho_A).
        return float(max(0.0, 2.0 * s_a))

    def execute_packet(
        self, packet: QuantumBioPacket, *, enforce_gate: bool = True
    ) -> HybridTickResult:
        packet.validate()
        if packet.channel_ids != self._channel_order:
            raise InteropValidationError(
                "packet.channel_ids must match binding channel order exactly"
            )
        sevo = self.assess_metabolic_gate(packet)
        if enforce_gate and not sevo.approved:
            zeros = tuple(0.0 for _ in self._role_order)
            return HybridTickResult(
                tick=packet.tick,
                backend_name=self.backend_name,
                measurements=tuple((r, "0") for r in self._role_order),
                coherence_phi=0.0,
                feedback_modulation=zeros,
                sevo=sevo,
                gate_blocked=True,
            )

        n = len(self._role_order)
        state = np.zeros(1 << n, dtype=np.complex128)
        state[0] = 1.0 + 0.0j

        for i, (theta, act) in enumerate(
            zip(packet.rotation_angles_rad, packet.normalized_activity, strict=True)
        ):
            c = math.cos(theta / 2.0)
            s = math.sin(theta / 2.0)
            ry = np.array([[c, -s], [s, c]], dtype=np.complex128)
            rz_angle = act * math.pi
            rz = np.array(
                [[np.exp(-0.5j * rz_angle), 0.0], [0.0, np.exp(0.5j * rz_angle)]],
                dtype=np.complex128,
            )
            state = self._apply_single_qubit(state, ry, i, n)
            state = self._apply_single_qubit(state, rz, i, n)

        for ch_a, ch_b in self.binding.entangled_pairs:
            state = self._apply_cnot(state, self._channel_index[ch_a], self._channel_index[ch_b], n)

        phi = self._bipartite_phi_proxy(state, n)
        probs = np.abs(state) ** 2
        probs = probs / float(np.sum(probs))
        outcome_idx = int(self._rng.choice(len(probs), p=probs))
        bitstring = format(outcome_idx, f"0{n}b")
        measurements = [(role, bit) for role, bit in zip(self._role_order, bitstring, strict=True)]
        feedback = _feedback_from_measurements(measurements, packet.normalized_activity, phi)
        return HybridTickResult(
            tick=packet.tick,
            backend_name=self.backend_name,
            measurements=tuple(measurements),
            coherence_phi=phi,
            feedback_modulation=feedback,
            sevo=sevo,
            gate_blocked=False,
        )

    def kernel_summary(self) -> dict[str, int | str]:
        return {
            "backend": self.backend_name,
            "num_qubits": len(self._role_order),
            "num_entanglements": len(self.binding.entangled_pairs),
        }


class QSpeaceKernelAdapter:
    """Native interoperability adapter delegating directly to ``q_speace``.

    Lazily imports ``q_speace`` so ``b_speace`` remains installable and testable
    standalone while providing first-class integration with:
      - ``q_speace.QuantumNeuralBridge`` (neuron/channel slot & entanglement registry)
      - ``q_speace.BrainQuantumCircuit`` & ``QuantumBrainSimulator`` (unitary circuit execution)
      - ``q_speace.QuantumCostModel`` & ``QuantumOperation`` (energy & Sevo gate)
    """

    backend_name: str = "q_speace_hybrid_kernel"

    def __init__(self, binding: HybridBindingSpec, seed: int | None = None) -> None:
        binding.validate()
        self.binding: HybridBindingSpec = binding
        self._seed = seed
        self._channel_order: tuple[str, ...] = tuple(ch for ch, _ in binding.channel_to_role)
        self._role_order: tuple[str, ...] = tuple(role for _, role in binding.channel_to_role)

        try:
            q_mod = importlib.import_module("q_speace")
        except ImportError as exc:
            raise InteropError(
                "q_speace is not installed in the active Python environment; "
                "install b-speace[qspeace] or use StandaloneQuantumKernelAdapter."
            ) from exc

        self._gate_type: Any = q_mod.GateType
        self._circuit_cls: Any = q_mod.BrainQuantumCircuit
        self._sim: Any = q_mod.QuantumBrainSimulator(seed=seed)
        self._cost_model: Any = q_mod.QuantumCostModel()
        self._op_cls: Any = q_mod.QuantumOperation
        self._bridge: Any = q_mod.QuantumNeuralBridge(num_qubits_per_neuron=1, seed=seed)

        for ch, _ in binding.channel_to_role:
            self._bridge.register(ch)
        for ch_a, ch_b in binding.entangled_pairs:
            self._bridge.entangle_neurons(ch_a, ch_b, label="bio_quantum_binding")

    def assess_metabolic_gate(self, packet: QuantumBioPacket) -> SevoAssessment:
        packet.validate()
        n_q = len(self._role_order)
        n_ent = len(self.binding.entangled_pairs)
        op = self._op_cls(
            num_qubits=n_q,
            num_gates=2 * n_q + n_ent,
            entanglement_depth=n_ent,
            decoherence_budget=0.0,
            num_spikes=packet.num_spikes,
        )
        energy_w = float(self._cost_model.energy_watts(op))
        sevo = float(self._cost_model.sevo(packet.delta_utility, packet.delta_entropy_info))
        if energy_w > self.binding.max_energy_w:
            return SevoAssessment(
                sevo=sevo,
                threshold=self.binding.sevo_threshold,
                estimated_energy_w=energy_w,
                max_energy_w=self.binding.max_energy_w,
                approved=False,
                reason="energy_budget_exceeded",
            )
        if not bool(
            self._cost_model.passes_sevo(
                packet.delta_utility,
                packet.delta_entropy_info,
                threshold=self.binding.sevo_threshold,
            )
        ):
            return SevoAssessment(
                sevo=sevo,
                threshold=self.binding.sevo_threshold,
                estimated_energy_w=energy_w,
                max_energy_w=self.binding.max_energy_w,
                approved=False,
                reason="sevo_below_threshold",
            )
        return SevoAssessment(
            sevo=sevo,
            threshold=self.binding.sevo_threshold,
            estimated_energy_w=energy_w,
            max_energy_w=self.binding.max_energy_w,
            approved=True,
            reason="ok",
        )

    def execute_packet(
        self, packet: QuantumBioPacket, *, enforce_gate: bool = True
    ) -> HybridTickResult:
        packet.validate()
        if packet.channel_ids != self._channel_order:
            raise InteropValidationError(
                "packet.channel_ids must match binding channel order exactly"
            )
        sevo = self.assess_metabolic_gate(packet)
        if enforce_gate and not sevo.approved:
            zeros = tuple(0.0 for _ in self._role_order)
            return HybridTickResult(
                tick=packet.tick,
                backend_name=self.backend_name,
                measurements=tuple((r, "0") for r in self._role_order),
                coherence_phi=0.0,
                feedback_modulation=zeros,
                sevo=sevo,
                gate_blocked=True,
            )

        self._bridge.set_activity(np.asarray(packet.normalized_activity, dtype=np.float64))

        circuit = self._circuit_cls(name=f"b_speace_tick_{packet.tick}")
        role_map = self.binding.role_map()
        for _ch, role in self.binding.channel_to_role:
            circuit.add_qubit(role)
        for ch, theta, act in zip(
            packet.channel_ids,
            packet.rotation_angles_rad,
            packet.normalized_activity,
            strict=True,
        ):
            role = role_map[ch]
            circuit.add_gate(self._gate_type.RY, target=role, angle=float(theta))
            circuit.add_gate(self._gate_type.RZ, target=role, angle=float(act * math.pi))
        for ch_a, ch_b in self.binding.entangled_pairs:
            circuit.add_gate(
                self._gate_type.CNOT,
                control=role_map[ch_a],
                target=role_map[ch_b],
            )

        qstate = self._sim.state(circuit)
        phi = float(qstate.phi_proxy())
        mr = qstate.measure()
        measurements = [(circuit.role_of(i), bit) for i, bit in enumerate(mr.bitstring)]
        feedback = _feedback_from_measurements(measurements, packet.normalized_activity, phi)
        return HybridTickResult(
            tick=packet.tick,
            backend_name=self.backend_name,
            measurements=tuple(measurements),
            coherence_phi=phi,
            feedback_modulation=feedback,
            sevo=sevo,
            gate_blocked=False,
        )

    def kernel_summary(self) -> dict[str, int | str]:
        bridge_summary = dict(self._bridge.summary())
        return {
            "backend": self.backend_name,
            "num_neurons": int(bridge_summary["num_neurons"]),
            "num_qubits": int(bridge_summary["num_qubits"]),
            "num_entanglements": int(bridge_summary["num_entanglements"]),
            "connected_components": int(bridge_summary["connected_components"]),
        }


class BaseBioQuantumAdapter:
    """Concrete high-level bridge implementing :class:`BioQuantumAdapter`."""

    adapter_name: str = "bio_quantum_bridge"

    def __init__(self, kernel: QuantumKernelPort) -> None:
        self.kernel: QuantumKernelPort = kernel

    def build_packet(
        self,
        tick: int,
        features: EncodedBioFeatures,
        *,
        delta_utility: float,
        delta_entropy_info: float,
        num_spikes: int = 0,
    ) -> QuantumBioPacket:
        idx_map = {cid: i for i, cid in enumerate(features.channel_ids)}
        bound_channels = tuple(ch for ch, _ in self.kernel.binding.channel_to_role)
        missing = [ch for ch in bound_channels if ch not in idx_map]
        if missing:
            raise InteropValidationError(
                f"encoded bio features missing bound channels: {missing!r}"
            )
        raw_act = np.array(
            [features.normalized_activity[idx_map[ch]] for ch in bound_channels],
            dtype=np.float64,
        )
        total = float(raw_act.sum())
        norm_act = (
            raw_act / total if total > 0.0 else np.ones(len(bound_channels)) / len(bound_channels)
        )
        angles = tuple(float(features.phase_angles_rad[idx_map[ch]]) for ch in bound_channels)

        packet = QuantumBioPacket(
            tick=tick,
            channel_ids=bound_channels,
            normalized_activity=tuple(float(v) for v in norm_act),
            rotation_angles_rad=angles,
            delta_utility=delta_utility,
            delta_entropy_info=delta_entropy_info,
            num_spikes=num_spikes,
            metadata={
                "firing_rate_hz": features.firing_rate_hz,
                "synchrony_index": features.synchrony_index,
                "shannon_entropy_bits": features.shannon_entropy_bits,
            },
        )
        packet.validate()
        return packet

    def step_hybrid(
        self,
        tick: int,
        features: EncodedBioFeatures,
        *,
        delta_utility: float,
        delta_entropy_info: float,
        num_spikes: int = 0,
        enforce_gate: bool = True,
    ) -> HybridTickResult:
        packet = self.build_packet(
            tick=tick,
            features=features,
            delta_utility=delta_utility,
            delta_entropy_info=delta_entropy_info,
            num_spikes=num_spikes,
        )
        return self.kernel.execute_packet(packet, enforce_gate=enforce_gate)


def make_quantum_kernel_adapter(
    binding: HybridBindingSpec,
    *,
    prefer_qspeace: bool = True,
    seed: int | None = None,
) -> QuantumKernelPort:
    """Factory selecting :class:`QSpeaceKernelAdapter` when available, else standalone."""
    if prefer_qspeace:
        try:
            return QSpeaceKernelAdapter(binding=binding, seed=seed)
        except InteropError:
            pass
    return StandaloneQuantumKernelAdapter(binding=binding, seed=seed)
