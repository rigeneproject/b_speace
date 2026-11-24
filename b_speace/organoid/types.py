"""Typed contracts, safety envelopes, and errors for Wetware-in-the-loop APIs (T001)."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from b_speace.bioelectric.types import BioSignalFrame


class OrganoidLifecycleState(StrEnum):
    """Formal lifecycle state machine for an organoid MEA interface."""

    OFFLINE = "offline"
    CALIBRATING = "calibrating"
    READY = "ready"
    STIMULATING = "stimulating"
    SHUTDOWN = "shutdown"
    FAULT = "fault"


class OrganoidError(Exception):
    """Base error for all Wetware-in-the-loop operations."""


class OrganoidUnavailableError(OrganoidError):
    """Raised when an operation is requested in an incompatible lifecycle state."""


class OrganoidSafetyViolationError(OrganoidError):
    """Raised when a stimulation command violates the WetwareSafetyEnvelope."""


class OrganoidCalibrationError(OrganoidError):
    """Raised when electrode impedance or baseline calibration fails."""


class OrganoidHealthError(OrganoidError):
    """Raised when environmental/viability telemetry falls outside safe bounds."""


def _check_finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise OrganoidSafetyViolationError(f"{name} must be finite (got {value!r})")


@dataclass(frozen=True)
class ElectrodeChannel:
    """Descriptor for a single Multi-Electrode Array (MEA) site."""

    channel_id: str
    index: int
    impedance_kohm: float = 50.0
    surface_area_cm2: float = 7.0e-6  # ~30 um diameter microelectrode
    active: bool = True

    def validate(self) -> None:
        if not self.channel_id:
            raise OrganoidCalibrationError("channel_id must be non-empty")
        if self.index < 0:
            raise OrganoidCalibrationError(f"negative channel index: {self.index}")
        if not math.isfinite(self.impedance_kohm) or self.impedance_kohm <= 0.0:
            raise OrganoidCalibrationError(
                f"impedance_kohm must be finite and > 0 (got {self.impedance_kohm})"
            )
        if not math.isfinite(self.surface_area_cm2) or self.surface_area_cm2 <= 0.0:
            raise OrganoidCalibrationError(
                f"surface_area_cm2 must be finite and > 0 (got {self.surface_area_cm2})"
            )


@dataclass(frozen=True)
class WetwareSafetyEnvelope:
    """Hard biophysical safety bounds enforced fail-closed before stimulation.

    Default thresholds reflect conservative micro-electrode stimulation limits
    (charge-balanced biphasic pulses, physiological temperature and pH).
    """

    max_voltage_mv: float = 800.0
    max_current_ua: float = 20.0
    max_pulse_duration_ms: float = 10.0
    max_charge_density_uc_cm2: float = 30.0
    max_frequency_hz: float = 100.0
    temp_min_c: float = 35.5
    temp_max_c: float = 38.0
    ph_min: float = 7.2
    ph_max: float = 7.55
    min_viability: float = 0.7
    require_biphasic: bool = True

    def validate(self) -> None:
        for name, val in (
            ("max_voltage_mv", self.max_voltage_mv),
            ("max_current_ua", self.max_current_ua),
            ("max_pulse_duration_ms", self.max_pulse_duration_ms),
            ("max_charge_density_uc_cm2", self.max_charge_density_uc_cm2),
            ("max_frequency_hz", self.max_frequency_hz),
            ("temp_min_c", self.temp_min_c),
            ("temp_max_c", self.temp_max_c),
            ("ph_min", self.ph_min),
            ("ph_max", self.ph_max),
            ("min_viability", self.min_viability),
        ):
            _check_finite(val, name)
        if self.max_voltage_mv <= 0.0 or self.max_current_ua <= 0.0:
            raise OrganoidSafetyViolationError("max voltage and current must be > 0")
        if self.max_pulse_duration_ms <= 0.0 or self.max_charge_density_uc_cm2 <= 0.0:
            raise OrganoidSafetyViolationError("max pulse duration and charge density must be > 0")
        if self.max_frequency_hz <= 0.0:
            raise OrganoidSafetyViolationError("max_frequency_hz must be > 0")
        if self.temp_min_c >= self.temp_max_c:
            raise OrganoidSafetyViolationError("temp_min_c must be < temp_max_c")
        if self.ph_min >= self.ph_max:
            raise OrganoidSafetyViolationError("ph_min must be < ph_max")
        if not (0.0 < self.min_viability <= 1.0):
            raise OrganoidSafetyViolationError("min_viability must be in (0, 1]")


@dataclass(frozen=True)
class StimulationCommand:
    """Explicit stimulation instruction submitted to an OrganoidInterface."""

    target_channels: tuple[str, ...]
    amplitude_ua: float
    voltage_mv: float
    duration_ms: float
    frequency_hz: float = 10.0
    biphasic: bool = True
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, float] = field(default_factory=dict)

    def charge_per_phase_uc(self) -> float:
        """Charge delivered per phase in microcoulombs (uA * ms * 1e-3)."""
        phase_ms = 0.5 * self.duration_ms if self.biphasic else self.duration_ms
        return abs(self.amplitude_ua) * phase_ms * 1e-3

    def validate(self) -> None:
        if not self.command_id:
            raise OrganoidSafetyViolationError("command_id must be non-empty")
        if not self.target_channels:
            raise OrganoidSafetyViolationError("target_channels must be non-empty")
        for name, val in (
            ("amplitude_ua", self.amplitude_ua),
            ("voltage_mv", self.voltage_mv),
            ("duration_ms", self.duration_ms),
            ("frequency_hz", self.frequency_hz),
        ):
            _check_finite(val, name)
        if self.duration_ms <= 0.0:
            raise OrganoidSafetyViolationError(f"duration_ms must be > 0 (got {self.duration_ms})")
        if self.frequency_hz < 0.0:
            raise OrganoidSafetyViolationError(
                f"frequency_hz must be >= 0 (got {self.frequency_hz})"
            )


@dataclass(frozen=True)
class MEARecording:
    """Multi-Electrode Array recording window returned by an OrganoidInterface."""

    timestamp_ms: float
    sample_rate_hz: float
    channel_ids: tuple[str, ...]
    frames: tuple[BioSignalFrame, ...]
    spike_counts: tuple[int, ...]
    mean_snr_db: float
    estimated_energy_uj: float

    @property
    def total_spikes(self) -> int:
        return sum(self.spike_counts)


@dataclass(frozen=True)
class OrganoidHealthSnapshot:
    """Environmental and viability telemetry snapshot of a wetware substrate."""

    lifecycle: OrganoidLifecycleState
    temperature_c: float
    ph: float
    viability_index: float
    mean_impedance_kohm: float
    active_channels: int
    total_channels: int
    safe_to_stimulate: bool


@dataclass(frozen=True)
class ClosedLoopStepResult:
    """Combined outcome of a Wetware-in-the-loop stimulate-and-record cycle."""

    command: StimulationCommand
    recording: MEARecording
    health: OrganoidHealthSnapshot
    safety_approved: bool
    blocked_reason: str | None = None
