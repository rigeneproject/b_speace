"""Typed contracts for T006 Industry P-Q-B Triadic Safeguard & Voluntary Habitat Protocol."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Literal

import numpy as np


class PQBSafeguardError(Exception):
    """Base error for Industry P-Q-B Triadic Safeguard & Anti-Polycrisis governance."""


class PQBSafeguardValidationError(PQBSafeguardError):
    """Raised on non-finite or out-of-range inputs (fail-closed numerical guard)."""


class PQBConstitutionalFaultError(PQBSafeguardError):
    """Raised when mandatory T006/T254 safety or constitutional flags are weakened."""


class TriadicPillar(StrEnum):
    """Three non-fungible constitutive substrates shared across SPEACE Macro, q_speace & b_speace."""

    EARTH_BIOSPHERE = "earth_biosphere"
    HUMAN_CIVILIZATION = "human_civilization"
    TECH_INFRASTRUCTURE = "tech_infrastructure"


TRIADIC_PILLARS: tuple[TriadicPillar, ...] = (
    TriadicPillar.EARTH_BIOSPHERE,
    TriadicPillar.HUMAN_CIVILIZATION,
    TriadicPillar.TECH_INFRASTRUCTURE,
)

CME_FIELDS: tuple[str, ...] = (
    "energy",
    "matter",
    "information",
    "time",
    "ecology",
    "resilience",
    "wellbeing",
    "innovation",
    "reversibility",
    "distribution",
    "coherence",
    "regeneration",
)

TRIADIC_PILLAR_AXES: dict[TriadicPillar, tuple[str, ...]] = {
    TriadicPillar.EARTH_BIOSPHERE: ("ecology", "regeneration", "matter", "coherence"),
    TriadicPillar.HUMAN_CIVILIZATION: ("wellbeing", "distribution", "time", "innovation"),
    TriadicPillar.TECH_INFRASTRUCTURE: ("energy", "information", "resilience", "reversibility"),
}


def verify_pqb_cme_partition() -> bool:
    """Verify exact 3x4 bijection between TriadicPillar and the 12 CME fields."""
    seen: list[str] = []
    for pillar in TRIADIC_PILLARS:
        axes = TRIADIC_PILLAR_AXES[pillar]
        if len(axes) != 4:
            raise PQBConstitutionalFaultError(
                f"pillar {pillar.value!r} must map to exactly 4 CME axes"
            )
        seen.extend(axes)
    if len(seen) != len(CME_FIELDS) or set(seen) != set(CME_FIELDS):
        raise PQBConstitutionalFaultError("TRIADIC_PILLAR_AXES is not a bijection with CME_FIELDS")
    return True


verify_pqb_cme_partition()


class CrisisDomain(StrEnum):
    """Five interconnected crisis domains modeled in systemic polycrises."""

    CLIMATIC_ECOLOGICAL = "climatic_ecological"
    ECONOMIC = "economic"
    SOCIAL = "social"
    SANITARY = "sanitary"
    CYBER_INFRASTRUCTURAL = "cyber_infrastructural"


CRISIS_DOMAINS: tuple[CrisisDomain, ...] = (
    CrisisDomain.CLIMATIC_ECOLOGICAL,
    CrisisDomain.ECONOMIC,
    CrisisDomain.SOCIAL,
    CrisisDomain.SANITARY,
    CrisisDomain.CYBER_INFRASTRUCTURAL,
)


class HabitatPlacementMode(StrEnum):
    """Placement domain for voluntary artificial bioregenerative habitats."""

    TERRESTRIAL = "terrestrial"
    EXTRATERRESTRIAL = "extraterrestrial"
    HYBRID_FEDERATED = "hybrid_federated"


class TransferMotivation(StrEnum):
    """Voluntary individual motivation for entering a protective habitat."""

    POLYCRISIS_PROTECTION = "polycrisis_protection"
    PERSONAL_WELLBEING = "personal_wellbeing"


class PQBSafeguardVerdictKind(StrEnum):
    """Deterministic decision outcomes of PQBTriadicSafeguardController."""

    APPROVED_ADVISORY = "APPROVED_ADVISORY"
    BLOCKED_CONSTITUTIONAL = "BLOCKED_CONSTITUTIONAL"
    BLOCKED_PQB_TELEMETRY_ENVELOPE = "BLOCKED_PQB_TELEMETRY_ENVELOPE"
    BLOCKED_PILLAR_FLOOR = "BLOCKED_PILLAR_FLOOR"
    BLOCKED_CROSS_PILLAR_SACRIFICE = "BLOCKED_CROSS_PILLAR_SACRIFICE"
    BLOCKED_RISK_TRANSFER = "BLOCKED_RISK_TRANSFER"
    BLOCKED_POLYCRISIS_AMPLIFICATION = "BLOCKED_POLYCRISIS_AMPLIFICATION"
    BLOCKED_REFUGE_COERCION = "BLOCKED_REFUGE_COERCION"
    BLOCKED_REFUGE_RESOURCE_DEFICIT = "BLOCKED_REFUGE_RESOURCE_DEFICIT"


PQBPolicyName = Literal[
    "scalar_pqb_utility_baseline",
    "decoupled_static_pqb_gate",
    "pqb_triadic_safeguard",
]

HABITAT_PLACEMENT_THRESHOLDS: dict[HabitatPlacementMode, dict[str, float]] = {
    HabitatPlacementMode.TERRESTRIAL: {
        "min_power_kw_per_person": 1.5,
        "min_reserve_days": 90.0,
        "min_loop_recycling_efficiency": 0.85,
        "min_shielding_integrity": 0.70,
    },
    HabitatPlacementMode.HYBRID_FEDERATED: {
        "min_power_kw_per_person": 2.5,
        "min_reserve_days": 180.0,
        "min_loop_recycling_efficiency": 0.92,
        "min_shielding_integrity": 0.85,
    },
    HabitatPlacementMode.EXTRATERRESTRIAL: {
        "min_power_kw_per_person": 3.5,
        "min_reserve_days": 365.0,
        "min_loop_recycling_efficiency": 0.98,
        "min_shielding_integrity": 0.95,
    },
}

MIN_WATER_L_PER_PERSON_DAY: float = 15.0
MIN_FOOD_KCAL_PER_PERSON_DAY: float = 2200.0
MIN_OXYGEN_KG_PER_PERSON_DAY: float = 0.84
MIN_MEDICAL_SANITARY_INDEX: float = 0.75
MIN_PSYCHOSOCIAL_WELLBEING_INDEX: float = 0.70
MIN_LIFE_SUPPORT_REDUNDANCY: float = 1.25


def require_finite(name: str, val: float) -> float:
    fval = float(val)
    if not math.isfinite(fval):
        raise PQBSafeguardValidationError(f"{name} must be finite (got {val!r})")
    return fval


def require_unit_interval(name: str, val: float) -> float:
    fval = require_finite(name, val)
    if not (0.0 <= fval <= 1.0):
        raise PQBSafeguardValidationError(f"{name} must be in [0, 1] (got {val!r})")
    return fval


@dataclass(frozen=True)
class PQBCapitalVector:
    """12-dimensional non-fungible capital vector aligned 1-to-1 with q_speace CME."""

    energy: float
    matter: float
    information: float
    time: float
    ecology: float
    resilience: float
    wellbeing: float
    innovation: float
    reversibility: float
    distribution: float
    coherence: float
    regeneration: float

    def __post_init__(self) -> None:
        for fname in CME_FIELDS:
            require_unit_interval(f"CME.{fname}", getattr(self, fname))

    @classmethod
    def uniform(cls, value: float = 0.62, **overrides: float) -> PQBCapitalVector:
        vals = dict.fromkeys(CME_FIELDS, value)
        vals.update(overrides)
        return cls(**vals)

    @classmethod
    def from_qspeace_cme(cls, cme_obj: object) -> PQBCapitalVector:
        """Convert any object exposing the 12 q_speace CME attributes without hard import."""
        vals: dict[str, float] = {}
        for fname in CME_FIELDS:
            if not hasattr(cme_obj, fname):
                raise PQBSafeguardValidationError(f"object missing CME field {fname!r}")
            vals[fname] = float(getattr(cme_obj, fname))
        return cls(**vals)

    def as_array(self) -> np.ndarray:
        return np.array([getattr(self, fname) for fname in CME_FIELDS], dtype=np.float64)

    def to_dict(self) -> dict[str, float]:
        return {fname: float(getattr(self, fname)) for fname in CME_FIELDS}


@dataclass(frozen=True)
class PolycrisisState:
    """Normalized [0, 1] severity across the 5 interconnected crisis domains."""

    climatic_ecological: float
    economic: float
    social: float
    sanitary: float
    cyber_infrastructural: float

    def __post_init__(self) -> None:
        for dom in CRISIS_DOMAINS:
            require_unit_interval(dom.value, getattr(self, dom.value))

    @classmethod
    def from_array(cls, arr: np.ndarray) -> PolycrisisState:
        if arr.shape != (5,):
            raise PQBSafeguardValidationError(f"expected shape (5,), got {arr.shape}")
        return cls(
            climatic_ecological=float(arr[0]),
            economic=float(arr[1]),
            social=float(arr[2]),
            sanitary=float(arr[3]),
            cyber_infrastructural=float(arr[4]),
        )

    def as_array(self) -> np.ndarray:
        return np.array([getattr(self, dom.value) for dom in CRISIS_DOMAINS], dtype=np.float64)

    def to_dict(self) -> dict[str, float]:
        return {dom.value: float(getattr(self, dom.value)) for dom in CRISIS_DOMAINS}


@dataclass(frozen=True)
class PQBTelemetrySnapshot:
    """Closed-loop Industry P-Q-B measurement & Simplex integrity snapshot."""

    q_active: bool = False
    sevo: float = 2.0
    q_uncertainty: float = 0.10
    b_biosensor_active: bool = True
    b_reference_disagreement: float = 0.03
    wetware_active: bool = False
    wetware_envelope_compliant: bool = True
    estimated_power_w: float = 120.0

    def __post_init__(self) -> None:
        s_val = require_finite("sevo", self.sevo)
        if s_val < 0.0:
            raise PQBSafeguardValidationError("sevo must be >= 0")
        require_unit_interval("q_uncertainty", self.q_uncertainty)
        require_unit_interval("b_reference_disagreement", self.b_reference_disagreement)
        p_val = require_finite("estimated_power_w", self.estimated_power_w)
        if p_val < 0.0:
            raise PQBSafeguardValidationError("estimated_power_w must be >= 0")


@dataclass(frozen=True)
class BioregenerativeReserveSpec:
    """Closed-loop P-Q-B life-support & psychosocial wellbeing stock specification."""

    water_liters_per_day_total: float
    food_kcal_per_day_total: float
    oxygen_kg_per_day_total: float
    clean_power_kw_total: float
    medical_sanitary_index: float
    psychosocial_wellbeing_index: float
    autonomy_reserve_days: float
    closed_loop_recycling_efficiency: float
    environmental_shielding_integrity: float
    biosensor_reference_verified: bool = True
    redundancy_factor: float = 1.25

    def __post_init__(self) -> None:
        for fname in (
            "water_liters_per_day_total",
            "food_kcal_per_day_total",
            "oxygen_kg_per_day_total",
            "clean_power_kw_total",
            "autonomy_reserve_days",
        ):
            fval = require_finite(fname, getattr(self, fname))
            if fval < 0.0:
                raise PQBSafeguardValidationError(f"{fname} must be >= 0")
        for uname in (
            "medical_sanitary_index",
            "psychosocial_wellbeing_index",
            "closed_loop_recycling_efficiency",
            "environmental_shielding_integrity",
        ):
            require_unit_interval(uname, getattr(self, uname))
        rf = require_finite("redundancy_factor", self.redundancy_factor)
        if rf < MIN_LIFE_SUPPORT_REDUNDANCY:
            raise PQBSafeguardValidationError(
                f"redundancy_factor must be >= {MIN_LIFE_SUPPORT_REDUNDANCY} (N+2 safety margin)"
            )


@dataclass(frozen=True)
class VoluntaryHabitatTransfer:
    """Voluntary individual/household opt-in transfer request (C8)."""

    request_id: str
    persons_count: int
    motivation: TransferMotivation
    voluntary_consent_verified: bool = True
    free_exit_acknowledged: bool = True
    coercive_assignment: bool = False

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise PQBSafeguardValidationError("request_id must be non-empty")
        if self.persons_count < 1:
            raise PQBSafeguardValidationError("persons_count must be >= 1")


@dataclass(frozen=True)
class VoluntaryBioregenerativeHabitatPlan:
    """Industry P-Q-B specification for terrestrial or off-Earth voluntary protective habitats."""

    habitat_id: str
    placement: HabitatPlacementMode
    target_civilization_population: int
    requested_occupancy: int
    reserves: BioregenerativeReserveSpec
    voluntary_opt_in_only: bool = True
    free_exit_guaranteed: bool = True
    coercive_relocation_forbidden: bool = True
    universal_non_discriminatory_access: bool = True
    transfer_requests: tuple[VoluntaryHabitatTransfer, ...] = ()

    def __post_init__(self) -> None:
        if not self.habitat_id.strip():
            raise PQBSafeguardValidationError("habitat_id must be non-empty")
        if self.target_civilization_population < 1:
            raise PQBSafeguardValidationError("target_civilization_population must be >= 1")
        if self.requested_occupancy < 0:
            raise PQBSafeguardValidationError("requested_occupancy must be >= 0")


@dataclass(frozen=True)
class BioregenerativeHabitatEvaluation:
    """Outcome of C8 autonomy, N+2 Leontief capacity & B-layer reference potability check."""

    habitat_id: str
    placement: str
    certified_leontief_capacity: int
    limiting_resource_channel: str
    effective_requested_occupancy: int
    target_civilization_population: int
    civilization_coverage_ratio: float
    universal_humanity_coverage_ready: bool
    autonomy_and_consent_verified: bool
    life_support_and_wellbeing_verified: bool
    biosensor_loop_verified: bool
    passed: bool
    failure_kind: PQBSafeguardVerdictKind | None
    reasons: tuple[str, ...]
    simulation_and_advisory_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["failure_kind"] = self.failure_kind.value if self.failure_kind is not None else None
        return payload


@dataclass(frozen=True)
class PQBSafeguardProfile:
    """Immutable constitutional thresholds for Industry P-Q-B Triadic Safeguarding."""

    profile_id: str = "industry-pqb-triadic-safeguard.v1"
    min_earth_axis_floor: float = 0.35
    min_earth_pillar_mean: float = 0.45
    min_civilization_axis_floor: float = 0.35
    min_civilization_pillar_mean: float = 0.45
    min_infrastructure_axis_floor: float = 0.35
    min_infrastructure_pillar_mean: float = 0.45
    max_single_axis_sacrifice: float = 0.05
    max_domain_collateral_delta: float = 0.03
    max_crisis_ceiling: float = 0.75
    cascade_horizon_steps: int = 4
    cme_cascade_sensitivity: float = 0.35
    min_sevo: float = 1.5
    max_q_uncertainty: float = 0.35
    max_b_reference_disagreement: float = 0.15
    max_power_w: float = 250.0
    require_human_oversight: bool = True
    advisory_only: bool = True
    no_physical_actuation: bool = True

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise PQBSafeguardValidationError("profile_id must be non-empty")
        if (
            not self.require_human_oversight
            or not self.advisory_only
            or not self.no_physical_actuation
        ):
            raise PQBConstitutionalFaultError(
                "mandatory T006 safety flags (require_human_oversight, advisory_only, "
                "no_physical_actuation) cannot be disabled"
            )
        for fname in (
            "min_earth_axis_floor",
            "min_earth_pillar_mean",
            "min_civilization_axis_floor",
            "min_civilization_pillar_mean",
            "min_infrastructure_axis_floor",
            "min_infrastructure_pillar_mean",
            "max_single_axis_sacrifice",
            "max_domain_collateral_delta",
            "max_crisis_ceiling",
            "cme_cascade_sensitivity",
            "max_q_uncertainty",
            "max_b_reference_disagreement",
        ):
            require_unit_interval(fname, getattr(self, fname))
        if self.min_earth_pillar_mean < self.min_earth_axis_floor:
            raise PQBSafeguardValidationError("min_earth_pillar_mean < min_earth_axis_floor")
        if self.min_civilization_pillar_mean < self.min_civilization_axis_floor:
            raise PQBSafeguardValidationError(
                "min_civilization_pillar_mean < min_civilization_axis_floor"
            )
        if self.min_infrastructure_pillar_mean < self.min_infrastructure_axis_floor:
            raise PQBSafeguardValidationError(
                "min_infrastructure_pillar_mean < min_infrastructure_axis_floor"
            )
        s_min = require_finite("min_sevo", self.min_sevo)
        p_max = require_finite("max_power_w", self.max_power_w)
        if s_min <= 0.0 or p_max <= 0.0:
            raise PQBSafeguardValidationError("min_sevo and max_power_w must be > 0")
        if self.cascade_horizon_steps < 1:
            raise PQBSafeguardValidationError("cascade_horizon_steps must be >= 1")

    def axis_floor_for(self, pillar: TriadicPillar) -> float:
        if pillar is TriadicPillar.EARTH_BIOSPHERE:
            return self.min_earth_axis_floor
        if pillar is TriadicPillar.HUMAN_CIVILIZATION:
            return self.min_civilization_axis_floor
        return self.min_infrastructure_axis_floor

    def mean_floor_for(self, pillar: TriadicPillar) -> float:
        if pillar is TriadicPillar.EARTH_BIOSPHERE:
            return self.min_earth_pillar_mean
        if pillar is TriadicPillar.HUMAN_CIVILIZATION:
            return self.min_civilization_pillar_mean
        return self.min_infrastructure_pillar_mean

    def profile_sha256(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, allow_nan=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PQBCampaignProposal:
    """Candidate Industry P-Q-B campaign or protective habitat plan under evaluation."""

    proposal_id: str
    proposer_id: str
    reviewer_id: str
    human_oversight_approved: bool
    pre_cme: PQBCapitalVector
    post_cme: PQBCapitalVector
    initial_crisis: PolycrisisState
    crisis_intervention: tuple[tuple[str, float], ...] = ()
    telemetry: PQBTelemetrySnapshot = PQBTelemetrySnapshot()
    habitat_plan: VoluntaryBioregenerativeHabitatPlan | None = None

    def __post_init__(self) -> None:
        if not self.proposal_id.strip() or not self.proposer_id.strip():
            raise PQBSafeguardValidationError("proposal_id and proposer_id must be non-empty")
        valid_domains = {d.value for d in CRISIS_DOMAINS}
        seen: set[str] = set()
        for key, val in self.crisis_intervention:
            if key not in valid_domains:
                raise PQBSafeguardValidationError(f"unknown crisis domain: {key!r}")
            if key in seen:
                raise PQBSafeguardValidationError(f"duplicate crisis domain: {key!r}")
            seen.add(key)
            fval = require_finite(f"crisis_intervention[{key}]", val)
            if not (-1.0 <= fval <= 1.0):
                raise PQBSafeguardValidationError(f"crisis_intervention[{key}] must lie in [-1, 1]")

    @classmethod
    def create(
        cls,
        *,
        proposal_id: str,
        proposer_id: str,
        reviewer_id: str,
        human_oversight_approved: bool,
        pre_cme: PQBCapitalVector,
        post_cme: PQBCapitalVector,
        initial_crisis: PolycrisisState,
        crisis_intervention: Mapping[str, float] | None = None,
        telemetry: PQBTelemetrySnapshot | None = None,
        habitat_plan: VoluntaryBioregenerativeHabitatPlan | None = None,
    ) -> PQBCampaignProposal:
        items = (
            tuple(sorted((str(k), float(v)) for k, v in crisis_intervention.items()))
            if crisis_intervention
            else ()
        )
        return cls(
            proposal_id=proposal_id,
            proposer_id=proposer_id,
            reviewer_id=reviewer_id,
            human_oversight_approved=human_oversight_approved,
            pre_cme=pre_cme,
            post_cme=post_cme,
            initial_crisis=initial_crisis,
            crisis_intervention=items,
            telemetry=telemetry if telemetry is not None else PQBTelemetrySnapshot(),
            habitat_plan=habitat_plan,
        )

    def intervention_map(self) -> dict[str, float]:
        return dict(self.crisis_intervention)


@dataclass(frozen=True)
class PQBSafeguardVerdict:
    """SHA-256 verifiable advisory decision record emitted by PQBTriadicSafeguardController."""

    proposal_id: str
    verdict: PQBSafeguardVerdictKind
    approved_for_advisory: bool
    reasons: tuple[str, ...]
    pillar_metrics: dict[str, dict[str, float]]
    initial_synergy_index: float
    final_synergy_index: float
    baseline_final_synergy_index: float
    coupling_spectral_radius: float
    max_collateral_crisis_delta: float
    peak_propagated_crisis: float
    habitat_evaluation: dict[str, Any] | None = None
    advisory_only: bool = True
    verdict_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["verdict"] = self.verdict.value
        return payload
