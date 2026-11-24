"""Tests for computational organoid (Wetware-in-the-loop) Protocols & Adapters."""

from __future__ import annotations

import pytest

from b_speace.organoid import (
    ChargeDensitySafetyGate,
    InMemoryTelemetrySink,
    OrganoidHealthError,
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


def test_organoid_protocol_conformance() -> None:
    sink = InMemoryTelemetrySink()
    gate = ChargeDensitySafetyGate()
    adapter = SimulatedOrganoidAdapter(num_channels=4, safety_gate=gate, telemetry_sink=sink)
    assert isinstance(gate, WetwareSafetyGate)
    assert isinstance(sink, WetwareTelemetrySink)
    assert isinstance(adapter, OrganoidInterface)


@pytest.mark.asyncio
async def test_organoid_lifecycle_and_closed_loop_step() -> None:
    sink = InMemoryTelemetrySink()
    adapter = SimulatedOrganoidAdapter(num_channels=4, telemetry_sink=sink, seed=99)
    assert adapter.lifecycle_state() is OrganoidLifecycleState.OFFLINE

    cmd_before_ready = StimulationCommand(
        target_channels=("mea_00",),
        amplitude_ua=3.0,
        voltage_mv=150.0,
        duration_ms=1.0,
    )
    with pytest.raises(OrganoidUnavailableError):
        await adapter.stimulate(cmd_before_ready)

    await adapter.connect()
    assert adapter.lifecycle_state() is OrganoidLifecycleState.CALIBRATING
    assert len(adapter.channels()) == 4

    health = await adapter.calibrate()
    assert adapter.lifecycle_state() is OrganoidLifecycleState.READY
    assert health.safe_to_stimulate is True
    assert health.active_channels == 4

    res = await adapter.closed_loop_step(cmd_before_ready, record_duration_ms=2.0)
    assert res.safety_approved is True
    assert len(res.recording.frames) > 0
    assert res.recording.estimated_energy_uj > 0.0
    assert len(sink.recordings) == 1
    assert len(sink.health_snapshots) >= 2

    await adapter.shutdown()
    assert adapter.lifecycle_state() is OrganoidLifecycleState.SHUTDOWN
    with pytest.raises(OrganoidUnavailableError):
        await adapter.connect()
    with pytest.raises(OrganoidUnavailableError):
        await adapter.record(1.0)


@pytest.mark.asyncio
async def test_organoid_safety_envelope_blocks_unsafe_commands() -> None:
    envelope = WetwareSafetyEnvelope(
        max_voltage_mv=500.0,
        max_current_ua=10.0,
        max_pulse_duration_ms=5.0,
        max_charge_density_uc_cm2=25.0,
        max_frequency_hz=50.0,
        require_biphasic=True,
    )
    gate = ChargeDensitySafetyGate(envelope=envelope)
    adapter = SimulatedOrganoidAdapter(num_channels=4, safety_gate=gate, seed=7)
    await adapter.connect()
    await adapter.calibrate()

    # Over-current
    with pytest.raises(OrganoidSafetyViolationError):
        await adapter.stimulate(
            StimulationCommand(
                target_channels=("mea_00",),
                amplitude_ua=15.0,
                voltage_mv=200.0,
                duration_ms=1.0,
            )
        )

    # Monophasic pulse rejected
    with pytest.raises(OrganoidSafetyViolationError):
        await adapter.stimulate(
            StimulationCommand(
                target_channels=("mea_00",),
                amplitude_ua=5.0,
                voltage_mv=200.0,
                duration_ms=1.0,
                biphasic=False,
            )
        )

    # Unknown channel
    with pytest.raises(OrganoidSafetyViolationError):
        await adapter.stimulate(
            StimulationCommand(
                target_channels=("mea_99",),
                amplitude_ua=5.0,
                voltage_mv=200.0,
                duration_ms=1.0,
            )
        )

    # Non-finite voltage
    with pytest.raises(OrganoidSafetyViolationError):
        await adapter.stimulate(
            StimulationCommand(
                target_channels=("mea_00",),
                amplitude_ua=5.0,
                voltage_mv=float("nan"),
                duration_ms=1.0,
            )
        )

    # Charge density violation (current and duration individually within bounds,
    # but Q/A exceeds max_charge_density_uc_cm2)
    with pytest.raises(OrganoidSafetyViolationError, match="charge density"):
        await adapter.stimulate(
            StimulationCommand(
                target_channels=("mea_00",),
                amplitude_ua=8.0,
                voltage_mv=200.0,
                duration_ms=2.0,
                biphasic=True,
            )
        )

    # Environmental health excursion (hyperthermia)
    adapter.set_environment(temperature_c=41.0)
    with pytest.raises(OrganoidHealthError):
        await adapter.stimulate(
            StimulationCommand(
                target_channels=("mea_00",),
                amplitude_ua=4.0,
                voltage_mv=150.0,
                duration_ms=1.0,
            )
        )

    await adapter.shutdown()
