"""Typed contracts and errors for T005 functional continuity verification (M0/M1)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum


class ContinuityError(Exception):
    """Base error for the T005 continuity verification subsystem."""


class ContinuityValidationError(ContinuityError):
    """Raised when observations, frames, profiles, or fault specs fail validation."""


class AuthorityViolationError(ContinuityError):
    """Raised when an invariant violation is detected in authority enforcement."""


class ContinuityMode(StrEnum):
    """Four P-Q-B arm configurations for T005 continuity experiments."""

    P = "P"
    P_Q = "P+Q"
    P_B = "P+B"
    P_Q_B = "P+Q+B"


class StandbyMode(StrEnum):
    """Replica pre-alignment strategy prior to primary controller failure."""

    WARM = "warm"
    COLD = "cold"


def _require_finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ContinuityValidationError(f"{name} must be finite (got {value!r})")


@dataclass(frozen=True)
class Observation:
    """Single sensor/stream sample distinguishing acquisition and delivery clocks."""

    session_id: str
    source_id: str
    local_seq: int
    acquired_tick: int
    delivered_tick: int
    value: float
    valid: bool = True

    def validate(self) -> None:
        if not self.session_id or not self.source_id:
            raise ContinuityValidationError("session_id and source_id must be non-empty")
        if self.local_seq < 0 or self.acquired_tick < 0 or self.delivered_tick < 0:
            raise ContinuityValidationError("sequence and tick indices must be >= 0")
        if self.delivered_tick < self.acquired_tick:
            raise ContinuityValidationError("delivered_tick cannot precede acquired_tick")
        if self.valid:
            _require_finite(self.value, "value")


@dataclass(frozen=True)
class CommittedFrame:
    """Append-only ordered frame committed to the session log."""

    session_id: str
    frame_index: int
    present_channels_mask: tuple[str, ...]
    observations: tuple[Observation, ...]
    schema_version: str = "t005.frame.v1"
    quality_flag: str = "complete"


@dataclass
class ReplicaState:
    """Mutable state of a virtual extension replica consuming committed frames."""

    replica_id: str
    profile_score: float
    next_frame_cursor: int = 0
    context: float = 0.5
    synthetic_goal: str = "track_context"
    last_confirmed_action: str | None = None
    available: bool = True
    buffered_frames: dict[int, CommittedFrame] = field(default_factory=dict)
    updates_applied: int = 0

    def validate(self) -> None:
        if not self.replica_id:
            raise ContinuityValidationError("replica_id must be non-empty")
        _require_finite(self.profile_score, "profile_score")
        if not (0.0 <= self.profile_score <= 1.0):
            raise ContinuityValidationError(
                f"profile_score must be in [0, 1] (got {self.profile_score})"
            )
        _require_finite(self.context, "context")
        if self.next_frame_cursor < 0:
            raise ContinuityValidationError("next_frame_cursor must be >= 0")


@dataclass(frozen=True)
class Grant:
    """Monotonic authority mandate issued by the coordinator."""

    session_id: str
    epoch: int
    holder_id: str
    issued_at_tick: int


@dataclass(frozen=True)
class Command:
    """Logical virtual command emitted by the active authority holder."""

    session_id: str
    epoch: int
    holder_id: str
    tick: int
    action_id: str
    targets: tuple[str, ...]
    context_estimate: float

    def validate(self) -> None:
        if not self.session_id or not self.holder_id or not self.action_id:
            raise ContinuityValidationError(
                "session_id, holder_id, and action_id must be non-empty"
            )
        if self.epoch < 0 or self.tick < 0:
            raise ContinuityValidationError("epoch and tick must be >= 0")
        if not self.targets:
            raise ContinuityValidationError("targets must be non-empty")
        _require_finite(self.context_estimate, "context_estimate")


@dataclass(frozen=True)
class DestinationReceipt:
    """Atomic acceptance or motivated rejection emitted by the virtual destination."""

    session_id: str
    tick: int
    action_id: str
    epoch: int
    holder_id: str
    accepted: bool
    deduplicated: bool
    reason: str


@dataclass(frozen=True)
class FaultSpec:
    """Fault injection specification for deterministic M1 verification."""

    fault_tick: int = 8
    replay_budget: int = 2
    standby_mode: StandbyMode = StandbyMode.WARM
    all_replicas_disconnected: bool = False
    lagging_replica_id: str | None = None

    def validate(self, horizon_ticks: int) -> None:
        if horizon_ticks < 1:
            raise ContinuityValidationError("horizon_ticks must be >= 1")
        if self.fault_tick < 0 or self.fault_tick > horizon_ticks:
            raise ContinuityValidationError(
                f"fault_tick {self.fault_tick} out of range [0, {horizon_ticks}]"
            )
        if self.replay_budget < 1:
            raise ContinuityValidationError(
                f"replay_budget must be >= 1 (got {self.replay_budget})"
            )


@dataclass(frozen=True)
class TickTraceEntry:
    """Causal per-tick provenance entry linking frame, epoch, election, and receipt."""

    tick: int
    frame_index: int
    epoch: int
    holder_id: str | None
    elected_replica: str | None
    command_action_id: str | None
    accepted: bool
    reason: str
    context_after: float | None
    oracle_context: float


@dataclass(frozen=True)
class RunRecord:
    """Complete auditable result of a single T005 continuity simulation run."""

    session_id: str
    input_hash: str
    seed: int
    mode: ContinuityMode
    standby_mode: StandbyMode
    fault_tick: int
    replay_budget: int
    horizon_ticks: int
    first_recovery_tick: int | None
    missed_actions: int
    expected_missed_actions: int
    background_updates_before_fault: int
    authority_violations: int
    duplicate_effects: int
    max_context_error: float
    winner_replica: str | None
    rejections: tuple[DestinationReceipt, ...] = field(default_factory=tuple)
    trace: tuple[TickTraceEntry, ...] = field(default_factory=tuple)
