"""M1 campaign runner, H2 fault-injection drills, and standard evidence bundles (T005-B)."""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .engine import (
    AppendOnlyFrameLog,
    ContinuityEngine,
    IndependentPrefixOracle,
    VirtualDestinationEndpoint,
    deliver_frame_to_replica,
)
from .scoring import H4EquivalenceReport, QuantumSingleQubitMatcher, verify_h4_equivalence_grid
from .types import (
    Command,
    ContinuityMode,
    ContinuityValidationError,
    FaultSpec,
    Observation,
    ReplicaState,
    RunRecord,
    StandbyMode,
)


@dataclass(frozen=True)
class H2DrillOutcome:
    """Single fault-injection drill outcome from T005-B §3."""

    drill_name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class H2DrillReport:
    """Aggregate report of all mandatory H2 fault-injection drills."""

    drills: tuple[H2DrillOutcome, ...]

    @property
    def all_passed(self) -> bool:
        return all(d.passed for d in self.drills)


@dataclass(frozen=True)
class M1CampaignSummary:
    """Summary of the complete T005-B M1 regression matrix, H2 drills, and H4 check."""

    seed: int
    horizon_ticks: int
    total_matrix_runs: int
    oracle_exact_matches: int
    q_on_off_exact_matches: int
    total_authority_violations: int
    total_duplicate_effects: int
    max_context_error: float
    h2_drills: H2DrillReport
    h4_equivalence: H4EquivalenceReport
    runs: tuple[RunRecord, ...]

    @property
    def all_passed(self) -> bool:
        return (
            self.oracle_exact_matches == self.total_matrix_runs
            and self.total_authority_violations == 0
            and self.total_duplicate_effects == 0
            and self.max_context_error <= 1e-12
            and self.h2_drills.all_passed
            and self.h4_equivalence.all_passed
        )


