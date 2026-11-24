"""Formal @runtime_checkable Protocols for biomolecular biosensors (T003)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import (
    BiosensorCalibration,
    BiosensorReading,
    ChemicalSample,
    ReferenceAssayResult,
)


@runtime_checkable
class BiomolecularSensor(Protocol):
    """Cell-free or cellular molecular sensor converting concentration to threshold alerts."""

    sensor_name: str
    calibration: BiosensorCalibration

    def reset(self, seed: int | None = None) -> None:
        """Reset internal drift clock and RNG state."""
        ...

    def sense(
        self, sample: ChemicalSample, *, elapsed_campaign_min: float = 0.0
    ) -> BiosensorReading:
        """Process a chemical sample and return a thresholded biosensor reading."""
        ...


@runtime_checkable
class ReferenceAssayPort(Protocol):
    """Independent analytical laboratory assay (e.g., LC-MS / ICP-MS) for verification."""

    assay_name: str
    turnaround_min: float
    cost_per_sample_usd: float
    energy_per_sample_wh: float

    def reset(self, seed: int | None = None) -> None:
        """Reset assay RNG state."""
        ...

    def measure(self, sample: ChemicalSample, *, limit_mg_l: float) -> ReferenceAssayResult:
        """Return an independent quantitative concentration measurement."""
        ...
