"""Classical controller P with closed-loop B/Q coordination and Simplex fallback (T003)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum

from b_speace.biomolecular import (
    BiomolecularSensor,
    BiosensorReading,
    ReferenceAssayPort,
    ReferenceAssayResult,
)

from .model import WaterFilterTwin
from .rankers import CandidateRanker, ClassicalBaselineRanker, QuantumInteractionRanker


class AblationMode(StrEnum):
    """Four pre-registered Industry P-Q-B ablation configurations (T002/T003)."""

    P_ONLY = "P"
    P_PLUS_B = "P+B"
    P_PLUS_Q = "P+Q"
    P_PLUS_Q_PLUS_B = "P+Q+B"


class DecisionAction(StrEnum):
    """Explicit auditable decision types recorded in DecisionRecord."""

    RANK_CANDIDATES = "rank_candidates"
    FALLBACK_CLASSICAL_RANKER = "fallback_classical_ranker"
    START_TRIAL = "start_trial"
    EARLY_STOP = "early_stop"
    RETRY_LOW_FLOW = "retry_low_flow"
    DISCARD_MATERIAL = "discard_material"
    CONFIRM_MATERIAL = "confirm_material"
    FALLBACK_DISABLE_B = "fallback_disable_b"
    CAMPAIGN_NO_MATCH = "campaign_no_match"


@dataclass(frozen=True)
class DecisionRecord:
    """Single causal provenance entry linking an observation to a controller decision."""

    step_index: int
    time_min: float
    material_id: str
    flow_rate_l_min: float
    treated_volume_l: float
    trigger_source: str  # "classical_prior" | "quantum_ranker" | "biosensor_b" | "reference_assay" | "simplex_monitor"
    trigger_summary: str
    action: DecisionAction
    rationale: str


@dataclass(frozen=True)
class FilterTrialConfig:
    """Operational protocol parameters shared identically across P, P+B, P+Q, P+Q+B."""

    step_volume_l: float = 5.0
    ref_sample_interval_l: float = 50.0
    b_sample_interval_l: float = 10.0
    b_alert_persistence: int = 1
    max_b_uncertainty: float = 0.85
    max_b_disagreements: int = 2
    allow_low_flow_retry: bool = True
    trial_setup_min: float = 5.0
    trial_overhead_cost_usd: float = 20.0
    pump_power_w: float = 60.0
    b_fixed_setup_cost_usd: float = 800.0

    def validate(self) -> None:
        for name, val in (
            ("step_volume_l", self.step_volume_l),
            ("ref_sample_interval_l", self.ref_sample_interval_l),
            ("b_sample_interval_l", self.b_sample_interval_l),
            ("max_b_uncertainty", self.max_b_uncertainty),
            ("trial_setup_min", self.trial_setup_min),
            ("trial_overhead_cost_usd", self.trial_overhead_cost_usd),
            ("pump_power_w", self.pump_power_w),
            ("b_fixed_setup_cost_usd", self.b_fixed_setup_cost_usd),
        ):
            if not math.isfinite(val) or val < 0.0:
                raise ValueError(f"{name} must be finite and >= 0 (got {val!r})")
        if self.step_volume_l <= 0.0 or self.ref_sample_interval_l <= 0.0:
            raise ValueError("step_volume_l and ref_sample_interval_l must be > 0")
        if self.b_sample_interval_l <= 0.0:
            raise ValueError("b_sample_interval_l must be > 0")
        if self.b_alert_persistence < 1:
            raise ValueError("b_alert_persistence must be >= 1")
        if self.max_b_disagreements < 1:
            raise ValueError("max_b_disagreements must be >= 1")


@dataclass(frozen=True)
class CampaignResult:
    """Complete verified outcome of a single ablation campaign."""

    mode: AblationMode
    seed: int
    confirmed_material_id: str | None
    confirmed_flow_rate_l_min: float | None
    selection_correct: bool
    high_flow_confirmed: bool
    time_to_confirm_min: float
    trials_started: int
    early_stops: int
    low_flow_retries: int
    total_treated_volume_l: float
    reference_assays_used: int
    biosensor_assays_used: int
    quantum_evals_used: int
    fixed_setup_cost_usd: float
    marginal_campaign_cost_usd: float
    estimated_energy_wh: float
    b_disagreements: int
    b_fallback_triggered: bool
    q_fallback_triggered: bool
    decision_trace: tuple[DecisionRecord, ...] = field(default_factory=tuple)


@dataclass
class _TrialOutcome:
    passed: bool
    early_stopped: bool
    trigger_source: str
    trigger_summary: str
    end_time_min: float
    treated_volume_l: float


class FilterTrialController:
    """Classical P orchestrator running P, P+B, P+Q, and P+Q+B over a hidden WaterFilterTwin."""

    def __init__(self, config: FilterTrialConfig | None = None) -> None:
        self.config: FilterTrialConfig = config or FilterTrialConfig()
        self.config.validate()

    def run_campaign(
        self,
        twin: WaterFilterTwin,
        *,
        mode: AblationMode,
        reference_assay: ReferenceAssayPort,
        biosensor: BiomolecularSensor | None = None,
        ranker: CandidateRanker | None = None,
        seed: int = 42,
    ) -> CampaignResult:
        uses_b = mode in (AblationMode.P_PLUS_B, AblationMode.P_PLUS_Q_PLUS_B)
        uses_q = mode in (AblationMode.P_PLUS_Q, AblationMode.P_PLUS_Q_PLUS_B)
        if uses_b and biosensor is None:
            raise ValueError(f"mode {mode.value} requires a BiomolecularSensor")

        active_ranker: CandidateRanker = ranker or ClassicalBaselineRanker()
        if uses_q and not active_ranker.uses_quantum:
            raise ValueError(f"mode {mode.value} requires a quantum CandidateRanker")

        # Reset adapters with deterministic seed derived from campaign seed.
        reference_assay.reset(seed=seed + 101)
        if biosensor is not None:
            biosensor.reset(seed=seed + 202)

        trace: list[DecisionRecord] = []
        time_min = 0.0
        trials_started = 0
        early_stops = 0
        low_flow_retries = 0
        total_volume_l = 0.0
        ref_used = 0
        b_used = 0
        q_used = 0
        marginal_cost = 0.0
        energy_wh = 0.0
        fixed_setup_cost = (self.config.b_fixed_setup_cost_usd if uses_b else 0.0) + (
            active_ranker.fixed_setup_cost_usd if uses_q else 0.0
        )
        b_active = uses_b
        b_disagreements = 0
        b_fallback = False
        q_fallback = False

        def _log(
            material_id: str,
            flow: float,
            vol: float,
            src: str,
            summary: str,
            action: DecisionAction,
            rationale: str,
        ) -> None:
            trace.append(
                DecisionRecord(
                    step_index=len(trace),
                    time_min=round(time_min, 4),
                    material_id=material_id,
                    flow_rate_l_min=flow,
                    treated_volume_l=round(vol, 4),
                    trigger_source=src,
                    trigger_summary=summary,
                    action=action,
                    rationale=rationale,
                )
            )

        # Step 1: Rank public candidate descriptors (zero access to hidden FilterMaterial).
        descriptors = twin.descriptors()
        ranked = active_ranker.rank(descriptors, seed=seed + 303)
        if uses_q:
            q_used = len(ranked)
            eval_min = (
                active_ranker.eval_duration_min
                if isinstance(active_ranker, QuantumInteractionRanker)
                else 2.0
            )
            q_marginal = (
                active_ranker.marginal_cost_per_eval_usd
                if isinstance(active_ranker, QuantumInteractionRanker)
                else 10.0
            )
            time_min += eval_min * q_used
            marginal_cost += q_marginal * q_used
            energy_wh += sum(r.quantum_energy_w * (eval_min / 60.0) for r in ranked)
            if any(r.fallback_triggered for r in ranked):
                q_fallback = True
                _log(
                    "ALL",
                    0.0,
                    0.0,
                    "simplex_monitor",
                    "quantum ranker uncertainty or Sevo gate exceeded bounds",
                    DecisionAction.FALLBACK_CLASSICAL_RANKER,
                    "Simplex monitor fell back to classical prior for affected candidates",
                )
        order_str = ", ".join(f"{r.material_id}({r.score:.2f})" for r in ranked)
        _log(
            "ALL",
            0.0,
            0.0,
            "quantum_ranker" if uses_q else "classical_prior",
            f"ordered=[{order_str}]",
            DecisionAction.RANK_CANDIDATES,
            f"Candidate queue initialized by {active_ranker.ranker_name}",
        )

        confirmed_id: str | None = None
        confirmed_flow: float | None = None

        def _run_single_trial(material_id: str, flow_rate: float) -> _TrialOutcome:
            nonlocal time_min, trials_started, early_stops, total_volume_l
            nonlocal ref_used, b_used, marginal_cost, energy_wh
            nonlocal b_active, b_disagreements, b_fallback

            trials_started += 1
            time_min += self.config.trial_setup_min
            marginal_cost += self.config.trial_overhead_cost_usd
            _log(
                material_id,
                flow_rate,
                0.0,
                "controller_p",
                f"flow={flow_rate:.2f} L/min target_vol={twin.target_volume_l:.1f} L",
                DecisionAction.START_TRIAL,
                "Start physical filter trial normalized to target treated volume",
            )

            v_treated = 0.0
            step_v = self.config.step_volume_l
            dt_step = step_v / flow_rate
            pending_refs: list[ReferenceAssayResult] = []
            pending_bs: list[BiosensorReading] = []
            paired_b_by_sample: dict[str, BiosensorReading] = {}
            consecutive_b_alerts = 0
            next_ref_v = self.config.ref_sample_interval_l
            next_b_v = self.config.b_sample_interval_l

            def _check_simplex_against_ref(ref_res: ReferenceAssayResult) -> None:
                nonlocal b_active, b_disagreements, b_fallback
                paired = paired_b_by_sample.get(ref_res.sample_id)
                if paired is None:
                    return
                if paired.threshold_crossed != ref_res.exceeds_limit:
                    b_disagreements += 1
                    if b_active and b_disagreements >= self.config.max_b_disagreements:
                        b_active = False
                        b_fallback = True
                        _log(
                            material_id,
                            flow_rate,
                            ref_res.treated_volume_l,
                            "simplex_monitor",
                            (
                                f"sample={ref_res.sample_id} B={paired.threshold_crossed} "
                                f"vs ref={ref_res.exceeds_limit} "
                                f"(disagreements={b_disagreements})"
                            ),
                            DecisionAction.FALLBACK_DISABLE_B,
                            "Simplex monitor disabled B due to reference disagreement / drift",
                        )

            while v_treated + 1e-9 < twin.target_volume_l:
                dv = min(step_v, twin.target_volume_l - v_treated)
                dt = dv / flow_rate
                v_treated += dv
                total_volume_l += dv
                time_min += dt
                energy_wh += self.config.pump_power_w * (dt / 60.0)

                take_ref = (v_treated + 1e-9 >= next_ref_v) or (
                    abs(v_treated - twin.target_volume_l) <= 1e-9
                )
                take_b = b_active and (biosensor is not None) and (v_treated + 1e-9 >= next_b_v)

                if take_ref or take_b:
                    sample = twin.sample_effluent(
                        material_id=material_id,
                        flow_rate_l_min=flow_rate,
                        treated_volume_l=v_treated,
                        sampled_at_min=time_min,
                    )
                    if take_b and biosensor is not None:
                        b_reading = biosensor.sense(sample, elapsed_campaign_min=time_min)
                        pending_bs.append(b_reading)
                        paired_b_by_sample[sample.sample_id] = b_reading
                        b_used += 1
                        marginal_cost += b_reading.cost_usd
                        energy_wh += b_reading.energy_wh
                        next_b_v += self.config.b_sample_interval_l
                    if take_ref:
                        ref_res = reference_assay.measure(
                            sample, limit_mg_l=twin.limit_concentration_mg_l
                        )
                        pending_refs.append(ref_res)
                        ref_used += 1
                        marginal_cost += ref_res.cost_usd
                        energy_wh += ref_res.energy_wh
                        next_ref_v += self.config.ref_sample_interval_l

                # Deliver ready reference assays first (ground-truth authority).
                still_pending_refs: list[ReferenceAssayResult] = []
                for ref_res in pending_refs:
                    if ref_res.available_at_min <= time_min + 1e-9:
                        _check_simplex_against_ref(ref_res)
                        if ref_res.exceeds_limit:
                            early_stops += 1
                            summary = (
                                f"ref={ref_res.measured_concentration_mg_l:.3f} mg/L "
                                f"> limit={ref_res.limit_mg_l:.3f} at V={ref_res.treated_volume_l:.1f} L"
                            )
                            _log(
                                material_id,
                                flow_rate,
                                v_treated,
                                "reference_assay",
                                summary,
                                DecisionAction.EARLY_STOP,
                                "Reference assay confirmed breakthrough before target volume",
                            )
                            return _TrialOutcome(
                                passed=False,
                                early_stopped=True,
                                trigger_source="reference_assay",
                                trigger_summary=summary,
                                end_time_min=time_min,
                                treated_volume_l=v_treated,
                            )
                    else:
                        still_pending_refs.append(ref_res)
                pending_refs = still_pending_refs

                # Deliver ready biosensor alerts (if B is active).
                still_pending_bs: list[BiosensorReading] = []
                for b_res in pending_bs:
                    if b_res.available_at_min <= time_min + 1e-9:
                        if not b_active:
                            continue
                        if (
                            b_res.threshold_crossed
                            and b_res.uncertainty_score <= self.config.max_b_uncertainty
                        ):
                            consecutive_b_alerts += 1
                        else:
                            consecutive_b_alerts = 0
                        if consecutive_b_alerts >= self.config.b_alert_persistence:
                            early_stops += 1
                            summary = (
                                f"B fluor={b_res.fluorescence_norm:.3f} >= "
                                f"thresh={b_res.fluorescence_threshold:.3f} "
                                f"(unc={b_res.uncertainty_score:.2f}) at V={b_res.treated_volume_l:.1f} L"
                            )
                            _log(
                                material_id,
                                flow_rate,
                                v_treated,
                                "biosensor_b",
                                summary,
                                DecisionAction.EARLY_STOP,
                                "Biosensor early breakthrough alert terminated trial before target volume",
                            )
                            return _TrialOutcome(
                                passed=False,
                                early_stopped=True,
                                trigger_source="biosensor_b",
                                trigger_summary=summary,
                                end_time_min=time_min,
                                treated_volume_l=v_treated,
                            )
                    else:
                        still_pending_bs.append(b_res)
                pending_bs = still_pending_bs
                _ = dt_step

            # Reached full target treated volume: MUST wait for final reference assay confirmation.
            pending_refs.sort(key=lambda r: r.available_at_min)
            for ref_res in pending_refs:
                if ref_res.available_at_min > time_min:
                    time_min = ref_res.available_at_min
                _check_simplex_against_ref(ref_res)
                if ref_res.exceeds_limit:
                    summary = (
                        f"ref={ref_res.measured_concentration_mg_l:.3f} mg/L "
                        f"> limit={ref_res.limit_mg_l:.3f} at V={ref_res.treated_volume_l:.1f} L"
                    )
                    return _TrialOutcome(
                        passed=False,
                        early_stopped=False,
                        trigger_source="reference_assay",
                        trigger_summary=summary,
                        end_time_min=time_min,
                        treated_volume_l=v_treated,
                    )

            final_ref = pending_refs[-1] if pending_refs else None
            summary = (
                f"final_ref={final_ref.measured_concentration_mg_l:.3f} mg/L "
                f"<= limit={twin.limit_concentration_mg_l:.3f} at V={v_treated:.1f} L"
                if final_ref is not None
                else f"verified at V={v_treated:.1f} L"
            )
            _log(
                material_id,
                flow_rate,
                v_treated,
                "reference_assay",
                summary,
                DecisionAction.CONFIRM_MATERIAL,
                "Independent reference assay confirmed compliance at full target volume",
            )
            return _TrialOutcome(
                passed=True,
                early_stopped=False,
                trigger_source="reference_assay",
                trigger_summary=summary,
                end_time_min=time_min,
                treated_volume_l=v_treated,
            )

        # Step 2: Execute trials across ranked candidates.
        for cand in ranked:
            high_outcome = _run_single_trial(cand.material_id, twin.flow_high_l_min)
            if high_outcome.passed:
                confirmed_id = cand.material_id
                confirmed_flow = twin.flow_high_l_min
                break

            if self.config.allow_low_flow_retry:
                low_flow_retries += 1
                _log(
                    cand.material_id,
                    twin.flow_low_l_min,
                    high_outcome.treated_volume_l,
                    high_outcome.trigger_source,
                    high_outcome.trigger_summary,
                    DecisionAction.RETRY_LOW_FLOW,
                    "High-flow breakthrough observed; retrying at lower flow rate to test contact-time limit",
                )
                low_outcome = _run_single_trial(cand.material_id, twin.flow_low_l_min)
                if low_outcome.passed:
                    confirmed_id = cand.material_id
                    confirmed_flow = twin.flow_low_l_min
                    break
                _log(
                    cand.material_id,
                    twin.flow_low_l_min,
                    low_outcome.treated_volume_l,
                    low_outcome.trigger_source,
                    low_outcome.trigger_summary,
                    DecisionAction.DISCARD_MATERIAL,
                    "Breakthrough persisted at low flow rate; discarding candidate",
                )
            else:
                _log(
                    cand.material_id,
                    twin.flow_high_l_min,
                    high_outcome.treated_volume_l,
                    high_outcome.trigger_source,
                    high_outcome.trigger_summary,
                    DecisionAction.DISCARD_MATERIAL,
                    "High-flow breakthrough observed and low-flow retry disabled",
                )

        if confirmed_id is None:
            _log(
                "NONE",
                0.0,
                total_volume_l,
                "controller_p",
                "all candidates exhausted",
                DecisionAction.CAMPAIGN_NO_MATCH,
                "No candidate satisfied the target removal specification",
            )

        # Post-hoc ground-truth verification (evaluator only).
        if confirmed_id is not None and confirmed_flow is not None:
            selection_correct = twin.oracle_is_compliant(confirmed_id, confirmed_flow)
            high_flow_confirmed = math.isclose(confirmed_flow, twin.flow_high_l_min)
        else:
            selection_correct = not twin.oracle_has_any_compliant()
            high_flow_confirmed = False

        return CampaignResult(
            mode=mode,
            seed=seed,
            confirmed_material_id=confirmed_id,
            confirmed_flow_rate_l_min=confirmed_flow,
            selection_correct=selection_correct,
            high_flow_confirmed=high_flow_confirmed,
            time_to_confirm_min=round(time_min, 4),
            trials_started=trials_started,
            early_stops=early_stops,
            low_flow_retries=low_flow_retries,
            total_treated_volume_l=round(total_volume_l, 4),
            reference_assays_used=ref_used,
            biosensor_assays_used=b_used,
            quantum_evals_used=q_used,
            fixed_setup_cost_usd=round(fixed_setup_cost, 2),
            marginal_campaign_cost_usd=round(marginal_cost, 2),
            estimated_energy_wh=round(energy_wh, 4),
            b_disagreements=b_disagreements,
            b_fallback_triggered=b_fallback,
            q_fallback_triggered=q_fallback,
            decision_trace=tuple(trace),
        )