def run_h2_fault_drills() -> H2DrillReport:
    """Execute all 5 mandatory fault-injection drills from T005-B §3."""
    drills: list[H2DrillOutcome] = []

    # Drill 1: Late command with stale epoch (including after same-holder re-assignment).
    dest = VirtualDestinationEndpoint()
    dest.advance_epoch("s1", 0, "robotica")
    dest.advance_epoch("s1", 1, "digitale")
    dest.advance_epoch("s1", 2, "robotica")  # re-assigned to same replica_id!
    stale_cmd = Command(
        session_id="s1",
        epoch=0,
        holder_id="robotica",
        tick=3,
        action_id="act_stale",
        targets=("robotica",),
        context_estimate=0.5,
    )
    stale_rec = dest.apply(stale_cmd)
    valid_cmd = Command(
        session_id="s1",
        epoch=2,
        holder_id="robotica",
        tick=3,
        action_id="act_valid",
        targets=("robotica",),
        context_estimate=0.5,
    )
    valid_rec = dest.apply(valid_cmd)
    drills.append(
        H2DrillOutcome(
            drill_name="stale_epoch_after_same_holder_reassignment",
            passed=(
                not stale_rec.accepted
                and stale_rec.reason == "stale_epoch"
                and valid_rec.accepted
                and dest.applied_count() == 1
            ),
            detail=f"stale_reason={stale_rec.reason}, valid_accepted={valid_rec.accepted}",
        )
    )

    # Drill 2: Duplicate command / lost confirmation + conflicting ID rejection on same tick.
    retry_rec = dest.apply(valid_cmd)
    conflict_cmd = Command(
        session_id="s1",
        epoch=2,
        holder_id="robotica",
        tick=3,
        action_id="act_conflicting",
        targets=("robotica",),
        context_estimate=0.5,
    )
    conflict_rec = dest.apply(conflict_cmd)
    drills.append(
        H2DrillOutcome(
            drill_name="duplicate_retry_idempotency_and_conflict_rejection",
            passed=(
                retry_rec.accepted
                and retry_rec.deduplicated
                and not conflict_rec.accepted
                and conflict_rec.reason == "incompatible_action_id_for_tick"
                and dest.applied_count() == 1
            ),
            detail=(
                f"retry_dedup={retry_rec.deduplicated}, conflict_reason={conflict_rec.reason}, "
                f"applied={dest.applied_count()}"
            ),
        )
    )

    # Drill 3: Out-of-order frame delivery, pause, and rejoin with zero double updates.
    log = AppendOnlyFrameLog("s_ooo", ("digital",))
    for t, v in enumerate((0.2, 0.8, 0.4, 0.6)):
        log.commit_next([Observation("s_ooo", "digital", t, t, t, v, True)])
    rep = ReplicaState(replica_id="r_ooo", profile_score=0.5)
    deliver_frame_to_replica(rep, log.frame_at(0), max_apply=1)
    # Deliver frame 2 out of order (gap at frame 1): cursor MUST halt at 1!
    applied_ooo = deliver_frame_to_replica(rep, log.frame_at(2), max_apply=2)
    cursor_at_gap = rep.next_frame_cursor
    # Re-deliver frame 0 (duplicate past frame): MUST be ignored (0 updates).
    applied_dup = deliver_frame_to_replica(rep, log.frame_at(0), max_apply=2)
    # Deliver missing frame 1: drains frames 1 and buffered 2 cleanly!
    applied_rejoin = deliver_frame_to_replica(rep, log.frame_at(1), max_apply=4)
    oracle_ctx = IndependentPrefixOracle().recompute_context(log.frames()[:3])
    drills.append(
        H2DrillOutcome(
            drill_name="out_of_order_gap_cursor_and_rejoin",
            passed=(
                applied_ooo == 0
                and cursor_at_gap == 1
                and applied_dup == 0
                and applied_rejoin == 2
                and rep.next_frame_cursor == 3
                and rep.updates_applied == 3
                and abs(rep.context - oracle_ctx) <= 1e-12
            ),
            detail=(
                f"cursor_at_gap={cursor_at_gap}, final_cursor={rep.next_frame_cursor}, "
                f"updates={rep.updates_applied}"
            ),
        )
    )

    # Drill 4: Profile-favored lagging replica excluded + all replicas disconnected.
    eng = ContinuityEngine()
    base_warm = eng.run(
        mode=ContinuityMode.P,
        fault=FaultSpec(fault_tick=8, replay_budget=2, standby_mode=StandbyMode.WARM),
        horizon_ticks=24,
        seed=42,
    )
    favored = base_warm.winner_replica or "robotica"
    lagging_run = eng.run(
        mode=ContinuityMode.P,
        fault=FaultSpec(
            fault_tick=8,
            replay_budget=2,
            standby_mode=StandbyMode.WARM,
            lagging_replica_id=favored,
        ),
        horizon_ticks=24,
        seed=42,
    )
    blackout_run = eng.run(
        mode=ContinuityMode.P,
        fault=FaultSpec(
            fault_tick=8,
            replay_budget=2,
            standby_mode=StandbyMode.WARM,
            all_replicas_disconnected=True,
        ),
        horizon_ticks=24,
        seed=42,
    )
    drills.append(
        H2DrillOutcome(
            drill_name="lagging_favored_excluded_and_total_blackout",
            passed=(
                lagging_run.winner_replica is not None
                and lagging_run.winner_replica != favored
                and blackout_run.first_recovery_tick is None
                and blackout_run.missed_actions == 16
            ),
            detail=(
                f"favored={favored}, elected_when_lagging={lagging_run.winner_replica}, "
                f"blackout_missed={blackout_run.missed_actions}"
            ),
        )
    )

    # Drill 5: Q unavailable classical fallback + non-finite rejection + lexicographical tie.
    q_down = QuantumSingleQubitMatcher(backend_unavailable=True)
    w_tie, _score, _all = q_down.select_winner(0.5, {"robotica": 0.3, "bio_robotica": 0.7})
    non_finite_rejected = False
    try:
        q_down.score(float("inf"), 0.5)
    except ContinuityValidationError:
        non_finite_rejected = True
    drills.append(
        H2DrillOutcome(
            drill_name="q_unavailable_fallback_non_finite_and_tie_break",
            passed=(w_tie == "bio_robotica" and q_down.fallback_count >= 2 and non_finite_rejected),
            detail=f"tie_winner={w_tie}, fallbacks={q_down.fallback_count}",
        )
    )

    return H2DrillReport(drills=tuple(drills))


