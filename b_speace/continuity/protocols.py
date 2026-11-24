"""Formal @runtime_checkable Protocols for T005 continuity verification (M0/M1)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from .types import Command, CommittedFrame, DestinationReceipt


@runtime_checkable
class ProfileMatcher(Protocol):
    """Scores candidate replica profiles against a scalar context in [0, 1]."""

    matcher_name: str
    uses_quantum: bool

    def score(self, context: float, profile: float) -> float:
        """Return a deterministic match score in [0, 1]."""
        ...

    def select_winner(
        self, context: float, profiles: Mapping[str, float]
    ) -> tuple[str, float, dict[str, float]]:
        """Return ``(winner_id, winner_score, all_scores)`` with deterministic tie-breaking."""
        ...


@runtime_checkable
class DestinationEndpointPort(Protocol):
    """Virtual command destination enforcing monotonic epochs and idempotency."""

    def advance_epoch(self, session_id: str, new_epoch: int, holder_id: str) -> None:
        """Advance accepted epoch and bind the active authority holder."""
        ...

    def apply(self, command: Command) -> DestinationReceipt:
        """Atomically validate, deduplicate, and record a virtual command."""
        ...

    def applied_count(self) -> int:
        """Return total number of distinct virtual effects actually applied."""
        ...


@runtime_checkable
class StateOraclePort(Protocol):
    """Independent prefix oracle verifying replica state reconstruction."""

    def recompute_context(
        self, frames: Sequence[CommittedFrame], *, initial_context: float = 0.5
    ) -> float:
        """Recompute expected scalar context directly from the committed frame prefix."""
        ...
