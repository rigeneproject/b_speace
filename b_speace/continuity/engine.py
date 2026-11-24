"""Core T005 functional continuity state-machine engine, oracle, and destination (M0/M1)."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence

import numpy as np

from b_speace.bioelectric import FitzHughNagumoAdapter

from .protocols import ProfileMatcher
from .scoring import ClassicalTrigonometricMatcher, QuantumSingleQubitMatcher
from .types import (
    Command,
    CommittedFrame,
    ContinuityMode,
    ContinuityValidationError,
    DestinationReceipt,
    FaultSpec,
    Grant,
    Observation,
    ReplicaState,
    RunRecord,
    StandbyMode,
    TickTraceEntry,
)


def default_replica_profiles() -> dict[str, float]:
    """Default software extension profiles (pure software profiles, zero actuation)."""
    return {
        "digitale": 0.25,
        "robotica": 0.55,
        "bio_robotica": 0.80,
    }


def closed_form_cold_backlog(fault_tick: int, post_fault_step_j: int, replay_budget: int) -> int:
    """Closed-form cold replica backlog at post-fault step ``j >= 1`` (T005-B §3)."""
    if fault_tick < 0 or post_fault_step_j < 1 or replay_budget < 1:
        raise ContinuityValidationError("invalid arguments to closed_form_cold_backlog")
    return max(0, fault_tick - post_fault_step_j * (replay_budget - 1))


def closed_form_missed_actions(
    *,
    horizon_ticks: int,
    fault_tick: int,
    replay_budget: int,
    standby_mode: StandbyMode,
    all_replicas_disconnected: bool = False,
) -> int:
    """Closed-form deterministic availability oracle (T005-B §3)."""
    if horizon_ticks < 1 or fault_tick < 0 or fault_tick > horizon_ticks or replay_budget < 1:
        raise ContinuityValidationError("invalid arguments to closed_form_missed_actions")
    remaining = horizon_ticks - fault_tick
    if remaining == 0:
        return 0
    if all_replicas_disconnected:
        return remaining
    if standby_mode is StandbyMode.WARM:
        return 0
    if fault_tick == 0:
        return 0
    if replay_budget == 1:
        return remaining
    steps_to_catch_up = math.ceil(fault_tick / (replay_budget - 1))
    return min(remaining, max(0, steps_to_catch_up - 1))


def _aggregate_frame_observation(frame: CommittedFrame) -> float | None:
    vals = [obs.value for obs in frame.observations if obs.valid]
    if not vals:
        return None
    return float(sum(vals) / len(vals))


def _apply_frame_to_context(prev_context: float, frame: CommittedFrame) -> float:
    agg = _aggregate_frame_observation(frame)
    if agg is None:
        return prev_context
    return float(0.5 * (prev_context + agg))


class AppendOnlyFrameLog:
    """Append-only committed frame log with observation deduplication."""

    def __init__(self, session_id: str, expected_channels: Sequence[str]) -> None:
        if not session_id:
            raise ContinuityValidationError("session_id must be non-empty")
        self.session_id: str = session_id
        self._expected: tuple[str, ...] = tuple(expected_channels)
        self._seen_obs_keys: set[tuple[str, str, int]] = set()
        self._frames: list[CommittedFrame] = []

    def commit_next(self, observations: Sequence[Observation]) -> CommittedFrame:
        """Deduplicate and append the next contiguous frame (never mutating past indices)."""
        accepted: list[Observation] = []
        for obs in observations:
            obs.validate()
            if obs.session_id != self.session_id:
                raise ContinuityValidationError(
                    f"observation session {obs.session_id!r} != log session {self.session_id!r}"
                )
            key = (obs.session_id, obs.source_id, obs.local_seq)
            if key in self._seen_obs_keys:
                continue
            self._seen_obs_keys.add(key)
            accepted.append(obs)

        present = tuple(sorted({obs.source_id for obs in accepted if obs.valid}))
        if not present:
            quality = "all_missing"
        elif set(present) >= set(self._expected):
            quality = "complete"
        else:
            quality = "partial_dropout"

        frame = CommittedFrame(
            session_id=self.session_id,
            frame_index=len(self._frames),
            present_channels_mask=present,
            observations=tuple(accepted),
            quality_flag=quality,
        )
        self._frames.append(frame)
        return frame

    def frames(self) -> tuple[CommittedFrame, ...]:
        return tuple(self._frames)

    def frame_at(self, index: int) -> CommittedFrame:
        return self._frames[index]

    def __len__(self) -> int:
        return len(self._frames)


class IndependentPrefixOracle:
    """Independent prefix state oracle verifying replica reconstruction (T005-B §2)."""

    def recompute_context(
        self, frames: Sequence[CommittedFrame], *, initial_context: float = 0.5
    ) -> float:
        ctx = float(initial_context)
        for frame in frames:
            ctx = _apply_frame_to_context(ctx, frame)
        return ctx


class VirtualDestinationEndpoint:
    """Virtual command destination enforcing monotonic epochs & tick idempotency (H2)."""

    def __init__(self) -> None:
        self._current_epoch: dict[str, int] = {}
        self._current_holder: dict[str, str] = {}
        self._applied_by_tick: dict[tuple[str, int], DestinationReceipt] = {}
        self._receipts: list[DestinationReceipt] = []
        self._effects_applied: int = 0

    def advance_epoch(self, session_id: str, new_epoch: int, holder_id: str) -> None:
        prev = self._current_epoch.get(session_id, -1)
        if new_epoch <= prev:
            raise ContinuityValidationError(
                f"new_epoch {new_epoch} must exceed current epoch {prev}"
            )
        if not holder_id:
            raise ContinuityValidationError("holder_id must be non-empty")
        self._current_epoch[session_id] = new_epoch
        self._current_holder[session_id] = holder_id

    def apply(self, command: Command) -> DestinationReceipt:
        command.validate()
        cur_epoch = self._current_epoch.get(command.session_id, -1)
        cur_holder = self._current_holder.get(command.session_id)

        if command.epoch < cur_epoch:
            rec = DestinationReceipt(
                session_id=command.session_id,
                tick=command.tick,
                action_id=command.action_id,
                epoch=command.epoch,
                holder_id=command.holder_id,
                accepted=False,
                deduplicated=False,
                reason="stale_epoch",
            )
            self._receipts.append(rec)
            return rec

        if command.epoch > cur_epoch or command.holder_id != cur_holder:
            rec = DestinationReceipt(
                session_id=command.session_id,
                tick=command.tick,
                action_id=command.action_id,
                epoch=command.epoch,
                holder_id=command.holder_id,
                accepted=False,
                deduplicated=False,
                reason="unauthorized_holder",
            )
            self._receipts.append(rec)
            return rec

        tick_key = (command.session_id, command.tick)
        existing = self._applied_by_tick.get(tick_key)
        if existing is not None:
            if existing.action_id == command.action_id:
                # Idempotent retry: retransmit confirmation without duplicating effect.
                retry_rec = DestinationReceipt(
                    session_id=command.session_id,
                    tick=command.tick,
                    action_id=command.action_id,
                    epoch=command.epoch,
                    holder_id=command.holder_id,
                    accepted=True,
                    deduplicated=True,
                    reason="idempotent_retry",
                )
                self._receipts.append(retry_rec)
                return retry_rec
            conflict_rec = DestinationReceipt(
                session_id=command.session_id,
                tick=command.tick,
                action_id=command.action_id,
                epoch=command.epoch,
                holder_id=command.holder_id,
                accepted=False,
                deduplicated=False,
                reason="incompatible_action_id_for_tick",
            )
            self._receipts.append(conflict_rec)
            return conflict_rec

        accepted_rec = DestinationReceipt(
            session_id=command.session_id,
            tick=command.tick,
            action_id=command.action_id,
            epoch=command.epoch,
            holder_id=command.holder_id,
            accepted=True,
            deduplicated=False,
            reason="accepted",
        )
        self._applied_by_tick[tick_key] = accepted_rec
        self._receipts.append(accepted_rec)
        self._effects_applied += 1
        return accepted_rec

    def applied_count(self) -> int:
        return self._effects_applied

    def receipts(self) -> tuple[DestinationReceipt, ...]:
        return tuple(self._receipts)


def deliver_frame_to_replica(
    replica: ReplicaState, frame: CommittedFrame, *, max_apply: int = 1
) -> int:
    """Deliver a frame (potentially out of order) and apply contiguous frames up to ``max_apply``.

    Returns the number of frames actually applied to ``replica.context``.
    Frames earlier than ``replica.next_frame_cursor`` are ignored (zero double updates);
    future frames are buffered while ``next_frame_cursor`` halts at the first gap.
    """
    if frame.frame_index < replica.next_frame_cursor:
        return 0
    if frame.frame_index not in replica.buffered_frames:
        replica.buffered_frames[frame.frame_index] = frame

    applied = 0
    while applied < max_apply and replica.next_frame_cursor in replica.buffered_frames:
        nxt = replica.buffered_frames.pop(replica.next_frame_cursor)
        replica.context = _apply_frame_to_context(replica.context, nxt)
        replica.next_frame_cursor += 1
        replica.updates_applied += 1
        applied += 1
    return applied


def _hash_frames(frames: Sequence[CommittedFrame]) -> str:
    canonical = [
        {
            "idx": f.frame_index,
            "mask": list(f.present_channels_mask),
            "obs": [
                (o.source_id, o.local_seq, o.acquired_tick, round(o.value, 12), o.valid)
                for o in f.observations
            ],
        }
        for f in frames
    ]
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class ContinuityEngine:
    """Deterministic single-session continuity and fault-recovery simulator (M0/M1)."""

    def __init__(
        self,
        profiles: Mapping[str, float] | None = None,
        *,
        fhn_input_gain: float = 15.0,
    ) -> None:
        profs = dict(profiles) if profiles is not None else default_replica_profiles()
        if not profs:
            raise ContinuityValidationError("profiles must be non-empty")
        for rid, val in profs.items():
            if not rid or not math.isfinite(val) or not (0.0 <= val <= 1.0):
                raise ContinuityValidationError(f"invalid profile ({rid!r}: {val!r})")
        self._profiles: dict[str, float] = profs
        self._fhn_gain: float = float(fhn_input_gain)

    def generate_session_frames(
        self,
        *,
        session_id: str,
        horizon_ticks: int,
        seed: int,
        include_b: bool,
    ) -> tuple[CommittedFrame, ...]:
        """Pre-generate deterministic committed frames shared across warm/cold & Q on/off pairs."""
        rng = np.random.Generator(np.random.PCG64(seed))
        expected_channels = (
            ("digital", "robotic", "bio_fhn") if include_b else ("digital", "robotic")
        )
        log = AppendOnlyFrameLog(session_id=session_id, expected_channels=expected_channels)
        fhn = FitzHughNagumoAdapter(num_channels=1, dt_ms=0.25, seed=seed) if include_b else None

        for t in range(horizon_ticks):
            base = 0.5 + 0.30 * math.sin(2.0 * math.pi * t / max(horizon_ticks, 1))
            val_dig = float(np.clip(base + rng.normal(0.0, 0.08), 0.0, 1.0))
            val_rob = float(np.clip(base + rng.normal(0.0, 0.06), 0.0, 1.0))
            obs_list: list[Observation] = [
                Observation(
                    session_id=session_id,
                    source_id="digital",
                    local_seq=t,
                    acquired_tick=t,
                    delivered_tick=t,
                    value=val_dig,
                    valid=True,
                ),
                Observation(
                    session_id=session_id,
                    source_id="robotic",
                    local_seq=t,
                    acquired_tick=t,
                    delivered_tick=t,
                    value=val_rob,
                    valid=True,
                ),
            ]
            if fhn is not None:
                # B channel derives strictly from digital input via FitzHugh-Nagumo.
                frame_bio = fhn.step([val_dig * self._fhn_gain])
                # Normalize FHN membrane potential [-100, +60] mV into [0, 1].
                v_mv = frame_bio.potentials_mv[0]
                b_norm = float(np.clip((v_mv + 100.0) / 160.0, 0.0, 1.0))
                obs_list.append(
                    Observation(
                        session_id=session_id,
                        source_id="bio_fhn",
                        local_seq=t,
                        acquired_tick=t,
                        delivered_tick=t,
                        value=b_norm,
                        valid=True,
                    )
                )
            log.commit_next(obs_list)
        return log.frames()

    def run(
        self,
        *,
        mode: ContinuityMode = ContinuityMode.P,
        fault: FaultSpec | None = None,
        horizon_ticks: int = 24,
        seed: int = 42,
        session_id: str = "t005_sess",
        pre_generated_frames: Sequence[CommittedFrame] | None = None,
        matcher_override: ProfileMatcher | None = None,
    ) -> RunRecord:
        spec = fault or FaultSpec()
        spec.validate(horizon_ticks=horizon_ticks)

        include_b = mode in (ContinuityMode.P_B, ContinuityMode.P_Q_B)
        uses_q = mode in (ContinuityMode.P_Q, ContinuityMode.P_Q_B)
        matcher: ProfileMatcher
        if matcher_override is not None:
            matcher = matcher_override
        elif uses_q:
            matcher = QuantumSingleQubitMatcher()
        else:
            matcher = ClassicalTrigonometricMatcher()

        frames = (
            tuple(pre_generated_frames)
            if pre_generated_frames is not None
            else self.generate_session_frames(
                session_id=session_id,
                horizon_ticks=horizon_ticks,
                seed=seed,
                include_b=include_b,
            )
        )
        if len(frames) != horizon_ticks:
            raise ContinuityValidationError(
                f"pre_generated_frames length {len(frames)} != horizon_ticks {horizon_ticks}"
            )
        input_hash = _hash_frames(frames)

        oracle = IndependentPrefixOracle()
        destination = VirtualDestinationEndpoint()
        primary = ReplicaState(replica_id="primary", profile_score=0.5)
        replicas: dict[str, ReplicaState] = {
            rid: ReplicaState(replica_id=rid, profile_score=prof)
            for rid, prof in self._profiles.items()
        }

        epoch = 0
        grant: Grant | None = Grant(
            session_id=session_id, epoch=epoch, holder_id="primary", issued_at_tick=0
        )
        destination.advance_epoch(session_id, epoch, "primary")

        first_recovery_tick: int | None = None
        missed_actions = 0
        bg_updates_before_fault = 0
        authority_violations = 0
        duplicate_effects = 0
        max_ctx_error = 0.0
        winner_replica: str | None = None
        rejections: list[DestinationReceipt] = []
        trace: list[TickTraceEntry] = []
        primary_failed = False

        for tick in range(horizon_ticks):
            # Step 1: Fault injection precedes frame `fault_tick`.
            if not primary_failed and tick == spec.fault_tick:
                primary_failed = True
                primary.available = False
                epoch += 1
                grant = None

            # Step 2: Frame `tick` commits (from pre-generated append-only log).
            frame = frames[tick]
            oracle_ctx = oracle.recompute_context(frames[: tick + 1])

            # Step 3: Reachable replicas replay frames up to their replay budget.
            if not primary_failed:
                deliver_frame_to_replica(primary, frame, max_apply=1)
                if spec.standby_mode is StandbyMode.WARM and not spec.all_replicas_disconnected:
                    for rid, rep in replicas.items():
                        if rid == spec.lagging_replica_id:
                            continue
                        bg_updates_before_fault += deliver_frame_to_replica(
                            rep, frame, max_apply=spec.replay_budget
                        )
            else:
                if not spec.all_replicas_disconnected:
                    for rid, rep in replicas.items():
                        if rid == spec.lagging_replica_id:
                            continue
                        budget_left = spec.replay_budget
                        while budget_left > 0 and rep.next_frame_cursor <= tick:
                            nxt_frame = frames[rep.next_frame_cursor]
                            applied = deliver_frame_to_replica(rep, nxt_frame, max_apply=1)
                            if applied == 0:
                                break
                            budget_left -= applied

            # Step 4 & 5: Elect eligible up-to-date replica if no active holder, then emit command.
            active_replica: ReplicaState | None = None
            if not primary_failed and grant is not None:
                active_replica = primary
            else:
                if grant is None:
                    eligible = {
                        rid: rep.profile_score
                        for rid, rep in replicas.items()
                        if rep.available
                        and not spec.all_replicas_disconnected
                        and rep.next_frame_cursor == tick + 1
                    }
                    if eligible:
                        # All eligible replicas hold identical prefix context; verify against first.
                        sample_ctx = replicas[next(iter(eligible))].context
                        chosen_id, _score, _all = matcher.select_winner(sample_ctx, eligible)
                        grant = Grant(
                            session_id=session_id,
                            epoch=epoch,
                            holder_id=chosen_id,
                            issued_at_tick=tick,
                        )
                        destination.advance_epoch(session_id, epoch, chosen_id)
                        winner_replica = chosen_id
                        if first_recovery_tick is None:
                            first_recovery_tick = tick
                if grant is not None:
                    active_replica = replicas[grant.holder_id]

            if active_replica is None or grant is None:
                missed_actions += 1
                trace.append(
                    TickTraceEntry(
                        tick=tick,
                        frame_index=frame.frame_index,
                        epoch=epoch,
                        holder_id=None,
                        elected_replica=None,
                        command_action_id=None,
                        accepted=False,
                        reason="no_eligible_replica",
                        context_after=None,
                        oracle_context=oracle_ctx,
                    )
                )
                continue

            action_id = f"{session_id}:e{grant.epoch}:t{tick}:{grant.holder_id}"
            cmd = Command(
                session_id=session_id,
                epoch=grant.epoch,
                holder_id=grant.holder_id,
                tick=tick,
                action_id=action_id,
                targets=(grant.holder_id,),
                context_estimate=active_replica.context,
            )
            receipt = destination.apply(cmd)
            if not receipt.accepted:
                authority_violations += 1
                rejections.append(receipt)
            else:
                active_replica.last_confirmed_action = action_id

            ctx_err = abs(active_replica.context - oracle_ctx)
            if ctx_err > max_ctx_error:
                max_ctx_error = ctx_err

            trace.append(
                TickTraceEntry(
                    tick=tick,
                    frame_index=frame.frame_index,
                    epoch=grant.epoch,
                    holder_id=grant.holder_id,
                    elected_replica=winner_replica if primary_failed else None,
                    command_action_id=action_id,
                    accepted=receipt.accepted,
                    reason=receipt.reason,
                    context_after=active_replica.context,
                    oracle_context=oracle_ctx,
                )
            )

        expected_missed = closed_form_missed_actions(
            horizon_ticks=horizon_ticks,
            fault_tick=spec.fault_tick,
            replay_budget=spec.replay_budget,
            standby_mode=spec.standby_mode,
            all_replicas_disconnected=spec.all_replicas_disconnected,
        )
        expected_effects = horizon_ticks - missed_actions
        if destination.applied_count() != expected_effects:
            duplicate_effects = abs(destination.applied_count() - expected_effects)

        return RunRecord(
            session_id=session_id,
            input_hash=input_hash,
            seed=seed,
            mode=mode,
            standby_mode=spec.standby_mode,
            fault_tick=spec.fault_tick,
            replay_budget=spec.replay_budget,
            horizon_ticks=horizon_ticks,
            first_recovery_tick=first_recovery_tick,
            missed_actions=missed_actions,
            expected_missed_actions=expected_missed,
            background_updates_before_fault=bg_updates_before_fault,
            authority_violations=authority_violations,
            duplicate_effects=duplicate_effects,
            max_context_error=max_ctx_error,
            winner_replica=winner_replica,
            rejections=tuple(rejections),
            trace=tuple(trace),
        )
