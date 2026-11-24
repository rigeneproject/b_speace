"""Typed packets and assessment records for bio-to-quantum interop (T001)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


class InteropError(Exception):
    """Base error for B-SPEACE <-> Q-SPEACE interoperability."""


class InteropValidationError(InteropError):
    """Raised on malformed hybrid packets or binding specs."""


class InteropGateBlockedError(InteropError):
    """Raised when an energy or Sevo entropic-efficiency gate blocks dispatch."""


@dataclass(frozen=True)
class HybridBindingSpec:
    """Declares how biological/MEA channels map onto q_speace qubit roles.

    Attributes
    ----------
    channel_to_role:
        Ordered mapping of bio/MEA channel IDs to named qubit roles in
        ``q_speace.BrainQuantumCircuit`` / ``QuantumNeuralBridge``.
    entangled_pairs:
        Pairs of channel IDs bound via computational entanglement (CNOT /
        ``EntanglementRegistry``). Strictly a computational resource
        (no-communication theorem).
    max_qubits:
        Hard cap matching q_speace prototype simulator limits (<= 16).
    sevo_threshold:
        Minimum entropic efficiency ``Sevo = dU / dS_info`` required to allow
        hybrid quantum dispatch (EDD-CVT §5.1 target > 1.5).
    max_energy_w:
        Instantaneous power ceiling (Watts) enforced before dispatch.
    """

    channel_to_role: tuple[tuple[str, str], ...]
    entangled_pairs: tuple[tuple[str, str], ...] = ()
    max_qubits: int = 8
    sevo_threshold: float = 1.5
    max_energy_w: float = 250.0

    def validate(self) -> None:
        if not self.channel_to_role:
            raise InteropValidationError("channel_to_role must be non-empty")
        if self.max_qubits < 1 or self.max_qubits > 16:
            raise InteropValidationError(f"max_qubits must be in [1, 16] (got {self.max_qubits})")
        if len(self.channel_to_role) > self.max_qubits:
            raise InteropValidationError(
                f"channel_to_role length {len(self.channel_to_role)} exceeds "
                f"max_qubits {self.max_qubits}"
            )
        channels = [c for c, _ in self.channel_to_role]
        roles = [r for _, r in self.channel_to_role]
        if len(set(channels)) != len(channels):
            raise InteropValidationError("duplicate channel IDs in channel_to_role")
        if len(set(roles)) != len(roles):
            raise InteropValidationError("duplicate qubit roles in channel_to_role")
        channel_set = set(channels)
        for a, b in self.entangled_pairs:
            if a not in channel_set or b not in channel_set:
                raise InteropValidationError(f"entangled pair ({a!r}, {b!r}) references unknown id")
            if a == b:
                raise InteropValidationError(f"self-entanglement is invalid: {a!r}")
        if not math.isfinite(self.sevo_threshold):
            raise InteropValidationError("sevo_threshold must be finite")
        if not math.isfinite(self.max_energy_w) or self.max_energy_w < 0.0:
            raise InteropValidationError("max_energy_w must be finite and >= 0")

    def role_map(self) -> dict[str, str]:
        return dict(self.channel_to_role)


@dataclass(frozen=True)
class QuantumBioPacket:
    """Classical feature packet prepared for a hybrid classical-quantum step.

    All fields are classical telemetry/angles; no quantum state leaves the
    classical boundary directly.
    """

    tick: int
    channel_ids: tuple[str, ...]
    normalized_activity: tuple[float, ...]
    rotation_angles_rad: tuple[float, ...]
    delta_utility: float
    delta_entropy_info: float
    num_spikes: int = 0
    metadata: dict[str, float] = field(default_factory=dict)

    def validate(self) -> None:
        if self.tick < 0:
            raise InteropValidationError(f"tick must be >= 0 (got {self.tick})")
        n = len(self.channel_ids)
        if n == 0:
            raise InteropValidationError("channel_ids must be non-empty")
        if len(self.normalized_activity) != n or len(self.rotation_angles_rad) != n:
            raise InteropValidationError(
                "normalized_activity and rotation_angles_rad must match channel_ids length"
            )
        for val in self.normalized_activity:
            if not math.isfinite(val) or val < 0.0:
                raise InteropValidationError(f"invalid normalized_activity value: {val!r}")
        for ang in self.rotation_angles_rad:
            if not math.isfinite(ang):
                raise InteropValidationError(f"non-finite rotation angle: {ang!r}")
        if not (math.isfinite(self.delta_utility) and math.isfinite(self.delta_entropy_info)):
            raise InteropValidationError("delta_utility and delta_entropy_info must be finite")
        if self.num_spikes < 0:
            raise InteropValidationError(f"num_spikes must be >= 0 (got {self.num_spikes})")


@dataclass(frozen=True)
class SevoAssessment:
    """Metabolic and entropic efficiency evaluation matching q_speace QuantumCostModel."""

    sevo: float
    threshold: float
    estimated_energy_w: float
    max_energy_w: float
    approved: bool
    reason: str = "ok"


@dataclass(frozen=True)
class HybridTickResult:
    """Classical outcome of one bio-to-quantum-to-bio hybrid tick."""

    tick: int
    backend_name: str
    measurements: tuple[tuple[str, str], ...]
    coherence_phi: float
    feedback_modulation: tuple[float, ...]
    sevo: SevoAssessment
    gate_blocked: bool = False
