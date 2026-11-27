"""Comparative Industry P-Q-B Triadic Safeguard & Voluntary Habitat Benchmark (T006)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np

from .evaluator import PQBTriadicSafeguardController
from .types import (
    TRIADIC_PILLAR_AXES,
    TRIADIC_PILLARS,
    BioregenerativeReserveSpec,
    HabitatPlacementMode,
    PolycrisisState,
    PQBCampaignProposal,
    PQBCapitalVector,
    PQBPolicyName,
    PQBSafeguardProfile,
    PQBTelemetrySnapshot,
    TransferMotivation,
    VoluntaryBioregenerativeHabitatPlan,
    VoluntaryHabitatTransfer,
)


@dataclass(frozen=True)
class PQBSafeguardScenario:
    """Labelled P-Q-B industrial or habitat scenario for policy ablation."""

    scenario_id: str
    split: Literal["calibration", "held_out"]
    description: str
    proposal: PQBCampaignProposal
    expected_safe: bool


@dataclass(frozen=True)
class PQBPolicySplitMetrics:
    """Safety & classification metrics for one policy on one evaluation split."""

    policy: PQBPolicyName
    split: str
    total_scenarios: int
    unsafe_approvals: int
    false_refusals: int
    exact_match_rate: float


@dataclass(frozen=True)
class PQBSafeguardBenchmarkReport:
    """Deterministic SHA-256 comparative benchmark report for T006."""

    spec: str
    cross_repo_alignment: str
    profile_sha256: str
    calibration_metrics: tuple[PQBPolicySplitMetrics, ...]
    held_out_metrics: tuple[PQBPolicySplitMetrics, ...]
    zero_unsafe_held_out: bool
    zero_false_refusal_held_out: bool
    strictly_beats_baselines: bool
    advisory_only: bool = True
    report_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_t006_pqb_scenarios() -> tuple[PQBSafeguardScenario, ...]:
    """Build disjoint calibration (n=4) and held-out (n=8) Industry P-Q-B scenarios."""
    mod_crisis = PolycrisisState(
        climatic_ecological=0.52,
        economic=0.48,
        social=0.45,
        sanitary=0.42,
        cyber_infrastructural=0.46,
    )
    high_crisis = PolycrisisState(
        climatic_ecological=0.62,
        economic=0.58,
        social=0.55,
        sanitary=0.52,
        cyber_infrastructural=0.56,
    )
    base_cme = PQBCapitalVector.uniform(0.60)
    clean_tel = PQBTelemetrySnapshot(
        q_active=True,
        sevo=2.1,
        q_uncertainty=0.12,
        b_biosensor_active=True,
        b_reference_disagreement=0.04,
        wetware_active=False,
        estimated_power_w=110.0,
    )

    return (
        # --- Calibration split (4 scenarios) ---
        PQBSafeguardScenario(
            scenario_id="PQB-CAL-01-extractive-chemical-plant",
            split="calibration",
            description="High industrial yield & innovation, but depletes Earth ecology below floor.",
            proposal=PQBCampaignProposal.create(
                proposal_id="PQB-CAL-01",
                proposer_id="pqb:planner",
                reviewer_id="human:ops_lead",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=PQBCapitalVector.uniform(
                    0.62,
                    energy=0.86,
                    innovation=0.88,
                    ecology=0.28,
                    regeneration=0.31,
                ),
                initial_crisis=mod_crisis,
                crisis_intervention={"economic": -0.05, "climatic_ecological": 0.08},
                telemetry=clean_tel,
            ),
            expected_safe=False,
        ),
        PQBSafeguardScenario(
            scenario_id="PQB-CAL-02-biosensor-drift-unverified-water",
            split="calibration",
            description="CME looks green, but B-layer biosensor disagrees with LC-MS reference.",
            proposal=PQBCampaignProposal.create(
                proposal_id="PQB-CAL-02",
                proposer_id="pqb:planner",
                reviewer_id="human:ops_lead",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=PQBCapitalVector.uniform(0.64, ecology=0.68, wellbeing=0.66),
                initial_crisis=mod_crisis,
                telemetry=PQBTelemetrySnapshot(
                    q_active=True,
                    sevo=1.9,
                    q_uncertainty=0.15,
                    b_biosensor_active=True,
                    b_reference_disagreement=0.32,  # > 0.15 Simplex limit
                ),
            ),
            expected_safe=False,
        ),
        PQBSafeguardScenario(
            scenario_id="PQB-CAL-03-grid-cascade-risk-transfer",
            split="calibration",
            description="Static CME passes, but industrial load transfers shock onto grid.",
            proposal=PQBCampaignProposal.create(
                proposal_id="PQB-CAL-03",
                proposer_id="pqb:planner",
                reviewer_id="human:ops_lead",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=PQBCapitalVector.uniform(0.63),
                initial_crisis=mod_crisis,
                crisis_intervention={"economic": -0.05, "cyber_infrastructural": 0.07},
                telemetry=clean_tel,
            ),
            expected_safe=False,
        ),
        PQBSafeguardScenario(
            scenario_id="PQB-CAL-04-clean-water-filter-campaign",
            split="calibration",
            description="T003-aligned P+Q+B water-purification rollout improving all 3 pillars.",
            proposal=PQBCampaignProposal.create(
                proposal_id="PQB-CAL-04",
                proposer_id="pqb:planner",
                reviewer_id="human:ops_lead",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=PQBCapitalVector.uniform(
                    0.65,
                    ecology=0.70,
                    regeneration=0.68,
                    wellbeing=0.69,
                    resilience=0.68,
                ),
                initial_crisis=mod_crisis,
                crisis_intervention={
                    "climatic_ecological": -0.06,
                    "sanitary": -0.07,
                    "social": -0.04,
                    "economic": -0.03,
                },
                telemetry=clean_tel,
            ),
            expected_safe=True,
        ),
        # --- Held-Out split (8 unseen scenarios) ---
        PQBSafeguardScenario(
            scenario_id="PQB-HO-01-wetware-envelope-breach",
            split="held_out",
            description="Active organoid loop breaches WetwareSafetyEnvelope charge/pH limits.",
            proposal=PQBCampaignProposal.create(
                proposal_id="PQB-HO-01",
                proposer_id="pqb:alpha",
                reviewer_id="human:bio_safety",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=PQBCapitalVector.uniform(0.66, innovation=0.78),
                initial_crisis=mod_crisis,
                telemetry=PQBTelemetrySnapshot(
                    q_active=False,
                    b_biosensor_active=True,
                    b_reference_disagreement=0.02,
                    wetware_active=True,
                    wetware_envelope_compliant=False,
                ),
            ),
            expected_safe=False,
        ),
        PQBSafeguardScenario(
            scenario_id="PQB-HO-02-quantum-low-sevo-overclaim",
            split="held_out",
            description="Active Q-layer dispatch fails Sevo efficiency gate (< 1.5).",
            proposal=PQBCampaignProposal.create(
                proposal_id="PQB-HO-02",
                proposer_id="pqb:alpha",
                reviewer_id="human:bio_safety",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=PQBCapitalVector.uniform(0.64),
                initial_crisis=mod_crisis,
                telemetry=PQBTelemetrySnapshot(
                    q_active=True,
                    sevo=1.10,
                    q_uncertainty=0.12,
                    b_biosensor_active=True,
                    b_reference_disagreement=0.03,
                ),
            ),
            expected_safe=False,
        ),
        PQBSafeguardScenario(
            scenario_id="PQB-HO-03-civilization-sacrifice-above-floor",
            split="held_out",
            description="Boosts industrial energy/ecology by sacrificing human distribution (-0.11).",
            proposal=PQBCampaignProposal.create(
                proposal_id="PQB-HO-03",
                proposer_id="pqb:alpha",
                reviewer_id="human:bio_safety",
                human_oversight_approved=True,
                pre_cme=PQBCapitalVector.uniform(0.66, distribution=0.70),
                post_cme=PQBCapitalVector.uniform(
                    0.69,
                    distribution=0.59,
                    energy=0.85,
                    ecology=0.78,
                ),
                initial_crisis=mod_crisis,
                telemetry=clean_tel,
            ),
            expected_safe=False,
        ),
        PQBSafeguardScenario(
            scenario_id="PQB-HO-04-sanitary-risk-transfer",
            split="held_out",
            description="Mitigates economic stress by aggravating sanitary polycrisis coupling.",
            proposal=PQBCampaignProposal.create(
                proposal_id="PQB-HO-04",
                proposer_id="pqb:alpha",
                reviewer_id="human:bio_safety",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=PQBCapitalVector.uniform(0.64),
                initial_crisis=high_crisis,
                crisis_intervention={"economic": -0.07, "sanitary": 0.06},
                telemetry=clean_tel,
            ),
            expected_safe=False,
        ),
        PQBSafeguardScenario(
            scenario_id="PQB-HO-05-coercive-habitat-relocation",
            split="held_out",
            description="Bioregenerative habitat with full supplies but involuntary relocation.",
            proposal=PQBCampaignProposal.create(
                proposal_id="PQB-HO-05",
                proposer_id="pqb:alpha",
                reviewer_id="human:bio_safety",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=PQBCapitalVector.uniform(0.66, wellbeing=0.72),
                initial_crisis=high_crisis,
                telemetry=clean_tel,
                habitat_plan=VoluntaryBioregenerativeHabitatPlan(
                    habitat_id="pqb-hab-coercive",
                    placement=HabitatPlacementMode.TERRESTRIAL,
                    target_civilization_population=5_000,
                    requested_occupancy=1_000,
                    reserves=BioregenerativeReserveSpec(
                        water_liters_per_day_total=30_000.0,
                        food_kcal_per_day_total=4_000_000.0,
                        oxygen_kg_per_day_total=1_600.0,
                        clean_power_kw_total=3_000.0,
                        medical_sanitary_index=0.90,
                        psychosocial_wellbeing_index=0.85,
                        autonomy_reserve_days=150.0,
                        closed_loop_recycling_efficiency=0.90,
                        environmental_shielding_integrity=0.82,
                    ),
                    free_exit_guaranteed=False,
                ),
            ),
            expected_safe=False,
        ),
        PQBSafeguardScenario(
            scenario_id="PQB-HO-06-unverified-biosensor-orbital-habitat",
            split="held_out",
            description="Voluntary orbital habitat whose B-layer water loop lacks LC-MS verification.",
            proposal=PQBCampaignProposal.create(
                proposal_id="PQB-HO-06",
                proposer_id="pqb:alpha",
                reviewer_id="human:bio_safety",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=PQBCapitalVector.uniform(0.65, innovation=0.74),
                initial_crisis=mod_crisis,
                telemetry=clean_tel,
                habitat_plan=VoluntaryBioregenerativeHabitatPlan(
                    habitat_id="pqb-orbital-unverified-b",
                    placement=HabitatPlacementMode.EXTRATERRESTRIAL,
                    target_civilization_population=10_000,
                    requested_occupancy=2_000,
                    reserves=BioregenerativeReserveSpec(
                        water_liters_per_day_total=50_000.0,
                        food_kcal_per_day_total=8_000_000.0,
                        oxygen_kg_per_day_total=3_000.0,
                        clean_power_kw_total=12_000.0,
                        medical_sanitary_index=0.90,
                        psychosocial_wellbeing_index=0.86,
                        autonomy_reserve_days=400.0,
                        closed_loop_recycling_efficiency=0.99,
                        environmental_shielding_integrity=0.97,
                        biosensor_reference_verified=False,
                    ),
                ),
            ),
            expected_safe=False,
        ),
        PQBSafeguardScenario(
            scenario_id="PQB-HO-07-regenerative-pqb-polycrisis-remediation",
            split="held_out",
            description="Closed-loop P+Q+B bioremediation & resilient microgrid across all 5 crises.",
            proposal=PQBCampaignProposal.create(
                proposal_id="PQB-HO-07",
                proposer_id="pqb:alpha",
                reviewer_id="human:bio_safety",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=PQBCapitalVector.uniform(
                    0.65,
                    ecology=0.70,
                    regeneration=0.69,
                    wellbeing=0.68,
                    resilience=0.71,
                    reversibility=0.69,
                ),
                initial_crisis=high_crisis,
                crisis_intervention={
                    "climatic_ecological": -0.07,
                    "economic": -0.06,
                    "social": -0.06,
                    "sanitary": -0.07,
                    "cyber_infrastructural": -0.07,
                },
                telemetry=clean_tel,
            ),
            expected_safe=True,
        ),
        PQBSafeguardScenario(
            scenario_id="PQB-HO-08-voluntary-bioregenerative-refuge-network",
            split="held_out",
            description="Hybrid voluntary P-Q-B refuge habitat for protection & personal wellbeing.",
            proposal=PQBCampaignProposal.create(
                proposal_id="PQB-HO-08",
                proposer_id="pqb:alpha",
                reviewer_id="human:bio_safety",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=PQBCapitalVector.uniform(
                    0.65,
                    ecology=0.67,
                    regeneration=0.67,
                    wellbeing=0.72,
                    distribution=0.68,
                    resilience=0.71,
                ),
                initial_crisis=high_crisis,
                crisis_intervention={
                    "climatic_ecological": -0.05,
                    "economic": -0.05,
                    "social": -0.06,
                    "sanitary": -0.06,
                    "cyber_infrastructural": -0.05,
                },
                telemetry=clean_tel,
                habitat_plan=VoluntaryBioregenerativeHabitatPlan(
                    habitat_id="pqb-hybrid-bioregen-sanctuary-v1",
                    placement=HabitatPlacementMode.HYBRID_FEDERATED,
                    target_civilization_population=10_000,
                    requested_occupancy=10_000,
                    reserves=BioregenerativeReserveSpec(
                        water_liters_per_day_total=200_000.0,
                        food_kcal_per_day_total=30_000_000.0,
                        oxygen_kg_per_day_total=12_000.0,
                        clean_power_kw_total=35_000.0,
                        medical_sanitary_index=0.93,
                        psychosocial_wellbeing_index=0.90,
                        autonomy_reserve_days=240.0,
                        closed_loop_recycling_efficiency=0.96,
                        environmental_shielding_integrity=0.91,
                        biosensor_reference_verified=True,
                    ),
                    transfer_requests=(
                        VoluntaryHabitatTransfer(
                            request_id="tx-polycrisis",
                            persons_count=6_000,
                            motivation=TransferMotivation.POLYCRISIS_PROTECTION,
                        ),
                        VoluntaryHabitatTransfer(
                            request_id="tx-wellbeing",
                            persons_count=4_000,
                            motivation=TransferMotivation.PERSONAL_WELLBEING,
                        ),
                    ),
                ),
            ),
            expected_safe=True,
        ),
    )


def _evaluate_policy(
    policy: PQBPolicyName,
    proposal: PQBCampaignProposal,
    controller: PQBTriadicSafeguardController,
) -> bool:
    if policy == "scalar_pqb_utility_baseline":
        return float(np.mean(proposal.post_cme.as_array())) >= float(
            np.mean(proposal.pre_cme.as_array())
        )
    if policy == "decoupled_static_pqb_gate":
        for pillar in TRIADIC_PILLARS:
            axes = TRIADIC_PILLAR_AXES[pillar]
            vals = [float(getattr(proposal.post_cme, ax)) for ax in axes]
            if min(vals) < controller.profile.axis_floor_for(pillar):
                return False
            if (sum(vals) / len(vals)) < controller.profile.mean_floor_for(pillar):
                return False
        return (
            proposal.human_oversight_approved
            and proposal.reviewer_id.strip() != proposal.proposer_id.strip()
        )
    return controller.evaluate(proposal).approved_for_advisory


def run_pqb_safeguard_benchmark(
    *,
    profile: PQBSafeguardProfile | None = None,
) -> PQBSafeguardBenchmarkReport:
    """Run deterministic 3-policy ablation across T006 calibration and held-out scenarios."""
    prof = profile if profile is not None else PQBSafeguardProfile()
    controller = PQBTriadicSafeguardController(profile=prof)
    scenarios = build_t006_pqb_scenarios()
    policies: tuple[PQBPolicyName, ...] = (
        "scalar_pqb_utility_baseline",
        "decoupled_static_pqb_gate",
        "pqb_triadic_safeguard",
    )

    def _eval_split(
        split_name: Literal["calibration", "held_out"],
    ) -> tuple[PQBPolicySplitMetrics, ...]:
        subset = [sc for sc in scenarios if sc.split == split_name]
        rows: list[PQBPolicySplitMetrics] = []
        for pol in policies:
            unsafe_app = 0
            false_ref = 0
            matches = 0
            for sc in subset:
                approved = _evaluate_policy(pol, sc.proposal, controller)
                if approved == sc.expected_safe:
                    matches += 1
                elif approved and not sc.expected_safe:
                    unsafe_app += 1
                elif not approved and sc.expected_safe:
                    false_ref += 1
            rows.append(
                PQBPolicySplitMetrics(
                    policy=pol,
                    split=split_name,
                    total_scenarios=len(subset),
                    unsafe_approvals=unsafe_app,
                    false_refusals=false_ref,
                    exact_match_rate=round(matches / max(len(subset), 1), 6),
                )
            )
        return tuple(rows)

    cal = _eval_split("calibration")
    ho = _eval_split("held_out")
    by_pol = {m.policy: m for m in ho}
    target = by_pol["pqb_triadic_safeguard"]
    scalar_b = by_pol["scalar_pqb_utility_baseline"]
    static_b = by_pol["decoupled_static_pqb_gate"]

    zero_unsafe = target.unsafe_approvals == 0
    zero_false_ref = target.false_refusals == 0
    beats = (
        zero_unsafe
        and zero_false_ref
        and target.unsafe_approvals < scalar_b.unsafe_approvals
        and target.unsafe_approvals < static_b.unsafe_approvals
    )

    draft: dict[str, Any] = {
        "spec": "T006",
        "cross_repo_alignment": "q_speace:T254",
        "profile_sha256": prof.profile_sha256(),
        "calibration_metrics": [asdict(m) for m in cal],
        "held_out_metrics": [asdict(m) for m in ho],
        "zero_unsafe_held_out": zero_unsafe,
        "zero_false_refusal_held_out": zero_false_ref,
        "strictly_beats_baselines": beats,
        "advisory_only": True,
    }
    digest = hashlib.sha256(
        json.dumps(draft, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()

    return PQBSafeguardBenchmarkReport(
        spec="T006",
        cross_repo_alignment="q_speace:T254",
        profile_sha256=prof.profile_sha256(),
        calibration_metrics=cal,
        held_out_metrics=ho,
        zero_unsafe_held_out=zero_unsafe,
        zero_false_refusal_held_out=zero_false_ref,
        strictly_beats_baselines=beats,
        advisory_only=True,
        report_sha256=digest,
    )
