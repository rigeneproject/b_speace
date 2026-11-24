"""Formal Protocols for bio-electric signal simulation & encoding (T001).

All Protocols are ``@runtime_checkable`` so adapters do not need to inherit
from a shared concrete base class to satisfy static or runtime checks.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

import numpy as np

from .types import (
    BioSignalFrame,
    EncodedBioFeatures,
    MembraneState,
    StimulationPulse,
)


@runtime_checkable
class BioElectricSimulator(Protocol):
    """Stateful multi-channel bio-electric signal simulator."""

    simulator_name: str
    num_channels: int
    channel_ids: tuple[str, ...]
    dt_ms: float

    def reset(self, seed: int | None = None) -> MembraneState:
        """Reset internal membrane state to deterministic baseline."""
        ...

    def step(self, external_current: Sequence[float] | np.ndarray | None = None) -> BioSignalFrame:
        """Advance simulation by ``dt_ms`` with optional per-channel current."""
        ...

    def run(
        self, steps: int, pulses: Sequence[StimulationPulse] | None = None
    ) -> list[BioSignalFrame]:
        """Run ``steps`` consecutive ticks with optional timed stimulation pulses."""
        ...

    def state_snapshot(self) -> MembraneState:
        """Return a defensive copy of the current membrane state."""
        ...


@runtime_checkable
class BioSignalEncoder(Protocol):
    """Maps a window of BioSignalFrames into normalized computational features."""

    encoder_name: str

    def encode(self, frames: Sequence[BioSignalFrame]) -> EncodedBioFeatures:
        """Convert one or more bio-electric frames into normalized features."""
        ...


@runtime_checkable
class BioSignalDecoder(Protocol):
    """Maps normalized control/modulation vectors into bounded stimulation pulses."""

    decoder_name: str

    def decode(self, control_vector: Sequence[float], channel_count: int) -> list[StimulationPulse]:
        """Translate a bounded control vector in [0, 1] into stimulation pulses."""
        ...
