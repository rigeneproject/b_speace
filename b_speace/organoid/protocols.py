"""Formal Protocols for computational organoids (Wetware-in-the-loop APIs, T001).

Mirrors the style of ``q_speace/spiking_brain/interface.py``: every backend
(in-silico MEA twin, cloud wetware RPC client, or lab MEA driver) MUST
implement :class:`OrganoidInterface` and enforce a :class:`WetwareSafetyGate`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from .types import (
    ClosedLoopStepResult,
    ElectrodeChannel,
    MEARecording,
    OrganoidHealthSnapshot,
    OrganoidLifecycleState,
    StimulationCommand,
    WetwareSafetyEnvelope,
)


@runtime_checkable
class WetwareSafetyGate(Protocol):
    """Fail-closed safety gate validating stimulation commands and culture health."""

    envelope: WetwareSafetyEnvelope

    def validate_command(
        self,
        command: StimulationCommand,
        channels: Sequence[ElectrodeChannel],
        health: OrganoidHealthSnapshot,
    ) -> None:
        """Raise :class:`OrganoidSafetyViolationError` or :class:`OrganoidHealthError` if unsafe."""
        ...


@runtime_checkable
class WetwareTelemetrySink(Protocol):
    """Observer receiving MEA recordings and health telemetry snapshots."""

    def emit_recording(self, recording: MEARecording) -> None:
        """Record an MEA acquisition event."""
        ...

    def emit_health(self, health: OrganoidHealthSnapshot) -> None:
        """Record an environmental/viability health snapshot."""
        ...


@runtime_checkable
class OrganoidInterface(Protocol):
    """Formal async Wetware-in-the-loop contract for computational organoids."""

    adapter_name: str
    is_simulated: bool
    supports_closed_loop: bool
    safety_envelope: WetwareSafetyEnvelope

    def lifecycle_state(self) -> OrganoidLifecycleState:
        """Return the current lifecycle state."""
        ...

    def channels(self) -> tuple[ElectrodeChannel, ...]:
        """Return registered MEA electrode descriptors."""
        ...

    async def connect(self) -> None:
        """Open transport / initialize twin and transition OFFLINE -> CALIBRATING."""
        ...

    async def calibrate(self) -> OrganoidHealthSnapshot:
        """Verify impedances and viability; transition CALIBRATING -> READY."""
        ...

    async def stimulate(self, command: StimulationCommand) -> None:
        """Validate and dispatch a stimulation pulse train."""
        ...

    async def record(self, duration_ms: float) -> MEARecording:
        """Acquire a multi-channel MEA recording over ``duration_ms``."""
        ...

    async def closed_loop_step(
        self, command: StimulationCommand, record_duration_ms: float
    ) -> ClosedLoopStepResult:
        """Atomically stimulate (if safe) and capture the evoked MEA response."""
        ...

    async def health(self) -> OrganoidHealthSnapshot:
        """Return current environmental, impedance, and viability telemetry."""
        ...

    async def shutdown(self) -> None:
        """Safely disarm electrodes and transition any state -> SHUTDOWN."""
        ...