def run_m1_regression_matrix(
    *,
    seed: int = 42,
    horizon_ticks: int = 24,
    fault_ticks: Sequence[int] = (1, 2, 7, 8, 17),
    replay_budgets: Sequence[int] = (1, 2, 3, 4, 8),
) -> M1CampaignSummary:
    """Execute T005-B §3 M1 50-case deterministic matrix across P, P+Q, P+B, P+Q+B."""
    engine = ContinuityEngine()
    frames_no_b = engine.generate_session_frames(
        session_id="m1_no_b", horizon_ticks=horizon_ticks, seed=seed, include_b=False
    )
    frames_with_b = engine.generate_session_frames(
        session_id="m1_with_b", horizon_ticks=horizon_ticks, seed=seed, include_b=True
    )

    runs: list[RunRecord] = []
    q_pairs: dict[tuple[bool, int, int, StandbyMode], dict[bool, RunRecord]] = {}

    for mode in (ContinuityMode.P, ContinuityMode.P_Q, ContinuityMode.P_B, ContinuityMode.P_Q_B):
        inc_b = mode in (ContinuityMode.P_B, ContinuityMode.P_Q_B)
        uses_q = mode in (ContinuityMode.P_Q, ContinuityMode.P_Q_B)
        shared_frames = frames_with_b if inc_b else frames_no_b

        for f_tick in fault_ticks:
            for budget in replay_budgets:
                for standby in (StandbyMode.WARM, StandbyMode.COLD):
                    spec = FaultSpec(
                        fault_tick=f_tick,
                        replay_budget=budget,
                        standby_mode=standby,
                    )
                    rec = engine.run(
                        mode=mode,
                        fault=spec,
                        horizon_ticks=horizon_ticks,
                        seed=seed,
                        session_id=f"{mode.value}_f{f_tick}_r{budget}_{standby.value}",
                        pre_generated_frames=shared_frames,
                    )
                    runs.append(rec)
                    q_pairs.setdefault((inc_b, f_tick, budget, standby), {})[uses_q] = rec

    oracle_matches = sum(1 for r in runs if r.missed_actions == r.expected_missed_actions)
    q_exact = 0
    for pair in q_pairs.values():
        r_off = pair[False]
        r_on = pair[True]
        if (
            r_off.winner_replica == r_on.winner_replica
            and r_off.missed_actions == r_on.missed_actions
            and r_off.first_recovery_tick == r_on.first_recovery_tick
            and abs(r_off.max_context_error - r_on.max_context_error) <= 1e-12
        ):
            q_exact += 1

    h2_drills = run_h2_fault_drills()
    h4_equiv = verify_h4_equivalence_grid(step=0.01, tol=1e-12)

    return M1CampaignSummary(
        seed=seed,
        horizon_ticks=horizon_ticks,
        total_matrix_runs=len(runs),
        oracle_exact_matches=oracle_matches,
        q_on_off_exact_matches=q_exact,
        total_authority_violations=sum(r.authority_violations for r in runs),
        total_duplicate_effects=sum(r.duplicate_effects for r in runs),
        max_context_error=max((r.max_context_error for r in runs), default=0.0),
        h2_drills=h2_drills,
        h4_equivalence=h4_equiv,
        runs=tuple(runs),
    )


def write_campaign_bundle(output_dir: Path, summary: M1CampaignSummary) -> dict[str, Path]:
    """Write standard T005-B campaign files: manifest.json, trials.jsonl, trace.jsonl, summary.json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    config_payload = {
        "schema": "t005.m1.campaign.v1",
        "seed": summary.seed,
        "horizon_ticks": summary.horizon_ticks,
        "total_matrix_runs": summary.total_matrix_runs,
    }
    config_hash = hashlib.sha256(
        json.dumps(config_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    manifest = {
        "schema": "t005.manifest.v1",
        "config_sha256": config_hash,
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        "rng": "PCG64",
        "seed": summary.seed,
        "horizon_ticks": summary.horizon_ticks,
        "total_matrix_runs": summary.total_matrix_runs,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    trials_path = output_dir / "trials.jsonl"
    with trials_path.open("w", encoding="utf-8") as fh:
        for r in summary.runs:
            row = {
                "session_id": r.session_id,
                "input_hash": r.input_hash,
                "mode": r.mode.value,
                "standby_mode": r.standby_mode.value,
                "fault_tick": r.fault_tick,
                "replay_budget": r.replay_budget,
                "first_recovery_tick": r.first_recovery_tick,
                "missed_actions": r.missed_actions,
                "expected_missed_actions": r.expected_missed_actions,
                "background_updates_before_fault": r.background_updates_before_fault,
                "authority_violations": r.authority_violations,
                "duplicate_effects": r.duplicate_effects,
                "max_context_error": r.max_context_error,
                "winner_replica": r.winner_replica,
            }
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    # Write detailed tick traces for the canonical f=8, r=2 runs across modes.
    trace_path = output_dir / "trace.jsonl"
    with trace_path.open("w", encoding="utf-8") as fh:
        for r in summary.runs:
            if r.fault_tick == 8 and r.replay_budget == 2:
                for entry in r.trace:
                    row_t: dict[str, Any] = {
                        "session_id": r.session_id,
                        "mode": r.mode.value,
                        "standby_mode": r.standby_mode.value,
                        **asdict(entry),
                    }
                    fh.write(json.dumps(row_t, sort_keys=True) + "\n")

    summary_payload = {
        "schema": "t005.summary.v1",
        "all_passed": summary.all_passed,
        "seed": summary.seed,
        "horizon_ticks": summary.horizon_ticks,
        "total_matrix_runs": summary.total_matrix_runs,
        "oracle_exact_matches": summary.oracle_exact_matches,
        "q_on_off_exact_matches": summary.q_on_off_exact_matches,
        "total_authority_violations": summary.total_authority_violations,
        "total_duplicate_effects": summary.total_duplicate_effects,
        "max_context_error": summary.max_context_error,
        "h2_drills": {
            "all_passed": summary.h2_drills.all_passed,
            "drills": [asdict(d) for d in summary.h2_drills.drills],
        },
        "h4_equivalence": {
            **asdict(summary.h4_equivalence),
            "all_passed": summary.h4_equivalence.all_passed,
        },
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "manifest": manifest_path,
        "trials": trials_path,
        "trace": trace_path,
        "summary": summary_path,
    }
