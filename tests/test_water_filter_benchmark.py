"""Tests for the T003 digital water-treatment filter P-Q-B closed-loop benchmark."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from b_speace.benchmarks.water_filter import (
    AblationMode,
    CandidateRanker,
    ClassicalBaselineRanker,
    DecisionAction,
    FilterTrialConfig,
    FilterTrialController,
    QuantumInteractionRanker,
    WaterFilterTwin,
    run_four_way_ablation,
    run_p_vs_pb_experiment,
    run_parametric_b_sweep,
)
from b_speace.biomolecular import (
    BiosensorCalibration,
    CellFreeThresholdSensorAdapter,
    SimulatedReferenceAssayAdapter,
)
from b_speace.cli import app

runner = CliRunner()


def test_water_filter_twin_separates_kinetics_from_capacity_and_hides_truth() -> None:
    twin = WaterFilterTwin()
    # Public descriptors must NOT expose hidden kinetic or capacity parameters.
    descs = twin.descriptors()
    assert len(descs) == 5
    for d in descs:
        assert not hasattr(d, "q_max_mg_g")
        assert not hasattr(d, "k_a_l_mg_min")
        assert not hasattr(d, "true_binding_energy_kcal_mol")

    # Verify physical archetypes at equal treated volume V_target = 100 L:
    assert twin.oracle_is_compliant("mat_weak_a", twin.flow_high_l_min) is False
    assert twin.oracle_is_compliant("mat_weak_a", twin.flow_low_l_min) is False
    # Kinetically limited material fails at Q_high but passes at Q_low!
    assert twin.oracle_is_compliant("mat_kinetic_c", twin.flow_high_l_min) is False
    assert twin.oracle_is_compliant("mat_kinetic_c", twin.flow_low_l_min) is True
    # Optimal material passes at Q_high!
    assert twin.oracle_is_compliant("mat_optimal_e", twin.flow_high_l_min) is True


def test_experiment_1_p_vs_pb_saves_time_with_causal_provenance_and_determinism() -> None:
    rep_a = run_p_vs_pb_experiment(seeds=(11, 22, 33))
    rep_b = run_p_vs_pb_experiment(seeds=(11, 22, 33))
    assert rep_a.aggregates == rep_b.aggregates

    p_agg = rep_a.aggregates[AblationMode.P_ONLY.value]
    pb_agg = rep_a.aggregates[AblationMode.P_PLUS_B.value]

    # Same accuracy (0% wrong selections), fewer minutes & early stops triggered by B!
    assert p_agg.wrong_selection_rate == 0.0
    assert pb_agg.wrong_selection_rate == 0.0
    assert pb_agg.mean_early_stops > p_agg.mean_early_stops
    assert pb_agg.mean_time_to_confirm_min < p_agg.mean_time_to_confirm_min
    assert pb_agg.mean_treated_volume_l < p_agg.mean_treated_volume_l

    # Verify causal decision provenance shows biosensor_b triggering EARLY_STOP and RETRY_LOW_FLOW.
    pb_trace = rep_a.sample_campaigns[AblationMode.P_PLUS_B.value].decision_trace
    assert any(
        rec.action is DecisionAction.EARLY_STOP and rec.trigger_source == "biosensor_b"
        for rec in pb_trace
    )
    assert any(rec.action is DecisionAction.RETRY_LOW_FLOW for rec in pb_trace)
    assert any(
        rec.action is DecisionAction.CONFIRM_MATERIAL and rec.trigger_source == "reference_assay"
        for rec in pb_trace
    )


def test_simplex_monitor_disables_heavily_drifted_biosensor_fail_closed() -> None:
    twin = WaterFilterTwin()
    # Extreme negative drift forces kd_eff down => frequent false positives against reference.
    bad_cal = BiosensorCalibration(
        contaminant="Pb2+",
        threshold_mg_l=0.10,
        kd_mg_l=0.10,
        hill_n=3.0,
        incubation_delay_min=1.0,
        noise_std=0.0,
        drift_rate_per_min=-0.05,
    )
    sensor = CellFreeThresholdSensorAdapter(calibration=bad_cal, seed=7)
    ref = SimulatedReferenceAssayAdapter(seed=7)
    controller = FilterTrialController(
        config=FilterTrialConfig(
            b_alert_persistence=2,
            max_b_disagreements=1,
            ref_sample_interval_l=20.0,
            b_sample_interval_l=20.0,
        )
    )
    # Run on a compliant optimal material so reference says PASS while drifted B says CROSS.
    optimal_only = WaterFilterTwin(materials=[twin._materials["mat_optimal_e"]])
    res = controller.run_campaign(
        optimal_only,
        mode=AblationMode.P_PLUS_B,
        reference_assay=ref,
        biosensor=sensor,
        seed=7,
    )
    assert res.b_fallback_triggered is True
    assert any(rec.action is DecisionAction.FALLBACK_DISABLE_B for rec in res.decision_trace)


def test_experiment_2_four_way_ablation_and_simplex_q_fallback() -> None:
    assert isinstance(ClassicalBaselineRanker(), CandidateRanker)

    report = run_four_way_ablation(seeds=(11, 22, 33), prefer_qspeace=True)
    for mode in AblationMode:
        assert mode.value in report.aggregates
        assert report.aggregates[mode.value].wrong_selection_rate == 0.0

    p_agg = report.aggregates[AblationMode.P_ONLY.value]
    pq_agg = report.aggregates[AblationMode.P_PLUS_Q.value]
    pqb_agg = report.aggregates[AblationMode.P_PLUS_Q_PLUS_B.value]

    # Q re-ranking surfaces high-affinity candidates first, cutting trials and time dramatically.
    assert pq_agg.mean_trials_started < p_agg.mean_trials_started
    assert pqb_agg.mean_time_to_confirm_min < p_agg.mean_time_to_confirm_min
    assert pqb_agg.fixed_setup_cost_usd > p_agg.fixed_setup_cost_usd

    # Verify Simplex fail-closed fallback when Q uncertainty exceeds max_quantum_uncertainty.
    twin = WaterFilterTwin()
    noisy_q_ranker = QuantumInteractionRanker(
        binding_estimator=lambda mid, rng: twin.estimate_quantum_binding_energy(
            mid, noise_std_kcal_mol=3.0, rng=rng
        ),
        max_quantum_uncertainty=0.5,
        prefer_qspeace=False,
        seed=42,
    )
    assert isinstance(noisy_q_ranker, CandidateRanker)
    ctrl = FilterTrialController()
    fallback_res = ctrl.run_campaign(
        twin,
        mode=AblationMode.P_PLUS_Q,
        reference_assay=SimulatedReferenceAssayAdapter(seed=42),
        ranker=noisy_q_ranker,
        seed=42,
    )
    assert fallback_res.q_fallback_triggered is True
    assert any(
        rec.action is DecisionAction.FALLBACK_CLASSICAL_RANKER
        for rec in fallback_res.decision_trace
    )


def test_parametric_b_sweep_and_cli_benchmark_command(tmp_path) -> None:
    points = run_parametric_b_sweep(
        delays_min=(2.0, 15.0),
        noise_stds=(0.02, 0.20),
        drift_rates=(0.0,),
        seeds=(11, 22),
    )
    assert len(points) == 4
    assert any(p.recommended_for_lab for p in points)

    out_file = tmp_path / "t003_out.json"
    res = runner.invoke(
        app,
        ["benchmark", "water-filter", "--mode", "four-way", "--seeds", "2", "--out", str(out_file)],
    )
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["experiment_name"] == "T003_experiment_2_four_way_PQB"
    assert set(payload["aggregates"].keys()) == {"P", "P+B", "P+Q", "P+Q+B"}
    assert out_file.exists()
