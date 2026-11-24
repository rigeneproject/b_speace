"""Digital water-treatment filter P-Q-B closed-loop benchmark (T003)."""

from __future__ import annotations

from .controller import (
    AblationMode,
    CampaignResult,
    DecisionAction,
    DecisionRecord,
    FilterTrialConfig,
    FilterTrialController,
)
from .model import (
    CandidateDescriptor,
    FilterMaterial,
    WaterFilterTwin,
    default_water_filter_materials,
)
from .rankers import (
    CandidateRanker,
    ClassicalBaselineRanker,
    QuantumInteractionRanker,
    RankedCandidate,
)
from .runner import (
    AblationReport,
    SweepPoint,
    run_four_way_ablation,
    run_p_vs_pb_experiment,
    run_parametric_b_sweep,
)

__all__ = [
    "AblationMode",
    "AblationReport",
    "CampaignResult",
    "CandidateDescriptor",
    "CandidateRanker",
    "ClassicalBaselineRanker",
    "DecisionAction",
    "DecisionRecord",
    "FilterMaterial",
    "FilterTrialConfig",
    "FilterTrialController",
    "QuantumInteractionRanker",
    "RankedCandidate",
    "SweepPoint",
    "WaterFilterTwin",
    "default_water_filter_materials",
    "run_four_way_ablation",
    "run_p_vs_pb_experiment",
    "run_parametric_b_sweep",
]
