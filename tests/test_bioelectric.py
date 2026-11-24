"""Tests for bio-electric signal simulation Protocols and Adapters."""

from __future__ import annotations

import math

import numpy as np
import pytest

from b_speace.bioelectric import (
    BioElectricSimulator,
    BioSignalDecoder,
    BioSignalEncoder,
    BioSignalValidationError,
    FitzHughNagumoAdapter,
    IonChannelParams,
    PopulationRateCodec,
    StimulationPulse,
)


def test_bioelectric_protocol_conformance() -> None:
    sim = FitzHughNagumoAdapter(num_channels=4, seed=7)
    codec = PopulationRateCodec()
    assert isinstance(sim, BioElectricSimulator)
    assert isinstance(codec, BioSignalEncoder)
    assert isinstance(codec, BioSignalDecoder)


def test_fitzhugh_nagumo_deterministic_and_evokes_spikes() -> None:
    pulse = StimulationPulse(
        channel_indices=(0, 1),
        amplitude_ua=15.0,
        duration_ms=4.0,
        start_ms=0.25,
        biphasic=False,
    )
    sim_a = FitzHughNagumoAdapter(num_channels=4, dt_ms=0.25, seed=123)
    sim_b = FitzHughNagumoAdapter(num_channels=4, dt_ms=0.25, seed=123)

    frames_a = sim_a.run(steps=40, pulses=[pulse])
    frames_b = sim_b.run(steps=40, pulses=[pulse])

    assert len(frames_a) == 40
    assert [f.potentials_mv for f in frames_a] == [f.potentials_mv for f in frames_b]
    assert sum(f.spike_count for f in frames_a) > 0
    assert all(f.instantaneous_power_uw > 0.0 for f in frames_a)


def test_bioelectric_fail_closed_validation() -> None:
    with pytest.raises(BioSignalValidationError):
        FitzHughNagumoAdapter(num_channels=0)
    with pytest.raises(BioSignalValidationError):
        FitzHughNagumoAdapter(num_channels=2, dt_ms=-0.1)
    with pytest.raises(BioSignalValidationError):
        IonChannelParams(tau=0.0).validate()

    sim = FitzHughNagumoAdapter(num_channels=3, seed=1)
    with pytest.raises(BioSignalValidationError):
        sim.step(np.array([1.0, float("nan"), 0.0]))
    with pytest.raises(BioSignalValidationError):
        sim.step([1.0, 2.0])  # wrong channel count
    with pytest.raises(BioSignalValidationError):
        sim.run(steps=-1)

    bad_pulse = StimulationPulse(channel_indices=(5,), amplitude_ua=1.0, duration_ms=1.0)
    with pytest.raises(BioSignalValidationError):
        sim.run(steps=2, pulses=[bad_pulse])


def test_population_rate_codec_roundtrip() -> None:
    sim = FitzHughNagumoAdapter(num_channels=4, seed=42)
    frames = sim.run(
        steps=16,
        pulses=[StimulationPulse(channel_indices=(0,), amplitude_ua=10.0, duration_ms=2.0)],
    )
    codec = PopulationRateCodec(max_pulse_amplitude_ua=12.0, default_pulse_duration_ms=1.5)
    features = codec.encode(frames)

    assert len(features.normalized_activity) == 4
    assert math.isclose(sum(features.normalized_activity), 1.0, rel_tol=1e-6)
    assert all(0.0 <= angle <= math.pi for angle in features.phase_angles_rad)
    assert 0.0 <= features.synchrony_index <= 1.0001
    assert features.shannon_entropy_bits >= 0.0

    pulses = codec.decode(features.normalized_activity, channel_count=4)
    assert len(pulses) == 4
    assert all(p.biphasic for p in pulses)

    with pytest.raises(BioSignalValidationError):
        codec.decode([1.5, 0.0, 0.0, 0.0], channel_count=4)
    with pytest.raises(BioSignalValidationError):
        codec.encode([])
