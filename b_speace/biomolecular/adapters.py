"""Reference adapters for cell-free threshold biosensors and analytical assays (T003)."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

import numpy as np

from .types import (
    BiomolecularValidationError,
    BiosensorCalibration,
    BiosensorReading,
    ChemicalSample,
    ReferenceAssayResult,
)


class BaseBiomolecularSensor(ABC):
    """Abstract base adapter enforcing sample and calibration validation."""

    sensor_name: str = "abstract_biomolecular_sensor"

    def __init__(
        self,
        calibration: BiosensorCalibration | None = None,
        seed: int | None = None,
    ) -> None:
        self.calibration: BiosensorCalibration = calibration or BiosensorCalibration()
        self.calibration.validate()
        self._seed = seed
        self._rng = np.random.default_rng(seed)

    def reset(self, seed: int | None = None) -> None:
        effective = self._seed if seed is None else seed
        self._rng = np.random.default_rng(effective)

    def sense(
        self, sample: ChemicalSample, *, elapsed_campaign_min: float = 0.0
    ) -> BiosensorReading:
        sample.validate()
        if not math.isfinite(elapsed_campaign_min) or elapsed_campaign_min < 0.0:
            raise BiomolecularValidationError(
                f"elapsed_campaign_min must be finite and >= 0 (got {elapsed_campaign_min!r})"
            )
        if sample.contaminant != self.calibration.contaminant:
            raise BiomolecularValidationError(
                f"sensor calibrated for {self.calibration.contaminant!r}, "
                f"cannot sense {sample.contaminant!r}"
            )
        return self._evaluate_sample(sample, elapsed_campaign_min=elapsed_campaign_min)

    @abstractmethod
    def _evaluate_sample(
        self, sample: ChemicalSample, *, elapsed_campaign_min: float
    ) -> BiosensorReading:
        """Compute biosensor output for a validated sample."""


class CellFreeThresholdSensorAdapter(BaseBiomolecularSensor):
    """ROSALIND-inspired cell-free allosteric transcription-factor threshold sensor.

    Models fluorescent aptamer output governed by a Hill transfer function with:
      - configurable incubation delay (``incubation_delay_min``),
      - stochastic readout noise (``noise_std``),
      - temporal calibration/reagent drift shifting effective ``K_d`` over time
        (``drift_rate_per_min``), and
      - optional sample matrix interference.
    """

    sensor_name: str = "rosalind_cell_free_hill_sensor"

    def _evaluate_sample(
        self, sample: ChemicalSample, *, elapsed_campaign_min: float
    ) -> BiosensorReading:
        cal = self.calibration
        # Effective dissociation constant drifts over campaign runtime (bounded > 10% of nominal).
        drift_factor = max(0.1, 1.0 + cal.drift_rate_per_min * elapsed_campaign_min)
        kd_eff = cal.kd_mg_l * drift_factor
        c_eff = max(0.0, sample.true_concentration_mg_l * (1.0 + sample.matrix_interference))

        if c_eff <= 0.0:
            hill_frac = 0.0
        else:
            c_n = c_eff**cal.hill_n
            kd_n = kd_eff**cal.hill_n
            hill_frac = float(c_n / (kd_n + c_n))

        clean_signal = cal.f_min + (cal.f_max - cal.f_min) * hill_frac
        noise = float(self._rng.normal(0.0, cal.noise_std)) if cal.noise_std > 0.0 else 0.0
        observed = float(np.clip(clean_signal + noise, 0.0, cal.f_max * 1.25))

        f_thresh = cal.fluorescence_threshold()
        crossed = observed >= f_thresh

        # Uncertainty score increases when reading is close to the decision boundary
        # or when readout noise is larger.
        margin = abs(observed - f_thresh)
        scale = max(cal.noise_std * 2.5, 0.05)
        uncertainty = float(math.exp(-margin / scale))

        return BiosensorReading(
            sample_id=sample.sample_id,
            sampled_at_min=sample.sampled_at_min,
            available_at_min=sample.sampled_at_min + cal.incubation_delay_min,
            treated_volume_l=sample.treated_volume_l,
            fluorescence_norm=observed,
            fluorescence_threshold=f_thresh,
            threshold_crossed=crossed,
            uncertainty_score=uncertainty,
            cost_usd=cal.cost_per_sample_usd,
            energy_wh=cal.energy_per_sample_wh,
            metadata={
                "kd_eff_mg_l": kd_eff,
                "drift_factor": drift_factor,
            },
        )


class SimulatedReferenceAssayAdapter:
    """Simulated independent analytical instrument (e.g., ICP-MS / LC-MS).

    Higher accuracy and no calibration drift, but higher turnaround latency,
    marginal cost, and energy consumption per sample.
    """

    assay_name: str = "simulated_icp_ms_reference"

    def __init__(
        self,
        *,
        turnaround_min: float = 30.0,
        relative_noise_std: float = 0.015,
        absolute_noise_floor_mg_l: float = 0.001,
        cost_per_sample_usd: float = 45.0,
        energy_per_sample_wh: float = 12.0,
        seed: int | None = None,
    ) -> None:
        for name, val in (
            ("turnaround_min", turnaround_min),
            ("relative_noise_std", relative_noise_std),
            ("absolute_noise_floor_mg_l", absolute_noise_floor_mg_l),
            ("cost_per_sample_usd", cost_per_sample_usd),
            ("energy_per_sample_wh", energy_per_sample_wh),
        ):
            if not math.isfinite(val) or val < 0.0:
                raise BiomolecularValidationError(f"{name} must be finite and >= 0 (got {val!r})")
        self.turnaround_min: float = float(turnaround_min)
        self._rel_noise = float(relative_noise_std)
        self._abs_floor = float(absolute_noise_floor_mg_l)
        self.cost_per_sample_usd: float = float(cost_per_sample_usd)
        self.energy_per_sample_wh: float = float(energy_per_sample_wh)
        self._seed = seed
        self._rng = np.random.default_rng(seed)

    def reset(self, seed: int | None = None) -> None:
        effective = self._seed if seed is None else seed
        self._rng = np.random.default_rng(effective)

    def measure(self, sample: ChemicalSample, *, limit_mg_l: float) -> ReferenceAssayResult:
        sample.validate()
        if not math.isfinite(limit_mg_l) or limit_mg_l <= 0.0:
            raise BiomolecularValidationError("limit_mg_l must be finite and > 0")
        sigma = max(sample.true_concentration_mg_l * self._rel_noise, self._abs_floor)
        noise = float(self._rng.normal(0.0, sigma)) if sigma > 0.0 else 0.0
        measured = max(0.0, sample.true_concentration_mg_l + noise)
        return ReferenceAssayResult(
            sample_id=sample.sample_id,
            sampled_at_min=sample.sampled_at_min,
            available_at_min=sample.sampled_at_min + self.turnaround_min,
            treated_volume_l=sample.treated_volume_l,
            measured_concentration_mg_l=measured,
            limit_mg_l=float(limit_mg_l),
            exceeds_limit=measured > limit_mg_l,
            measurement_std_mg_l=sigma,
            cost_usd=self.cost_per_sample_usd,
            energy_wh=self.energy_per_sample_wh,
        )
