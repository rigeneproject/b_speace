"""Typed contracts and errors for cell-free biomolecular biosensors (T003)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


class BiomolecularError(Exception):
    """Base error for the biomolecular biosensing subsystem."""


class BiomolecularValidationError(BiomolecularError):
    """Raised when biosensor calibration, sample, or assay parameters are invalid."""


def _require_finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise BiomolecularValidationError(f"{name} must be finite (got {value!r})")


@dataclass(frozen=True)
class ChemicalSample:
    """Water or fluid sample submitted to a biosensor or reference assay.

    Note: ``true_concentration_mg_l`` is an internal physical-twin value consumed
    ONLY by simulated sensor/assay adapters; controllers must never read it directly.
    """

    sample_id: str
    sampled_at_min: float
    treated_volume_l: float
    contaminant: str
    true_concentration_mg_l: float
    matrix_interference: float = 0.0

    def validate(self) -> None:
        if not self.sample_id:
            raise BiomolecularValidationError("sample_id must be non-empty")
        if not self.contaminant:
            raise BiomolecularValidationError("contaminant must be non-empty")
        for name, val in (
            ("sampled_at_min", self.sampled_at_min),
            ("treated_volume_l", self.treated_volume_l),
            ("true_concentration_mg_l", self.true_concentration_mg_l),
            ("matrix_interference", self.matrix_interference),
        ):
            _require_finite(val, name)
        if self.sampled_at_min < 0.0:
            raise BiomolecularValidationError("sampled_at_min must be >= 0")
        if self.treated_volume_l < 0.0:
            raise BiomolecularValidationError("treated_volume_l must be >= 0")
        if self.true_concentration_mg_l < 0.0:
            raise BiomolecularValidationError("true_concentration_mg_l must be >= 0")
        if self.matrix_interference <= -1.0:
            raise BiomolecularValidationError("matrix_interference must be > -1.0")


@dataclass(frozen=True)
class BiosensorCalibration:
    """Calibration parameters for a ROSALIND-style allosteric Hill cell-free circuit.

    Transfer function:
        y(c, t) = f_min + (f_max - f_min) * c_eff^n / (kd_eff^n + c_eff^n) + noise
    where:
        kd_eff = kd_mg_l * (1.0 + drift_rate_per_min * elapsed_min)
        c_eff  = max(0.0, c * (1.0 + matrix_interference))
    """

    contaminant: str = "target_contaminant"
    threshold_mg_l: float = 0.10
    kd_mg_l: float = 0.10
    hill_n: float = 3.0
    f_min: float = 0.05
    f_max: float = 1.0
    incubation_delay_min: float = 5.0
    noise_std: float = 0.04
    drift_rate_per_min: float = 0.0
    cost_per_sample_usd: float = 1.5
    energy_per_sample_wh: float = 0.002

    def validate(self) -> None:
        if not self.contaminant:
            raise BiomolecularValidationError("contaminant must be non-empty")
        for name, val in (
            ("threshold_mg_l", self.threshold_mg_l),
            ("kd_mg_l", self.kd_mg_l),
            ("hill_n", self.hill_n),
            ("f_min", self.f_min),
            ("f_max", self.f_max),
            ("incubation_delay_min", self.incubation_delay_min),
            ("noise_std", self.noise_std),
            ("drift_rate_per_min", self.drift_rate_per_min),
            ("cost_per_sample_usd", self.cost_per_sample_usd),
            ("energy_per_sample_wh", self.energy_per_sample_wh),
        ):
            _require_finite(val, name)
        if self.threshold_mg_l <= 0.0:
            raise BiomolecularValidationError("threshold_mg_l must be > 0")
        if self.kd_mg_l <= 0.0:
            raise BiomolecularValidationError("kd_mg_l must be > 0")
        if self.hill_n <= 0.0:
            raise BiomolecularValidationError("hill_n must be > 0")
        if self.f_max <= self.f_min:
            raise BiomolecularValidationError("f_max must be > f_min")
        if self.incubation_delay_min < 0.0:
            raise BiomolecularValidationError("incubation_delay_min must be >= 0")
        if self.noise_std < 0.0:
            raise BiomolecularValidationError("noise_std must be >= 0")
        if self.cost_per_sample_usd < 0.0 or self.energy_per_sample_wh < 0.0:
            raise BiomolecularValidationError("cost and energy per sample must be >= 0")

    def fluorescence_threshold(self) -> float:
        """Expected noiseless fluorescence at ``threshold_mg_l`` with zero drift."""
        ratio = (self.threshold_mg_l**self.hill_n) / (
            self.kd_mg_l**self.hill_n + self.threshold_mg_l**self.hill_n
        )
        return float(self.f_min + (self.f_max - self.f_min) * ratio)


@dataclass(frozen=True)
class BiosensorReading:
    """Output emitted by a BiomolecularSensor after its incubation delay."""

    sample_id: str
    sampled_at_min: float
    available_at_min: float
    treated_volume_l: float
    fluorescence_norm: float
    fluorescence_threshold: float
    threshold_crossed: bool
    uncertainty_score: float
    cost_usd: float
    energy_wh: float
    metadata: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ReferenceAssayResult:
    """Independent laboratory analytical measurement (e.g., ICP-MS / LC-MS)."""

    sample_id: str
    sampled_at_min: float
    available_at_min: float
    treated_volume_l: float
    measured_concentration_mg_l: float
    limit_mg_l: float
    exceeds_limit: bool
    measurement_std_mg_l: float
    cost_usd: float
    energy_wh: float
