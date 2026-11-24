"""Typed value objects and errors for bio-electric signal simulation (T001)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


class BioElectricError(Exception):
    """Base error for the bio-electric simulation subsystem."""


class BioSignalValidationError(BioElectricError):
    """Raised when bio-electric parameters or signal arrays fail validation."""


def _require_finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise BioSignalValidationError(f"{name} must be finite (got {value!r})")


@dataclass(frozen=True)
class IonChannelParams:
    """Dimensionless excitable-membrane parameters (FitzHugh-Nagumo family).

    Attributes
    ----------
    a:
        Recovery offset controlling excitability threshold.
    b:
        Recovery slope controlling relaxation rate.
    tau:
        Time-scale separation between fast voltage and slow recovery variables.
    spike_threshold:
        Dimensionless potential threshold above which a spike event is flagged.
    voltage_scale_mv:
        Linear scaling converting dimensionless potential to millivolts.
    resting_potential_mv:
        Baseline resting membrane potential in millivolts.
    """

    a: float = 0.7
    b: float = 0.8
    tau: float = 12.5
    spike_threshold: float = 1.0
    voltage_scale_mv: float = 35.0
    resting_potential_mv: float = -65.0

    def validate(self) -> None:
        for name, val in (
            ("a", self.a),
            ("b", self.b),
            ("tau", self.tau),
            ("spike_threshold", self.spike_threshold),
            ("voltage_scale_mv", self.voltage_scale_mv),
            ("resting_potential_mv", self.resting_potential_mv),
        ):
            _require_finite(val, name)
        if self.tau <= 0.0:
            raise BioSignalValidationError(f"tau must be > 0 (got {self.tau})")
        if self.voltage_scale_mv <= 0.0:
            raise BioSignalValidationError(
                f"voltage_scale_mv must be > 0 (got {self.voltage_scale_mv})"
            )


@dataclass(frozen=True)
class StimulationPulse:
    """Bounded external electrical pulse applied to one or more channels."""

    channel_indices: tuple[int, ...]
    amplitude_ua: float
    duration_ms: float
    start_ms: float = 0.0
    frequency_hz: float = 0.0
    biphasic: bool = True

    def validate(self, num_channels: int | None = None) -> None:
        if not self.channel_indices:
            raise BioSignalValidationError("channel_indices must be non-empty")
        for idx in self.channel_indices:
            if idx < 0:
                raise BioSignalValidationError(f"negative channel index: {idx}")
            if num_channels is not None and idx >= num_channels:
                raise BioSignalValidationError(
                    f"channel index {idx} out of range [0, {num_channels})"
                )
        for name, val in (
            ("amplitude_ua", self.amplitude_ua),
            ("duration_ms", self.duration_ms),
            ("start_ms", self.start_ms),
            ("frequency_hz", self.frequency_hz),
        ):
            _require_finite(val, name)
        if self.duration_ms <= 0.0:
            raise BioSignalValidationError(f"duration_ms must be > 0 (got {self.duration_ms})")
        if self.start_ms < 0.0:
            raise BioSignalValidationError(f"start_ms must be >= 0 (got {self.start_ms})")
        if self.frequency_hz < 0.0:
            raise BioSignalValidationError(f"frequency_hz must be >= 0 (got {self.frequency_hz})")


@dataclass
class MembraneState:
    """Mutable internal state snapshot of a multi-channel excitable membrane."""

    potentials: np.ndarray
    recovery: np.ndarray
    time_ms: float = 0.0

    def validate(self) -> None:
        if self.potentials.ndim != 1 or self.recovery.ndim != 1:
            raise BioSignalValidationError("potentials and recovery must be 1-D arrays")
        if self.potentials.shape != self.recovery.shape:
            raise BioSignalValidationError("potentials and recovery shapes must match")
        if self.potentials.size == 0:
            raise BioSignalValidationError("membrane state must have >= 1 channel")
        if not (np.all(np.isfinite(self.potentials)) and np.all(np.isfinite(self.recovery))):
            raise BioSignalValidationError("membrane state contains non-finite values")
        _require_finite(self.time_ms, "time_ms")
        if self.time_ms < 0.0:
            raise BioSignalValidationError(f"time_ms must be >= 0 (got {self.time_ms})")

    def copy(self) -> MembraneState:
        return MembraneState(
            potentials=self.potentials.copy(),
            recovery=self.recovery.copy(),
            time_ms=self.time_ms,
        )


@dataclass(frozen=True)
class BioSignalFrame:
    """Immutable single-tick multi-channel bio-electric recording."""

    timestamp_ms: float
    channel_ids: tuple[str, ...]
    potentials_mv: tuple[float, ...]
    spike_mask: tuple[bool, ...]
    instantaneous_power_uw: float
    metadata: dict[str, float] = field(default_factory=dict)

    @property
    def num_channels(self) -> int:
        return len(self.channel_ids)

    @property
    def spike_count(self) -> int:
        return sum(1 for fired in self.spike_mask if fired)


@dataclass(frozen=True)
class EncodedBioFeatures:
    """Normalized computational feature vector derived from bio-electric frames.

    Designed for direct ingestion by downstream classical controllers or
    :mod:`b_speace.interop` quantum adapters.
    """

    channel_ids: tuple[str, ...]
    normalized_activity: tuple[float, ...]
    phase_angles_rad: tuple[float, ...]
    firing_rate_hz: float
    synchrony_index: float
    shannon_entropy_bits: float
