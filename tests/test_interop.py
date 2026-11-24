"""Tests for B-SPEACE <-> Q-SPEACE hybrid classical-quantum interoperability."""

from __future__ import annotations

import importlib
import math

import pytest

from b_speace.bioelectric import EncodedBioFeatures
from b_speace.interop import (
    BaseBioQuantumAdapter,
    BioQuantumAdapter,
    HybridBindingSpec,
    InteropValidationError,
    QSpeaceKernelAdapter,
    QuantumKernelPort,
    StandaloneQuantumKernelAdapter,
    make_quantum_kernel_adapter,
)


def _sample_binding() -> HybridBindingSpec:
    return HybridBindingSpec(
        channel_to_role=(
            ("mea_00", "sensory_a"),
            ("mea_01", "sensory_b"),
            ("mea_02", "assoc_a"),
            ("mea_03", "assoc_b"),
        ),
        entangled_pairs=(("mea_00", "mea_02"), ("mea_01", "mea_03")),
        max_qubits=4,
        sevo_threshold=1.5,
        max_energy_w=250.0,
    )


def _sample_features() -> EncodedBioFeatures:
    return EncodedBioFeatures(
        channel_ids=("mea_00", "mea_01", "mea_02", "mea_03"),
        normalized_activity=(0.35, 0.25, 0.25, 0.15),
        phase_angles_rad=(math.pi / 2, math.pi / 3, math.pi / 4, math.pi / 5),
        firing_rate_hz=12.5,
        synchrony_index=0.82,
        shannon_entropy_bits=1.92,
    )


def test_interop_protocol_conformance() -> None:
    binding = _sample_binding()
    kernel = StandaloneQuantumKernelAdapter(binding=binding, seed=11)
    bridge = BaseBioQuantumAdapter(kernel=kernel)
    assert isinstance(kernel, QuantumKernelPort)
    assert isinstance(bridge, BioQuantumAdapter)
    assert kernel.kernel_summary()["num_qubits"] == 4
    assert kernel.kernel_summary()["num_entanglements"] == 2


def test_standalone_kernel_executes_and_gates_sevo() -> None:
    binding = _sample_binding()
    kernel = StandaloneQuantumKernelAdapter(binding=binding, seed=42)
    bridge = BaseBioQuantumAdapter(kernel=kernel)
    features = _sample_features()

    approved = bridge.step_hybrid(
        tick=0,
        features=features,
        delta_utility=4.0,
        delta_entropy_info=1.0,
        num_spikes=3,
    )
    assert approved.gate_blocked is False
    assert approved.sevo.approved is True
    assert approved.sevo.sevo == pytest.approx(4.0)
    assert approved.coherence_phi > 0.0
    assert len(approved.measurements) == 4
    assert all(0.0 <= v <= 1.0 for v in approved.feedback_modulation)

    # Low Sevo must be blocked fail-closed.
    blocked = bridge.step_hybrid(
        tick=1,
        features=features,
        delta_utility=0.5,
        delta_entropy_info=1.0,
        num_spikes=1,
    )
    assert blocked.gate_blocked is True
    assert blocked.sevo.approved is False
    assert blocked.sevo.reason == "sevo_below_threshold"
    assert blocked.coherence_phi == 0.0

    # Zero / negative delta_entropy_info must fail closed.
    zero_ent = bridge.step_hybrid(
        tick=2,
        features=features,
        delta_utility=5.0,
        delta_entropy_info=0.0,
    )
    assert zero_ent.gate_blocked is True
    assert zero_ent.sevo.approved is False


def test_binding_spec_validation_rejects_invalid_configs() -> None:
    with pytest.raises(InteropValidationError):
        HybridBindingSpec(channel_to_role=()).validate()
    with pytest.raises(InteropValidationError):
        HybridBindingSpec(
            channel_to_role=(("a", "q0"), ("a", "q1")),
        ).validate()
    with pytest.raises(InteropValidationError):
        HybridBindingSpec(
            channel_to_role=(("a", "q0"), ("b", "q1")),
            entangled_pairs=(("a", "a"),),
        ).validate()


def test_factory_returns_valid_kernel_port() -> None:
    kernel = make_quantum_kernel_adapter(binding=_sample_binding(), prefer_qspeace=False, seed=3)
    assert isinstance(kernel, QuantumKernelPort)
    assert kernel.backend_name == "standalone_numpy_quantum"


def test_qspeace_native_interop_when_installed() -> None:
    """Verify native QSpeaceKernelAdapter against live q_speace if importable."""
    try:
        importlib.import_module("q_speace")
    except ImportError:
        pytest.skip("q_speace is not installed in the active environment")

    binding = _sample_binding()
    kernel = QSpeaceKernelAdapter(binding=binding, seed=42)
    assert isinstance(kernel, QuantumKernelPort)
    bridge = BaseBioQuantumAdapter(kernel=kernel)
    res = bridge.step_hybrid(
        tick=0,
        features=_sample_features(),
        delta_utility=4.0,
        delta_entropy_info=1.0,
        num_spikes=2,
    )
    assert res.gate_blocked is False
    assert res.backend_name == "q_speace_hybrid_kernel"
    assert res.coherence_phi > 0.0
    assert len(res.measurements) == 4
    summary = kernel.kernel_summary()
    assert summary["num_qubits"] == 4
    assert summary["num_entanglements"] == 2
