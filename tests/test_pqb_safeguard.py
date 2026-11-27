"""Tests for T006 Industry P-Q-B Triadic Safeguard, Anti-Polycrisis & Voluntary Habitat."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from b_speace import (
    CME_FIELDS,
    CRISIS_DOMAINS,
    JSON_SCHEMA_DRAFT_2020_12,
    NORMATIVE_SCHEMA_FILES,
    STANDARD_IDENTIFIER,
    TRIADIC_PILLAR_AXES,
    TRIADIC_PILLARS,
    BCELCatalog,
    BioregenerativeReserveSpec,
    ConformanceProfileLevel,
    HabitatPlacementMode,
    PolycrisisCouplingModel,
    PolycrisisState,
    PQBCampaignProposal,
    PQBCapitalVector,
    PQBConstitutionalFaultError,
    PQBSafeguardProfile,
    PQBSafeguardValidationError,
    PQBSafeguardVerdictKind,
    PQBTelemetrySnapshot,
    PQBTriadicSafeguardController,
    TransferMotivation,
    TriadicPillar,
    VoluntaryBioregenerativeHabitatPlan,
    VoluntaryHabitatTransfer,
    build_conformance_manifest,
    build_t006_pqb_scenarios,
    compute_normative_schema_digests,
    evaluate_bioregenerative_habitat,
    load_normative_schema,
    run_pqb_safeguard_benchmark,
    validate_top_level_schema_contract,
    verify_conformance_manifest,
    verify_pqb_cme_partition,
)
from b_speace.cli import app


@dataclass(frozen=True)
class _MockQSpeaceCME:
    energy: float = 0.70
    matter: float = 0.68
    information: float = 0.72
    time: float = 0.65
    ecology: float = 0.74
    resilience: float = 0.71
    wellbeing: float = 0.73
    innovation: float = 0.69
    reversibility: float = 0.70
    distribution: float = 0.67
    coherence: float = 0.75
    regeneration: float = 0.72


def test_t006_bcel_entries_and_cme_partition() -> None:
    cat = BCELCatalog()
    acc_concepts = {e.concept for e in cat.accidental()}
    func_concepts = {e.concept for e in cat.functional()}
    assert (
        "Planetary organism gestation or infallible off-world ark teleology (T006)" in acc_concepts
    )
    assert (
        "Industry P-Q-B non-compensable triadic substrate & polycrisis shield (T006)"
        in func_concepts
    )
    assert "P-Q-B bioregenerative voluntary protective habitat protocol (T006)" in func_concepts

    assert verify_pqb_cme_partition() is True
    all_axes = [ax for p in TRIADIC_PILLARS for ax in TRIADIC_PILLAR_AXES[p]]
    assert len(all_axes) == 12
    assert set(all_axes) == set(CME_FIELDS)

    converted = PQBCapitalVector.from_qspeace_cme(_MockQSpeaceCME())
    assert converted.ecology == pytest.approx(0.74)
    assert converted.to_dict()["wellbeing"] == pytest.approx(0.73)

    with pytest.raises(PQBSafeguardValidationError, match="missing CME field"):
        PQBCapitalVector.from_qspeace_cme(object())


def test_profile_and_numeric_fail_closed_guards() -> None:
    with pytest.raises(PQBConstitutionalFaultError):
        PQBSafeguardProfile(advisory_only=False)
    with pytest.raises(PQBConstitutionalFaultError):
        PQBSafeguardProfile(no_physical_actuation=False)
    with pytest.raises(PQBConstitutionalFaultError):
        PQBSafeguardProfile(require_human_oversight=False)
    with pytest.raises(PQBSafeguardValidationError):
        PQBSafeguardProfile(min_earth_axis_floor=0.60, min_earth_pillar_mean=0.40)

    with pytest.raises(PQBSafeguardValidationError, match="finite"):
        PolycrisisState(math.nan, 0.2, 0.2, 0.2, 0.2)
    with pytest.raises(PQBSafeguardValidationError, match="finite"):
        PQBTelemetrySnapshot(sevo=math.inf)

    model = PolycrisisCouplingModel()
    assert 0.5 < model.spectral_radius() < 1.5
    single = PolycrisisState(0.75, 0.0, 0.0, 0.0, 0.0)
    coupled = PolycrisisState(0.70, 0.65, 0.60, 0.58, 0.62)
    assert model.synergy_index(single) == pytest.approx(0.0)
    assert model.synergy_index(coupled) > 0.35
    traj = model.propagate(single, steps=4)
    assert len(traj) == 5
    assert traj[1].economic > 0.0


@pytest.mark.parametrize(
    ("axis_name", "pillar"),
    [
        ("ecology", TriadicPillar.EARTH_BIOSPHERE),
        ("wellbeing", TriadicPillar.HUMAN_CIVILIZATION),
        ("reversibility", TriadicPillar.TECH_INFRASTRUCTURE),
    ],
)
def test_triadic_non_compensability_blocks_any_single_pillar_breach(
    axis_name: str,
    pillar: TriadicPillar,
) -> None:
    ctrl = PQBTriadicSafeguardController()
    prop = PQBCampaignProposal.create(
        proposal_id=f"breach-{axis_name}",
        proposer_id="pqb:agent",
        reviewer_id="human:reviewer",
        human_oversight_approved=True,
        pre_cme=PQBCapitalVector.uniform(0.60),
        post_cme=PQBCapitalVector.uniform(0.85, **{axis_name: 0.26}),
        initial_crisis=PolycrisisState(0.35, 0.30, 0.30, 0.28, 0.32),
    )
    res = ctrl.evaluate(prop)
    assert res.approved_for_advisory is False
    assert res.verdict is PQBSafeguardVerdictKind.BLOCKED_PILLAR_FLOOR
    assert any(pillar.value in r for r in res.reasons)


def test_pqb_simplex_telemetry_and_constitutional_and_risk_transfer_gates() -> None:
    ctrl = PQBTriadicSafeguardController()
    base = PQBCapitalVector.uniform(0.66)
    crisis = PolycrisisState(0.45, 0.42, 0.40, 0.38, 0.41)

    # 1. Self-approval blocked
    v_self = ctrl.evaluate(
        PQBCampaignProposal.create(
            proposal_id="self-app",
            proposer_id="pqb:same",
            reviewer_id="pqb:same",
            human_oversight_approved=True,
            pre_cme=base,
            post_cme=base,
            initial_crisis=crisis,
        )
    )
    assert v_self.verdict is PQBSafeguardVerdictKind.BLOCKED_CONSTITUTIONAL

    # 2. High Q uncertainty or B reference disagreement or Wetware breach blocked
    v_q_unc = ctrl.evaluate(
        PQBCampaignProposal.create(
            proposal_id="high-q-unc",
            proposer_id="pqb:a",
            reviewer_id="human:b",
            human_oversight_approved=True,
            pre_cme=base,
            post_cme=base,
            initial_crisis=crisis,
            telemetry=PQBTelemetrySnapshot(q_active=True, sevo=2.0, q_uncertainty=0.60),
        )
    )
    assert v_q_unc.verdict is PQBSafeguardVerdictKind.BLOCKED_PQB_TELEMETRY_ENVELOPE

    # 3. Cross-pillar sacrifice blocked
    v_sac = ctrl.evaluate(
        PQBCampaignProposal.create(
            proposal_id="sac",
            proposer_id="pqb:a",
            reviewer_id="human:b",
            human_oversight_approved=True,
            pre_cme=PQBCapitalVector.uniform(0.70),
            post_cme=PQBCapitalVector.uniform(0.74, regeneration=0.60),
            initial_crisis=crisis,
        )
    )
    assert v_sac.verdict is PQBSafeguardVerdictKind.BLOCKED_CROSS_PILLAR_SACRIFICE

    # 4. Risk transfer blocked
    v_tr = ctrl.evaluate(
        PQBCampaignProposal.create(
            proposal_id="transfer",
            proposer_id="pqb:a",
            reviewer_id="human:b",
            human_oversight_approved=True,
            pre_cme=base,
            post_cme=PQBCapitalVector.uniform(0.68),
            initial_crisis=crisis,
            crisis_intervention={"climatic_ecological": -0.07, "sanitary": 0.06},
        )
    )
    assert v_tr.verdict is PQBSafeguardVerdictKind.BLOCKED_RISK_TRANSFER

    # 5. Balanced P+Q+B campaign approved
    v_ok = ctrl.evaluate(
        PQBCampaignProposal.create(
            proposal_id="ok",
            proposer_id="pqb:a",
            reviewer_id="human:b",
            human_oversight_approved=True,
            pre_cme=base,
            post_cme=PQBCapitalVector.uniform(0.69),
            initial_crisis=crisis,
            crisis_intervention=dict.fromkeys([d.value for d in CRISIS_DOMAINS], -0.05),
            telemetry=PQBTelemetrySnapshot(q_active=True, sevo=2.2, q_uncertainty=0.10),
        )
    )
    assert v_ok.verdict is PQBSafeguardVerdictKind.APPROVED_ADVISORY
    assert v_ok.approved_for_advisory is True
    assert len(v_ok.verdict_sha256) == 64


def test_voluntary_bioregenerative_habitat_protocol() -> None:
    with pytest.raises(PQBSafeguardValidationError, match="redundancy_factor"):
        BioregenerativeReserveSpec(
            water_liters_per_day_total=20_000.0,
            food_kcal_per_day_total=3_000_000.0,
            oxygen_kg_per_day_total=1_200.0,
            clean_power_kw_total=3_000.0,
            medical_sanitary_index=0.85,
            psychosocial_wellbeing_index=0.80,
            autonomy_reserve_days=120.0,
            closed_loop_recycling_efficiency=0.90,
            environmental_shielding_integrity=0.80,
            redundancy_factor=1.10,
        )

    reserves = BioregenerativeReserveSpec(
        water_liters_per_day_total=200_000.0,
        food_kcal_per_day_total=30_000_000.0,
        oxygen_kg_per_day_total=12_000.0,
        clean_power_kw_total=50_000.0,
        medical_sanitary_index=0.92,
        psychosocial_wellbeing_index=0.88,
        autonomy_reserve_days=400.0,
        closed_loop_recycling_efficiency=0.99,
        environmental_shielding_integrity=0.97,
        biosensor_reference_verified=True,
    )

    # Voluntary extraterrestrial pilot against 8B humanity reports partial coverage honestly
    ev_pilot = evaluate_bioregenerative_habitat(
        VoluntaryBioregenerativeHabitatPlan(
            habitat_id="pqb-orbital-alpha",
            placement=HabitatPlacementMode.EXTRATERRESTRIAL,
            target_civilization_population=8_000_000_000,
            requested_occupancy=10_000,
            reserves=reserves,
            transfer_requests=(
                VoluntaryHabitatTransfer(
                    request_id="r1",
                    persons_count=5_000,
                    motivation=TransferMotivation.POLYCRISIS_PROTECTION,
                ),
                VoluntaryHabitatTransfer(
                    request_id="r2",
                    persons_count=5_000,
                    motivation=TransferMotivation.PERSONAL_WELLBEING,
                ),
            ),
        )
    )
    assert ev_pilot.passed is True
    assert ev_pilot.universal_humanity_coverage_ready is False
    assert ev_pilot.biosensor_loop_verified is True

    # Coercive transfer request is blocked
    ev_coerced = evaluate_bioregenerative_habitat(
        VoluntaryBioregenerativeHabitatPlan(
            habitat_id="pqb-coerced",
            placement=HabitatPlacementMode.TERRESTRIAL,
            target_civilization_population=5_000,
            requested_occupancy=500,
            reserves=reserves,
            transfer_requests=(
                VoluntaryHabitatTransfer(
                    request_id="bad",
                    persons_count=500,
                    motivation=TransferMotivation.POLYCRISIS_PROTECTION,
                    coercive_assignment=True,
                ),
            ),
        )
    )
    assert ev_coerced.passed is False
    assert ev_coerced.failure_kind is PQBSafeguardVerdictKind.BLOCKED_REFUGE_COERCION


def test_t006_benchmark_and_cli(tmp_path: Path) -> None:
    report = run_pqb_safeguard_benchmark()
    assert report.spec == "T006"
    assert report.cross_repo_alignment == "q_speace:T254"
    assert report.zero_unsafe_held_out is True
    assert report.zero_false_refusal_held_out is True
    assert report.strictly_beats_baselines is True

    out_path = tmp_path / "t006_report.json"
    runner = CliRunner()
    res = runner.invoke(app, ["safeguard", "evaluate", "--out", str(out_path)])
    assert res.exit_code == 0, res.output
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["report_sha256"] == report.report_sha256
    assert data["strictly_beats_baselines"] is True


def test_t007_normative_json_schemas_and_conformance_profiles(tmp_path: Path) -> None:
    # 1. All 3 Draft 2020-12 schemas load cleanly and enforce closed properties
    digests = compute_normative_schema_digests()
    assert len(digests) == 3
    for fname in NORMATIVE_SCHEMA_FILES:
        schema = load_normative_schema(fname)
        assert schema["$schema"] == JSON_SCHEMA_DRAFT_2020_12
        assert schema["additionalProperties"] is False
        assert len(digests[fname]) == 64

    with pytest.raises(PQBSafeguardValidationError, match="unknown normative schema"):
        load_normative_schema("nonexistent.schema.json")

    # 2. Validate real proposal and verdict dicts against Annex A.1 & A.2 top-level contracts
    ctrl = PQBTriadicSafeguardController()
    sc = build_t006_pqb_scenarios()[-1]
    prop_payload = {
        "proposal_id": sc.proposal.proposal_id,
        "proposer_id": sc.proposal.proposer_id,
        "reviewer_id": sc.proposal.reviewer_id,
        "human_oversight_approved": sc.proposal.human_oversight_approved,
        "pre_cme": sc.proposal.pre_cme.to_dict(),
        "post_cme": sc.proposal.post_cme.to_dict(),
        "initial_crisis": sc.proposal.initial_crisis.to_dict(),
        "crisis_intervention": sc.proposal.intervention_map(),
        "telemetry": {
            "q_active": sc.proposal.telemetry.q_active,
            "sevo": sc.proposal.telemetry.sevo,
            "q_uncertainty": sc.proposal.telemetry.q_uncertainty,
            "b_biosensor_active": sc.proposal.telemetry.b_biosensor_active,
            "b_reference_disagreement": sc.proposal.telemetry.b_reference_disagreement,
            "wetware_active": sc.proposal.telemetry.wetware_active,
            "wetware_envelope_compliant": sc.proposal.telemetry.wetware_envelope_compliant,
            "estimated_power_w": sc.proposal.telemetry.estimated_power_w,
        },
        "habitat_plan": None,
    }
    validate_top_level_schema_contract("pqb_campaign_proposal.schema.json", prop_payload)
    verdict_dict = ctrl.evaluate(sc.proposal).to_dict()
    validate_top_level_schema_contract("pqb_safeguard_verdict.schema.json", verdict_dict)

    # Extra key or non-finite value rejected fail-closed
    with pytest.raises(PQBSafeguardValidationError, match="forbidden additional keys"):
        validate_top_level_schema_contract(
            "pqb_safeguard_verdict.schema.json",
            {**verdict_dict, "rogue_field": 1},
        )
    with pytest.raises(PQBSafeguardValidationError, match="RFC 8259"):
        validate_top_level_schema_contract(
            "pqb_safeguard_verdict.schema.json",
            {**verdict_dict, "peak_propagated_crisis": math.nan},
        )

    # 3. Build and verify L1, L2, and L3 Clause 7 Conformance Manifests (Annex A.3)
    for level in ConformanceProfileLevel:
        manifest = build_conformance_manifest(system_id="eu-iso-audit-node", level=level)
        m_dict = manifest.to_dict()
        assert m_dict["standard_id"] == STANDARD_IDENTIFIER
        assert verify_conformance_manifest(m_dict) is True

        # Tampering with actuation flag or hash invalidates verification
        assert (
            verify_conformance_manifest({**m_dict, "autonomous_physical_actuation_permitted": True})
            is False
        )
        assert verify_conformance_manifest({**m_dict, "system_id": "tampered-node"}) is False

    # 4. CLI conformance export test
    manifest_file = tmp_path / "l3_conformance.json"
    runner = CliRunner()
    res = runner.invoke(
        app,
        ["safeguard", "conformance", "--level", "L3", "--out", str(manifest_file)],
    )
    assert res.exit_code == 0, res.output
    loaded_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert verify_conformance_manifest(loaded_manifest) is True

    bad_res = runner.invoke(app, ["safeguard", "conformance", "--level", "L99"])
    assert bad_res.exit_code != 0
