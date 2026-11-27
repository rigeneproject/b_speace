"""Deterministic Industry P-Q-B Triadic Safeguard & Voluntary Habitat Evaluator (T006)."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from .types import (
    CRISIS_DOMAINS,
    HABITAT_PLACEMENT_THRESHOLDS,
    MIN_FOOD_KCAL_PER_PERSON_DAY,
    MIN_MEDICAL_SANITARY_INDEX,
    MIN_OXYGEN_KG_PER_PERSON_DAY,
    MIN_PSYCHOSOCIAL_WELLBEING_INDEX,
    MIN_WATER_L_PER_PERSON_DAY,
    TRIADIC_PILLAR_AXES,
    TRIADIC_PILLARS,
    BioregenerativeHabitatEvaluation,
    PolycrisisState,
    PQBCampaignProposal,
    PQBSafeguardProfile,
    PQBSafeguardValidationError,
    PQBSafeguardVerdict,
    PQBSafeguardVerdictKind,
    VoluntaryBioregenerativeHabitatPlan,
    require_finite,
)

DEFAULT_POLYCRISIS_COUPLING: tuple[tuple[float, ...], ...] = (
    (0.00, 0.06, 0.02, 0.01, 0.07),
    (0.08, 0.00, 0.07, 0.07, 0.09),
    (0.06, 0.09, 0.00, 0.08, 0.05),
    (0.07, 0.06, 0.06, 0.00, 0.07),
    (0.08, 0.07, 0.04, 0.03, 0.00),
)

DEFAULT_CRISIS_DAMPING: tuple[float, ...] = (0.16, 0.22, 0.20, 0.22, 0.22)

DEFAULT_PILLAR_EXPOSURE: tuple[tuple[float, ...], ...] = (
    (0.60, 0.12, 0.06, 0.06, 0.16),
    (0.15, 0.25, 0.28, 0.24, 0.08),
    (0.16, 0.20, 0.08, 0.06, 0.50),
)


@dataclass(frozen=True)
class PolycrisisCouplingModel:
    """Discrete coupled 5-domain propagation model aligned with q_speace T254."""

    coupling_weights: tuple[tuple[float, ...], ...] = DEFAULT_POLYCRISIS_COUPLING
    damping: tuple[float, ...] = DEFAULT_CRISIS_DAMPING
    pillar_exposure: tuple[tuple[float, ...], ...] = DEFAULT_PILLAR_EXPOSURE

    def __post_init__(self) -> None:
        if len(self.coupling_weights) != 5 or any(len(r) != 5 for r in self.coupling_weights):
            raise PQBSafeguardValidationError("coupling_weights must have shape 5x5")
        for r_idx, row in enumerate(self.coupling_weights):
            for c_idx, val in enumerate(row):
                fval = require_finite(f"coupling_weights[{r_idx}][{c_idx}]", val)
                if fval < 0.0 or fval > 1.0:
                    raise PQBSafeguardValidationError("coupling_weights entries must be in [0, 1]")
                if r_idx == c_idx and abs(fval) > 1e-12:
                    raise PQBSafeguardValidationError("coupling_weights diagonal must be zero")

        if len(self.damping) != 5:
            raise PQBSafeguardValidationError("damping must have length 5")
        for idx, dval in enumerate(self.damping):
            fd = require_finite(f"damping[{idx}]", dval)
            if not (0.0 < fd < 1.0):
                raise PQBSafeguardValidationError("damping entries must lie in (0, 1)")

        if len(self.pillar_exposure) != 3 or any(len(r) != 5 for r in self.pillar_exposure):
            raise PQBSafeguardValidationError("pillar_exposure must have shape 3x5")
        for p_idx, row in enumerate(self.pillar_exposure):
            row_sum = 0.0
            for c_idx, val in enumerate(row):
                fval = require_finite(f"pillar_exposure[{p_idx}][{c_idx}]", val)
                if fval < 0.0:
                    raise PQBSafeguardValidationError("pillar_exposure entries must be >= 0")
                row_sum += fval
            if row_sum <= 0.0 or row_sum > 1.0 + 1e-9:
                raise PQBSafeguardValidationError("pillar_exposure row sum must lie in (0, 1]")

    def weight_matrix(self) -> np.ndarray:
        return np.array(self.coupling_weights, dtype=np.float64)

    def damping_vector(self) -> np.ndarray:
        return np.array(self.damping, dtype=np.float64)

    def exposure_matrix(self) -> np.ndarray:
        return np.array(self.pillar_exposure, dtype=np.float64)

    def spectral_radius(self) -> float:
        jacobian = np.diag(1.0 - self.damping_vector()) + self.weight_matrix()
        eigvals = np.linalg.eigvals(jacobian)
        return float(np.max(np.abs(eigvals)))

    def synergy_index(self, state: PolycrisisState) -> float:
        s = state.as_array()
        w = self.weight_matrix()
        denom = float(np.sum(w))
        if denom <= 1e-12:
            return 0.0
        return float(np.clip(float(s @ w @ s) / denom, 0.0, 1.0))

    def normalize_intervention(
        self,
        intervention: Mapping[str, float] | Sequence[float] | None,
    ) -> np.ndarray:
        if intervention is None:
            return np.zeros(5, dtype=np.float64)
        if isinstance(intervention, Mapping):
            unknown = set(intervention.keys()) - {d.value for d in CRISIS_DOMAINS}
            if unknown:
                raise PQBSafeguardValidationError(
                    f"unknown crisis domain(s) in intervention: {sorted(unknown)}"
                )
            vec = [float(intervention.get(d.value, 0.0)) for d in CRISIS_DOMAINS]
        else:
            if len(intervention) != 5:
                raise PQBSafeguardValidationError("intervention sequence must have length 5")
            vec = [float(x) for x in intervention]
        for idx, val in enumerate(vec):
            fval = require_finite(f"intervention[{idx}]", val)
            if not (-1.0 <= fval <= 1.0):
                raise PQBSafeguardValidationError("intervention entries must lie in [-1, 1]")
        return np.array(vec, dtype=np.float64)

    def propagate(
        self,
        initial: PolycrisisState,
        intervention: Mapping[str, float] | Sequence[float] | None = None,
        *,
        steps: int = 4,
    ) -> tuple[PolycrisisState, ...]:
        if steps < 1:
            raise PQBSafeguardValidationError("steps must be >= 1")
        u = self.normalize_intervention(intervention)
        w = self.weight_matrix()
        gamma = self.damping_vector()
        traj: list[PolycrisisState] = [initial]
        curr = initial.as_array()
        for _ in range(steps):
            curr = np.clip((1.0 - gamma) * curr + (w @ curr) + u, 0.0, 1.0)
            traj.append(PolycrisisState.from_array(curr))
        return tuple(traj)

    def pillar_stress(self, state: PolycrisisState) -> dict[str, float]:
        proj = np.clip(self.exposure_matrix() @ state.as_array(), 0.0, 1.0)
        return {pillar.value: float(proj[idx]) for idx, pillar in enumerate(TRIADIC_PILLARS)}


def evaluate_bioregenerative_habitat(
    plan: VoluntaryBioregenerativeHabitatPlan,
) -> BioregenerativeHabitatEvaluation:
    """Evaluate C8 voluntary individual choice, Leontief N+2 capacity & B-layer reference verification."""
    reasons: list[str] = []
    coercion_detected = False

    if not plan.voluntary_opt_in_only:
        coercion_detected = True
        reasons.append("C8 violation: voluntary_opt_in_only is False")
    if not plan.free_exit_guaranteed:
        coercion_detected = True
        reasons.append("C8 violation: free_exit_guaranteed is False")
    if not plan.coercive_relocation_forbidden:
        coercion_detected = True
        reasons.append("C8 violation: coercive_relocation_forbidden is False")
    if not plan.universal_non_discriminatory_access:
        coercion_detected = True
        reasons.append("C8 violation: universal_non_discriminatory_access is False")

    transfer_sum = 0
    for req in plan.transfer_requests:
        transfer_sum += req.persons_count
        if (
            not req.voluntary_consent_verified
            or not req.free_exit_acknowledged
            or req.coercive_assignment
        ):
            coercion_detected = True
            reasons.append(
                f"C8 violation in request {req.request_id!r}: coercive or non-consensual transfer"
            )

    eff_occupancy = max(plan.requested_occupancy, transfer_sum)
    reqs = HABITAT_PLACEMENT_THRESHOLDS[plan.placement]
    res = plan.reserves
    kappa = res.redundancy_factor

    channel_caps = {
        "water": res.water_liters_per_day_total / (kappa * MIN_WATER_L_PER_PERSON_DAY),
        "food": res.food_kcal_per_day_total / (kappa * MIN_FOOD_KCAL_PER_PERSON_DAY),
        "oxygen": res.oxygen_kg_per_day_total / (kappa * MIN_OXYGEN_KG_PER_PERSON_DAY),
        "clean_power": res.clean_power_kw_total / (kappa * reqs["min_power_kw_per_person"]),
    }
    limiting_channel = min(channel_caps, key=lambda k: channel_caps[k])
    cert_capacity = int(math.floor(channel_caps[limiting_channel]))

    resource_ok = True
    if eff_occupancy > cert_capacity:
        resource_ok = False
        reasons.append(
            f"Leontief N+2 capacity {cert_capacity} (bottleneck={limiting_channel}) "
            f"< requested occupancy {eff_occupancy}"
        )
    if res.medical_sanitary_index < MIN_MEDICAL_SANITARY_INDEX:
        resource_ok = False
        reasons.append(
            f"medical_sanitary_index {res.medical_sanitary_index:.3f} < "
            f"{MIN_MEDICAL_SANITARY_INDEX:.3f}"
        )
    if res.psychosocial_wellbeing_index < MIN_PSYCHOSOCIAL_WELLBEING_INDEX:
        resource_ok = False
        reasons.append(
            f"psychosocial_wellbeing_index {res.psychosocial_wellbeing_index:.3f} < "
            f"{MIN_PSYCHOSOCIAL_WELLBEING_INDEX:.3f}"
        )
    if res.autonomy_reserve_days < reqs["min_reserve_days"]:
        resource_ok = False
        reasons.append(
            f"{plan.placement.value} autonomy_reserve_days {res.autonomy_reserve_days:.1f} < "
            f"{reqs['min_reserve_days']:.1f}"
        )
    if res.closed_loop_recycling_efficiency < reqs["min_loop_recycling_efficiency"]:
        resource_ok = False
        reasons.append(
            f"{plan.placement.value} closed_loop_recycling_efficiency "
            f"{res.closed_loop_recycling_efficiency:.3f} < "
            f"{reqs['min_loop_recycling_efficiency']:.3f}"
        )
    if res.environmental_shielding_integrity < reqs["min_shielding_integrity"]:
        resource_ok = False
        reasons.append(
            f"{plan.placement.value} environmental_shielding_integrity "
            f"{res.environmental_shielding_integrity:.3f} < "
            f"{reqs['min_shielding_integrity']:.3f}"
        )
    if not res.biosensor_reference_verified:
        resource_ok = False
        reasons.append(
            "B-layer closed-loop water/air biosensor lacks analytical reference verification"
        )

    failure_kind: PQBSafeguardVerdictKind | None = None
    if coercion_detected:
        failure_kind = PQBSafeguardVerdictKind.BLOCKED_REFUGE_COERCION
    elif not resource_ok:
        failure_kind = PQBSafeguardVerdictKind.BLOCKED_REFUGE_RESOURCE_DEFICIT

    passed = failure_kind is None
    cov_ratio = round(min(1.0, cert_capacity / plan.target_civilization_population), 6)
    universal_ready = passed and cert_capacity >= plan.target_civilization_population

    return BioregenerativeHabitatEvaluation(
        habitat_id=plan.habitat_id,
        placement=plan.placement.value,
        certified_leontief_capacity=cert_capacity,
        limiting_resource_channel=limiting_channel,
        effective_requested_occupancy=eff_occupancy,
        target_civilization_population=plan.target_civilization_population,
        civilization_coverage_ratio=cov_ratio,
        universal_humanity_coverage_ready=universal_ready,
        autonomy_and_consent_verified=not coercion_detected,
        life_support_and_wellbeing_verified=resource_ok,
        biosensor_loop_verified=res.biosensor_reference_verified,
        passed=passed,
        failure_kind=failure_kind,
        reasons=tuple(reasons),
        simulation_and_advisory_only=True,
    )


class PQBTriadicSafeguardController:
    """Industry P-Q-B controller enforcing C6 triadic floors, C7 anti-polycrisis & C8 habitats."""

    def __init__(
        self,
        *,
        profile: PQBSafeguardProfile | None = None,
        coupling: PolycrisisCouplingModel | None = None,
    ) -> None:
        self.profile = profile if profile is not None else PQBSafeguardProfile()
        self.coupling = coupling if coupling is not None else PolycrisisCouplingModel()

    def evaluate(self, proposal: PQBCampaignProposal) -> PQBSafeguardVerdict:
        reasons: list[str] = []
        verdict_kind: PQBSafeguardVerdictKind | None = None

        # 1. Constitutional human-oversight & anti-self-approval check
        if not proposal.reviewer_id.strip():
            verdict_kind = PQBSafeguardVerdictKind.BLOCKED_CONSTITUTIONAL
            reasons.append("missing independent reviewer_id")
        elif proposal.reviewer_id.strip() == proposal.proposer_id.strip():
            verdict_kind = PQBSafeguardVerdictKind.BLOCKED_CONSTITUTIONAL
            reasons.append("self-approval forbidden (proposer_id == reviewer_id)")
        elif self.profile.require_human_oversight and not proposal.human_oversight_approved:
            verdict_kind = PQBSafeguardVerdictKind.BLOCKED_CONSTITUTIONAL
            reasons.append("C1_HumanApprovalRequired: human_oversight_approved is False")

        # 2. Closed-loop P-Q-B Simplex & Wetware safety envelope check
        tel = proposal.telemetry
        if tel.estimated_power_w > self.profile.max_power_w:
            if verdict_kind is None:
                verdict_kind = PQBSafeguardVerdictKind.BLOCKED_PQB_TELEMETRY_ENVELOPE
            reasons.append(
                f"estimated_power_w {tel.estimated_power_w:.2f} > max_power_w "
                f"{self.profile.max_power_w:.2f}"
            )
        if tel.q_active:
            if tel.sevo < self.profile.min_sevo:
                if verdict_kind is None:
                    verdict_kind = PQBSafeguardVerdictKind.BLOCKED_PQB_TELEMETRY_ENVELOPE
                reasons.append(
                    f"Q-layer Sevo {tel.sevo:.3f} < min_sevo {self.profile.min_sevo:.3f}"
                )
            if tel.q_uncertainty > self.profile.max_q_uncertainty:
                if verdict_kind is None:
                    verdict_kind = PQBSafeguardVerdictKind.BLOCKED_PQB_TELEMETRY_ENVELOPE
                reasons.append(
                    f"Q-layer uncertainty {tel.q_uncertainty:.3f} > "
                    f"max_q_uncertainty {self.profile.max_q_uncertainty:.3f}"
                )
        if tel.b_biosensor_active and (
            tel.b_reference_disagreement > self.profile.max_b_reference_disagreement
        ):
            if verdict_kind is None:
                verdict_kind = PQBSafeguardVerdictKind.BLOCKED_PQB_TELEMETRY_ENVELOPE
            reasons.append(
                f"B-layer biosensor reference disagreement {tel.b_reference_disagreement:.3f} > "
                f"{self.profile.max_b_reference_disagreement:.3f}"
            )
        if tel.wetware_active and not tel.wetware_envelope_compliant:
            if verdict_kind is None:
                verdict_kind = PQBSafeguardVerdictKind.BLOCKED_PQB_TELEMETRY_ENVELOPE
            reasons.append("WetwareSafetyEnvelope violation in active B-layer organoid/MEA loop")

        # 3. Coupled polycrisis trajectory & baseline comparison
        horizon = self.profile.cascade_horizon_steps
        base_traj = self.coupling.propagate(proposal.initial_crisis, None, steps=horizon)
        cand_traj = self.coupling.propagate(
            proposal.initial_crisis,
            proposal.intervention_map(),
            steps=horizon,
        )
        init_synergy = self.coupling.synergy_index(proposal.initial_crisis)
        base_final_synergy = self.coupling.synergy_index(base_traj[-1])
        cand_final_synergy = self.coupling.synergy_index(cand_traj[-1])
        spec_radius = self.coupling.spectral_radius()

        base_arr = np.stack([st.as_array() for st in base_traj[1:]], axis=0)
        cand_arr = np.stack([st.as_array() for st in cand_traj[1:]], axis=0)
        collateral_deltas = np.max(cand_arr - base_arr, axis=0)
        max_collateral_delta = float(np.max(collateral_deltas))
        peak_cand_crisis = float(np.max(cand_arr))
        peak_base_crisis = float(np.max(base_arr))

        # 4. C6 Non-compensable Triadic CME floors & anti-sacrifice
        pillar_metrics: dict[str, dict[str, float]] = {}
        final_pillar_stress = self.coupling.pillar_stress(cand_traj[-1])
        base_pillar_stress = self.coupling.pillar_stress(base_traj[-1])
        floor_violated = False
        sacrifice_violated = False
        cascade_floor_violated = False

        for pillar in TRIADIC_PILLARS:
            axes = TRIADIC_PILLAR_AXES[pillar]
            pre_vals = [float(getattr(proposal.pre_cme, ax)) for ax in axes]
            post_vals = [float(getattr(proposal.post_cme, ax)) for ax in axes]
            deltas = [pv - qv for qv, pv in zip(pre_vals, post_vals, strict=True)]

            axis_floor = self.profile.axis_floor_for(pillar)
            mean_floor = self.profile.mean_floor_for(pillar)
            post_min = min(post_vals)
            post_mean = sum(post_vals) / len(post_vals)
            worst_delta = min(deltas)

            stress_excess = max(
                0.0,
                final_pillar_stress[pillar.value] - base_pillar_stress[pillar.value],
            )
            cascade_penalty = self.profile.cme_cascade_sensitivity * (
                0.5 * final_pillar_stress[pillar.value] + stress_excess
            )
            projected_post_cascade_min = max(0.0, post_min - cascade_penalty)

            pillar_metrics[pillar.value] = {
                "pre_axis_min": round(min(pre_vals), 6),
                "post_axis_min": round(post_min, 6),
                "pre_mean": round(sum(pre_vals) / len(pre_vals), 6),
                "post_mean": round(post_mean, 6),
                "worst_axis_delta": round(worst_delta, 6),
                "final_polycrisis_stress": round(final_pillar_stress[pillar.value], 6),
                "projected_post_cascade_axis_min": round(projected_post_cascade_min, 6),
            }

            if post_min < axis_floor:
                floor_violated = True
                reasons.append(
                    f"{pillar.value}: post_axis_min {post_min:.4f} < floor {axis_floor:.4f}"
                )
            if post_mean < mean_floor:
                floor_violated = True
                reasons.append(
                    f"{pillar.value}: post_mean {post_mean:.4f} < mean_floor {mean_floor:.4f}"
                )
            if worst_delta < -self.profile.max_single_axis_sacrifice - 1e-12:
                sacrifice_violated = True
                reasons.append(
                    f"{pillar.value}: axis degradation {worst_delta:.4f} exceeds "
                    f"-max_single_axis_sacrifice (-{self.profile.max_single_axis_sacrifice:.4f})"
                )
            if projected_post_cascade_min < axis_floor:
                cascade_floor_violated = True
                reasons.append(
                    f"{pillar.value}: post-cascade projected axis min "
                    f"{projected_post_cascade_min:.4f} < floor {axis_floor:.4f}"
                )

        if verdict_kind is None and floor_violated:
            verdict_kind = PQBSafeguardVerdictKind.BLOCKED_PILLAR_FLOOR
        if verdict_kind is None and sacrifice_violated:
            verdict_kind = PQBSafeguardVerdictKind.BLOCKED_CROSS_PILLAR_SACRIFICE

        # 5. C7 Anti-risk-transfer & polycrisis cascade amplification
        for idx, domain in enumerate(CRISIS_DOMAINS):
            c_delta = float(collateral_deltas[idx])
            if c_delta > self.profile.max_domain_collateral_delta + 1e-12:
                if verdict_kind is None:
                    verdict_kind = PQBSafeguardVerdictKind.BLOCKED_RISK_TRANSFER
                reasons.append(
                    f"risk transfer onto {domain.value}: +{c_delta:.4f} > "
                    f"{self.profile.max_domain_collateral_delta:.4f}"
                )

        ceiling = self.profile.max_crisis_ceiling
        ceiling_breached = (peak_base_crisis <= ceiling and peak_cand_crisis > ceiling + 1e-12) or (
            peak_base_crisis > ceiling and peak_cand_crisis > peak_base_crisis + 1e-12
        )
        synergy_amplified = cand_final_synergy > base_final_synergy + 0.01

        if ceiling_breached or synergy_amplified or cascade_floor_violated:
            if verdict_kind is None:
                verdict_kind = PQBSafeguardVerdictKind.BLOCKED_POLYCRISIS_AMPLIFICATION
            if ceiling_breached:
                reasons.append(
                    f"propagated crisis peak {peak_cand_crisis:.4f} breached ceiling {ceiling:.4f}"
                )
            if synergy_amplified:
                reasons.append(
                    f"polycrisis synergy amplified from {base_final_synergy:.4f} "
                    f"to {cand_final_synergy:.4f}"
                )

        # 6. C8 Voluntary Bioregenerative Protective Habitat check
        habitat_eval_dict: dict[str, Any] | None = None
        if proposal.habitat_plan is not None:
            hab_eval = evaluate_bioregenerative_habitat(proposal.habitat_plan)
            habitat_eval_dict = hab_eval.to_dict()
            if not hab_eval.passed and hab_eval.failure_kind is not None:
                if (
                    hab_eval.failure_kind is PQBSafeguardVerdictKind.BLOCKED_REFUGE_COERCION
                    and verdict_kind is not PQBSafeguardVerdictKind.BLOCKED_CONSTITUTIONAL
                ):
                    verdict_kind = PQBSafeguardVerdictKind.BLOCKED_REFUGE_COERCION
                elif verdict_kind is None:
                    verdict_kind = hab_eval.failure_kind
                reasons.extend(hab_eval.reasons)

        if verdict_kind is None:
            verdict_kind = PQBSafeguardVerdictKind.APPROVED_ADVISORY
            reasons.append(
                "all Industry P-Q-B triadic floors, Simplex telemetry gates, anti-polycrisis "
                "bounds, and voluntary habitat rules satisfied (advisory-only)"
            )

        approved = verdict_kind is PQBSafeguardVerdictKind.APPROVED_ADVISORY
        r_init_syn = round(init_synergy, 6)
        r_final_syn = round(cand_final_synergy, 6)
        r_base_syn = round(base_final_synergy, 6)
        r_spec = round(spec_radius, 6)
        r_collat = round(max_collateral_delta, 6)
        r_peak = round(peak_cand_crisis, 6)

        draft: dict[str, Any] = {
            "proposal_id": proposal.proposal_id,
            "verdict": verdict_kind.value,
            "approved_for_advisory": approved,
            "reasons": list(reasons),
            "pillar_metrics": pillar_metrics,
            "initial_synergy_index": r_init_syn,
            "final_synergy_index": r_final_syn,
            "baseline_final_synergy_index": r_base_syn,
            "coupling_spectral_radius": r_spec,
            "max_collateral_crisis_delta": r_collat,
            "peak_propagated_crisis": r_peak,
            "habitat_evaluation": habitat_eval_dict,
            "advisory_only": True,
        }
        digest = hashlib.sha256(
            json.dumps(draft, sort_keys=True, allow_nan=False).encode("utf-8")
        ).hexdigest()

        return PQBSafeguardVerdict(
            proposal_id=proposal.proposal_id,
            verdict=verdict_kind,
            approved_for_advisory=approved,
            reasons=tuple(reasons),
            pillar_metrics=pillar_metrics,
            initial_synergy_index=r_init_syn,
            final_synergy_index=r_final_syn,
            baseline_final_synergy_index=r_base_syn,
            coupling_spectral_radius=r_spec,
            max_collateral_crisis_delta=r_collat,
            peak_propagated_crisis=r_peak,
            habitat_evaluation=habitat_eval_dict,
            advisory_only=True,
            verdict_sha256=digest,
        )
