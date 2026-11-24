"""Structural Protocols for B-SPEACE <-> Q-SPEACE hybrid interoperability (T001)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from b_speace.bioelectric.types import EncodedBioFeatures

from .types import (
    HybridBindingSpec,
    HybridTickResult,
    QuantumBioPacket,
    SevoAssessment,
)


@runtime_checkable
class QuantumKernelPort(Protocol):
    """Port abstracting q_speace's hybrid classical-quantum kernel.

    Concrete adapters may wrap ``q_speace`` directly (``QSpeaceKernelAdapter``)
    or provide a standalone numpy fallback (``StandaloneQuantumKernelAdapter``).
    """

    backend_name: str
    binding: HybridBindingSpec

    def assess_metabolic_gate(self, packet: QuantumBioPacket) -> SevoAssessment:
        """Evaluate estimated power draw and entropic efficiency Sevo."""
        ...

    def execute_packet(
        self, packet: QuantumBioPacket, *, enforce_gate: bool = True
    ) -> HybridTickResult:
        """Encode bio features into a quantum circuit, run, and return classical feedback."""
        ...

    def kernel_summary(self) -> dict[str, int | str]:
        """Return diagnostic counts (qubits, bindings, entanglements, backend)."""
        ...


@runtime_checkable
class BioQuantumAdapter(Protocol):
    """High-level bidirectional bridge from EncodedBioFeatures to quantum feedback."""

    adapter_name: str
    kernel: QuantumKernelPort

    def build_packet(
        self,
        tick: int,
        features: EncodedBioFeatures,
        *,
        delta_utility: float,
        delta_entropy_info: float,
        num_spikes: int = 0,
    ) -> QuantumBioPacket:
        """Project encoded bio-electric features onto the bound quantum channels."""
        ...

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
        """Run one bio -> quantum -> classical feedback cycle."""
        ...
