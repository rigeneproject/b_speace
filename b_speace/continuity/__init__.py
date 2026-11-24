"""Multi-substrate functional continuity & transfer-lab engine (T005 M0/M1)."""

from __future__ import annotations

from .campaign import (
    H2DrillOutcome,
    H2DrillReport,
    M1CampaignSummary,
    run_h2_fault_drills,
    run_m1_regression_matrix,
    write_campaign_bundle,
)
from .engine import (
    AppendOnlyFrameLog,
    ContinuityEngine,
    IndependentPrefixOracle,
    VirtualDestinationEndpoint,
    closed_form_cold_backlog,
    closed_form_missed_actions,
    default_replica_profiles,
)
from .protocols import (
    DestinationEndpointPort,
    ProfileMatcher,
    StateOraclePort,
)
from .scoring import (
    ClassicalTrigonometricMatcher,
    H4EquivalenceReport,
    QuantumSingleQubitMatcher,
    verify_h4_equivalence_grid,
)
from .types import (
    AuthorityViolationError,
    Command,
    CommittedFrame,
    ContinuityError,
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

__all__ = [
    "AppendOnlyFrameLog",
    "AuthorityViolationError",
    "ClassicalTrigonometricMatcher",
    "Command",
    "CommittedFrame",
    "ContinuityEngine",
    "ContinuityError",
    "ContinuityMode",
    "ContinuityValidationError",
    "DestinationEndpointPort",
    "DestinationReceipt",
    "FaultSpec",
    "Grant",
    "H2DrillOutcome",
    "H2DrillReport",
    "H4EquivalenceReport",
    "IndependentPrefixOracle",
    "M1CampaignSummary",
    "Observation",
    "ProfileMatcher",
    "QuantumSingleQubitMatcher",
    "ReplicaState",
    "RunRecord",
    "StandbyMode",
    "StateOraclePort",
    "TickTraceEntry",
    "VirtualDestinationEndpoint",
    "closed_form_cold_backlog",
    "closed_form_missed_actions",
    "default_replica_profiles",
    "run_h2_fault_drills",
    "run_m1_regression_matrix",
    "verify_h4_equivalence_grid",
    "write_campaign_bundle",
]
