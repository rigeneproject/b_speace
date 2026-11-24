"""Tests for T005 M0/M1 functional continuity engine, H1/H2/H4 oracles, and CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from b_speace.cli import app
from b_speace.continuity import (
    AppendOnlyFrameLog,
    ClassicalTrigonometricMatcher,
    ContinuityEngine,
    ContinuityMode,
    ContinuityValidationError,
    DestinationEndpointPort,
    FaultSpec,
    IndependentPrefixOracle,
    Observation,
    ProfileMatcher,
    QuantumSingleQubitMatcher,
    StandbyMode,
    StateOraclePort,
    VirtualDestinationEndpoint,
    closed_form_cold_backlog,
    closed_form_missed_actions,
    run_h2_fault_drills,
    run_m1_regression_matrix,
    verify_h4_equivalence_grid,
    write_campaign_bundle,
)

runner = CliRunner()


def test_continuity_protocol_conformance() -> None:
    assert isinstance(ClassicalTrigonometricMatcher(), ProfileMatcher)
    assert isinstance(QuantumSingleQubitMatcher(), ProfileMatcher)
    assert isinstance(VirtualDestinationEndpoint(), DestinationEndpointPort)
    assert isinstance(IndependentPrefixOracle(), StateOraclePort)


def test_canonical_warm_vs_cold_f8_r2_matches_analytical_oracle() -> None:
    engine = ContinuityEngine()
    warm = engine.run(
        mode=ContinuityMode.P,
        fault=FaultSpec(fault_tick=8, replay_budget=2, standby_mode=StandbyMode.WARM),
        horizon_ticks=24,
        seed=42,
    )
    cold = engine.run(
        mode=ContinuityMode.P,
        fault=FaultSpec(fault_tick=8, replay_budget=2, standby_mode=StandbyMode.COLD),
        horizon_ticks=24,
        seed=42,
    )

    assert warm.input_hash == cold.input_hash
    assert warm.first_recovery_tick == 8
    assert warm.missed_actions == 0
    assert warm.background_updates_before_fault == 24  # 3 replicas * 8 pre-fault frames
    assert warm.authority_violations == 0
    assert warm.duplicate_effects == 0
    assert warm.max_context_error <= 1e-12

    assert cold.first_recovery_tick == 15
    assert cold.missed_actions == 7
    assert cold.expected_missed_actions == 7
    assert cold.background_updates_before_fault == 0
    assert cold.authority_violations == 0
    assert cold.duplicate_effects == 0
    assert cold.max_context_error <= 1e-12

    # Verify closed-form backlog sequence for f=8, r=2: j=1..8 -> 7,6,5,4,3,2,1,0.
    assert [closed_form_cold_backlog(8, j, 2) for j in range(1, 9)] == [7, 6, 5, 4, 3, 2, 1, 0]
    assert (
        closed_form_missed_actions(
            horizon_ticks=24, fault_tick=8, replay_budget=1, standby_mode=StandbyMode.COLD
        )
        == 16
    )


def test_append_only_log_deduplication_and_dropout_policy() -> None:
    log = AppendOnlyFrameLog("s_drop", ("digital", "robotic"))
    # Duplicate (session, source, local_seq) must be deduplicated within frame.
    f0 = log.commit_next(
        [
            Observation("s_drop", "digital", 0, 0, 0, 0.8, True),
            Observation("s_drop", "digital", 0, 0, 0, 0.8, True),
            Observation("s_drop", "robotic", 0, 0, 0, 0.4, True),
        ]
    )
    assert f0.quality_flag == "complete"
    assert len(f0.observations) == 2

    # Partial dropout: only digital present.
    f1 = log.commit_next([Observation("s_drop", "digital", 1, 1, 1, 0.2, True)])
    assert f1.quality_flag == "partial_dropout"
    assert f1.present_channels_mask == ("digital",)

    # All missing: context holds previous value.
    f2 = log.commit_next([Observation("s_drop", "digital", 2, 2, 2, 0.0, False)])
    assert f2.quality_flag == "all_missing"

    oracle = IndependentPrefixOracle()
    c0 = oracle.recompute_context([f0])
    c1 = oracle.recompute_context([f0, f1])
    c2 = oracle.recompute_context([f0, f1, f2])
    assert c0 == pytest.approx(0.5 * (0.5 + 0.6))
    assert c1 == pytest.approx(0.5 * (c0 + 0.2))
    assert c2 == pytest.approx(c1)

    with pytest.raises(ContinuityValidationError):
        Observation("s_drop", "digital", 3, 5, 4, 0.5, True).validate()


def test_h4_full_analytical_equivalence_grid() -> None:
    rep = verify_h4_equivalence_grid(step=0.01, tol=1e-12)
    assert rep.grid_points_tested == 101 * 101
    assert rep.max_abs_error <= 1e-12
    assert rep.all_passed is True
    assert rep.classical_sufficient is True


def test_h2_all_mandatory_fault_drills_pass() -> None:
    report = run_h2_fault_drills()
    assert len(report.drills) == 5
    assert report.all_passed is True


def test_m1_full_200_run_regression_matrix_and_bundle(tmp_path: Path) -> None:
    summary = run_m1_regression_matrix(seed=42, horizon_ticks=24)
    # 5 fault ticks * 5 replay budgets * 2 standby modes * 4 P-Q-B modes = 200 runs.
    assert summary.total_matrix_runs == 200
    assert summary.oracle_exact_matches == 200
    assert summary.q_on_off_exact_matches == 100
    assert summary.total_authority_violations == 0
    assert summary.total_duplicate_effects == 0
    assert summary.max_context_error <= 1e-12
    assert summary.all_passed is True

    files = write_campaign_bundle(tmp_path / "m1_bundle", summary)
    for key in ("manifest", "trials", "trace", "summary"):
        assert files[key].exists()
    parsed_summary = json.loads(files["summary"].read_text(encoding="utf-8"))
    assert parsed_summary["all_passed"] is True
    assert parsed_summary["total_matrix_runs"] == 200
    trial_lines = files["trials"].read_text(encoding="utf-8").strip().splitlines()
    assert len(trial_lines) == 200


def test_continuity_cli_run_and_evaluate(tmp_path: Path) -> None:
    res_run = runner.invoke(
        app,
        [
            "continuity",
            "run",
            "--mode",
            "P+Q+B",
            "--standby",
            "cold",
            "--fault-tick",
            "8",
            "--replay-budget",
            "2",
        ],
    )
    assert res_run.exit_code == 0
    run_payload = json.loads(res_run.stdout)
    assert run_payload["missed_actions"] == 7
    assert run_payload["first_recovery_tick"] == 15
    assert run_payload["authority_violations"] == 0

    out_dir = tmp_path / "cli_m1"
    res_eval = runner.invoke(app, ["continuity", "evaluate", "--output", str(out_dir)])
    assert res_eval.exit_code == 0
    eval_payload = json.loads(res_eval.stdout)
    assert eval_payload["all_passed"] is True
    assert eval_payload["total_matrix_runs"] == 200
    assert (out_dir / "summary.json").exists()
