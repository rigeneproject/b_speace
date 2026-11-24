"""Tests for b_speace.biomolecular cell-free biosensors and reference assays (T003)."""

from __future__ import annotations

import pytest

from b_speace.biomolecular import (
    BiomolecularSensor,
    BiomolecularValidationError,
    BiosensorCalibration,
    CellFreeThresholdSensorAdapter,
    ChemicalSample,
    ReferenceAssayPort,
    SimulatedReferenceAssayAdapter,
)


def test_biomolecular_protocol_conformance() -> None:
    sensor = CellFreeThresholdSensorAdapter(seed=7)
    ref = SimulatedReferenceAssayAdapter(seed=7)
    assert isinstance(sensor, BiomolecularSensor)
    assert isinstance(ref, ReferenceAssayPort)


def test_cell_free_hill_threshold_and_delay() -> None:
    cal = BiosensorCalibration(
        contaminant="Pb2+",
        threshold_mg_l=0.10,
        kd_mg_l=0.10,
        hill_n=4.0,
        incubation_delay_min=6.0,
        noise_std=0.0,
        drift_rate_per_min=0.0,
    )
    sensor = CellFreeThresholdSensorAdapter(calibration=cal, seed=1)

    low_sample = ChemicalSample(
        sample_id="s_low",
        sampled_at_min=10.0,
        treated_volume_l=20.0,
        contaminant="Pb2+",
        true_concentration_mg_l=0.02,
    )
    high_sample = ChemicalSample(
        sample_id="s_high",
        sampled_at_min=15.0,
        treated_volume_l=30.0,
        contaminant="Pb2+",
        true_concentration_mg_l=0.30,
    )

    r_low = sensor.sense(low_sample)
    r_high = sensor.sense(high_sample)

    assert r_low.threshold_crossed is False
    assert r_high.threshold_crossed is True
    assert r_low.available_at_min == pytest.approx(16.0)
    assert r_high.available_at_min == pytest.approx(21.0)
    assert r_high.fluorescence_norm > r_low.fluorescence_norm


def test_cell_free_drift_shifts_sensitivity_and_validation_fails_closed() -> None:
    cal = BiosensorCalibration(
        contaminant="Pb2+",
        threshold_mg_l=0.10,
        kd_mg_l=0.10,
        hill_n=3.0,
        noise_std=0.0,
        drift_rate_per_min=0.01,
    )
    sensor = CellFreeThresholdSensorAdapter(calibration=cal, seed=2)
    sample = ChemicalSample(
        sample_id="s_mid",
        sampled_at_min=5.0,
        treated_volume_l=10.0,
        contaminant="Pb2+",
        true_concentration_mg_l=0.12,
    )
    fresh = sensor.sense(sample, elapsed_campaign_min=0.0)
    drifted = sensor.sense(sample, elapsed_campaign_min=200.0)
    assert fresh.threshold_crossed is True
    assert drifted.fluorescence_norm < fresh.fluorescence_norm
    assert drifted.threshold_crossed is False

    wrong_contaminant = ChemicalSample(
        sample_id="s_bad",
        sampled_at_min=1.0,
        treated_volume_l=2.0,
        contaminant="Atrazine",
        true_concentration_mg_l=0.2,
    )
    with pytest.raises(BiomolecularValidationError):
        sensor.sense(wrong_contaminant)

    with pytest.raises(BiomolecularValidationError):
        BiosensorCalibration(threshold_mg_l=-0.1).validate()


def test_simulated_reference_assay_properties() -> None:
    ref = SimulatedReferenceAssayAdapter(
        turnaround_min=30.0, relative_noise_std=0.0, absolute_noise_floor_mg_l=0.0
    )
    sample = ChemicalSample(
        sample_id="s_ref",
        sampled_at_min=25.0,
        treated_volume_l=50.0,
        contaminant="Pb2+",
        true_concentration_mg_l=0.18,
    )
    res = ref.measure(sample, limit_mg_l=0.10)
    assert res.exceeds_limit is True
    assert res.available_at_min == pytest.approx(55.0)
    assert res.measured_concentration_mg_l == pytest.approx(0.18)
