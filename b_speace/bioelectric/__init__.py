"""Bio-electric signal simulation layer for B-SPEACE."""

from __future__ import annotations

from .adapters import (
    BaseBioElectricAdapter,
    FitzHughNagumoAdapter,
    PopulationRateCodec,
)
from .protocols import (
    BioElectricSimulator,
    BioSignalDecoder,
    BioSignalEncoder,
)
from .types import (
    BioElectricError,
    BioSignalFrame,
    BioSignalValidationError,
    EncodedBioFeatures,
    IonChannelParams,
    MembraneState,
    StimulationPulse,
)

__all__ = [
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
]
