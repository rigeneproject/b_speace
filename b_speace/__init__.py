"""B-SPEACE — Biological & Bio-Inspired Layer for the SPEACE framework.

Provides formal Protocol/Adapter abstractions for:
  - Bio-electric signal simulation (:mod:`b_speace.bioelectric`)
  - Computational organoids / Wetware-in-the-loop APIs (:mod:`b_speace.organoid`)
  - Hybrid classical-quantum interoperability with ``q_speace`` (:mod:`b_speace.interop`)
  - Biological-Cybernetic Equivalence gate (:mod:`b_speace.bcel`)
  - Closed-loop runtime orchestration (:mod:`b_speace.orchestrator`)
"""

from __future__ import annotations

from .bcel import BCELCatalog, BCELEquivalence
from .bioelectric import (
    BaseBioElectricAdapter,
    BioElectricError,
    BioElectricSimulator,
    BioSignalDecoder,
    BioSignalEncoder,
    BioSignalFrame,
    BioSignalValidationError,
    EncodedBioFeatures,
    FitzHughNagumoAdapter,
    IonChannelParams,
    MembraneState,
    PopulationRateCodec,
    StimulationPulse,
)
from .interop import (
    BaseBioQuantumAdapter,
    BioQuantumAdapter,
    HybridBindingSpec,
    HybridTickResult,
    InteropError,
    InteropGateBlockedError,
    InteropValidationError,
    QSpeaceKernelAdapter,
    QuantumBioPacket,
    QuantumKernelPort,
    SevoAssessment,
    StandaloneQuantumKernelAdapter,
    make_quantum_kernel_adapter,
)
from .orchestrator import BioOrchestrator, BioTickReport
from .organoid import (
    BaseOrganoidAdapter,
    ChargeDensitySafetyGate,
    ClosedLoopStepResult,
    ElectrodeChannel,
    InMemoryTelemetrySink,
    MEARecording,
    OrganoidCalibrationError,
    OrganoidError,
    OrganoidHealthError,
    OrganoidHealthSnapshot,
    OrganoidInterface,
    OrganoidLifecycleState,
    OrganoidSafetyViolationError,
    OrganoidUnavailableError,
    SimulatedOrganoidAdapter,
    StimulationCommand,
    WetwareSafetyEnvelope,
    WetwareSafetyGate,
    WetwareTelemetrySink,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "BCELCatalog",
    "BCELEquivalence",
    "BaseBioElectricAdapter",
    "BioElectricError",
    "BioElectricSimulator",
    "BioSignalDecoder",
    "BioSignalEncoder",
    "BioSignalFrame",
    "BioSignalValidationError",
    "EncodedBioFeatures",
    "FitzHughNagumoAdapter",
    "IonChannelParams",
    "MembraneState",
    "PopulationRateCodec",
    "StimulationPulse",
    "BaseOrganoidAdapter",
    "ChargeDensitySafetyGate",
    "ClosedLoopStepResult",
    "ElectrodeChannel",
    "InMemoryTelemetrySink",
    "MEARecording",
    "OrganoidCalibrationError",
    "OrganoidError",
    "OrganoidHealthError",
    "OrganoidHealthSnapshot",
    "OrganoidInterface",
    "OrganoidLifecycleState",
    "OrganoidSafetyViolationError",
    "OrganoidUnavailableError",
    "SimulatedOrganoidAdapter",
    "StimulationCommand",
    "WetwareSafetyEnvelope",
    "WetwareSafetyGate",
    "WetwareTelemetrySink",
    "BaseBioQuantumAdapter",
    "BioQuantumAdapter",
    "HybridBindingSpec",
    "HybridTickResult",
    "InteropError",
    "InteropGateBlockedError",
    "InteropValidationError",
    "QSpeaceKernelAdapter",
    "QuantumBioPacket",
    "QuantumKernelPort",
    "SevoAssessment",
    "StandaloneQuantumKernelAdapter",
    "make_quantum_kernel_adapter",
    "BioOrchestrator",
    "BioTickReport",
]
