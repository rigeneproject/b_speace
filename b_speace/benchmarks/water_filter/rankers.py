"""Candidate material rankers for P-only / P+B vs P+Q / P+Q+B ablations (T003).

Implements:
- :class:`CandidateRanker`: ``@runtime_checkable`` Protocol.
- :class:`ClassicalBaselineRanker`: ranks candidates using classical historical priors.
- :class:`QuantumInteractionRanker`: invokes :class:`QuantumKernelPort`
  (``QSpeaceKernelAdapter`` or ``StandaloneQuantumKernelAdapter``) with explicit
  ``Sevo`` metabolic gating and Simplex-inspired uncertainty fallback
  (switching back to classical ordering whenever ``sigma_Q > max_uncertainty`` or
  the quantum gate blocks dispatch).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

from b_speace.bioelectric.types import EncodedBioFeatures
from b_speace.interop import (
    BaseBioQuantumAdapter,
    HybridBindingSpec,
    QuantumKernelPort,
    make_quantum_kernel_adapter,
)

from .model import CandidateDescriptor


@dataclass(frozen=True)
class RankedCandidate:
    """Candidate ordering entry with provenance, uncertainty, and cost accounting."""

    material_id: str
    score: float
    uncertainty: float
    source: str  # "classical" | "quantum" | "classical_fallback"
    quantum_energy_w: float = 0.0
    quantum_coherence_phi: float = 0.0
    sevo_approved: bool = True
    fallback_triggered: bool = False


@runtime_checkable
class CandidateRanker(Protocol):
    """Orders candidate materials before physical filter trials."""

    ranker_name: str
    uses_quantum: bool
    fixed_setup_cost_usd: float

    def rank(
        self, candidates: Sequence[CandidateDescriptor], *, seed: int | None = None
    ) -> list[RankedCandidate]:
        """Return candidates sorted best-first."""
        ...


class ClassicalBaselineRanker:
    """Orders candidates strictly by classical historical prior score."""

    ranker_name: str = "classical_prior_ranker"
    uses_quantum: bool = False
    fixed_setup_cost_usd: float = 0.0

    def rank(
        self, candidates: Sequence[CandidateDescriptor], *, seed: int | None = None
    ) -> list[RankedCandidate]:
        _ = seed
        ranked = [
            RankedCandidate(
                material_id=c.material_id,
                score=float(c.classical_prior_score),
                uncertainty=float(c.classical_uncertainty),
                source="classical",
            )
            for c in candidates
        ]
        ranked.sort(key=lambda r: r.score, reverse=True)
        return ranked


BindingEnergyEstimator = Callable[[str, np.random.Generator], tuple[float, float]]


class QuantumInteractionRanker:
    """Molecular-scale Q ranker gated by QuantumKernelPort (Sevo) & Simplex uncertainty.

    Combines a noisy molecular binding-energy estimate (e.g., VQE-style
    contaminant–site affinity) with a real circuit execution through
    :class:`b_speace.interop.QuantumKernelPort`. If ``Sevo`` blocks execution or
    estimated uncertainty ``sigma_Q`` exceeds ``max_quantum_uncertainty``, the
    Simplex rule falls back to the classical prior score.
    """

    ranker_name: str = "quantum_interaction_ranker"
    uses_quantum: bool = True

    def __init__(
        self,
        binding_estimator: BindingEnergyEstimator,
        *,
        max_quantum_uncertainty: float = 1.5,
        prefer_qspeace: bool = True,
        fixed_setup_cost_usd: float = 2500.0,
        marginal_cost_per_eval_usd: float = 15.0,
        eval_duration_min: float = 4.0,
        sevo_threshold: float = 1.5,
        seed: int | None = None,
    ) -> None:
        if not math.isfinite(max_quantum_uncertainty) or max_quantum_uncertainty < 0.0:
            raise ValueError("max_quantum_uncertainty must be finite and >= 0")
        self._estimator = binding_estimator
        self._max_unc = float(max_quantum_uncertainty)
        self._prefer_qspeace = prefer_qspeace
        self.fixed_setup_cost_usd: float = float(fixed_setup_cost_usd)
        self.marginal_cost_per_eval_usd: float = float(marginal_cost_per_eval_usd)
        self.eval_duration_min: float = float(eval_duration_min)
        self._sevo_threshold = float(sevo_threshold)
        self._seed = seed

    def _make_kernel(self, seed: int | None) -> QuantumKernelPort:
        binding = HybridBindingSpec(
            channel_to_role=(
                ("site_0", "binding_orbital_a"),
                ("site_1", "binding_orbital_b"),
                ("site_2", "solvation_a"),
                ("site_3", "solvation_b"),
            ),
            entangled_pairs=(("site_0", "site_1"), ("site_2", "site_3")),
            max_qubits=4,
            sevo_threshold=self._sevo_threshold,
            max_energy_w=250.0,
        )
        return make_quantum_kernel_adapter(
            binding=binding,
            prefer_qspeace=self._prefer_qspeace,
            seed=seed,
        )

    def rank(
        self, candidates: Sequence[CandidateDescriptor], *, seed: int | None = None
    ) -> list[RankedCandidate]:
        eff_seed = self._seed if seed is None else seed
        rng = np.random.default_rng(eff_seed)
        kernel = self._make_kernel(eff_seed)
        bridge = BaseBioQuantumAdapter(kernel=kernel)

        ranked: list[RankedCandidate] = []
        for idx, cand in enumerate(candidates):
            energy_kcal, sigma_q = self._estimator(cand.material_id, rng)
            # Build classical feature vector for the 4-qubit binding circuit.
            feats = cand.site_feature_vector[:4]
            if len(feats) < 4:
                feats = feats + (0.25,) * (4 - len(feats))
            norm_sum = sum(max(v, 1e-6) for v in feats)
            norm_act = tuple(max(v, 1e-6) / norm_sum for v in feats)
            # Encode normalized affinity magnitude into rotation angles [0, pi].
            affinity_unit = float(np.clip(-energy_kcal / 16.0, 0.05, 0.98))
            angles = tuple(
                float(np.clip((0.5 * affinity_unit + 0.5 * f) * math.pi, 0.05, math.pi))
                for f in feats
            )
            encoded = EncodedBioFeatures(
                channel_ids=("site_0", "site_1", "site_2", "site_3"),
                normalized_activity=norm_act,
                phase_angles_rad=angles,
                firing_rate_hz=0.0,
                synchrony_index=affinity_unit,
                shannon_entropy_bits=1.0,
            )
            # Higher uncertainty reduces expected utility gain (drives Sevo gate honestly).
            delta_utility = max(0.5, 4.0 / (1.0 + sigma_q))
            hybrid = bridge.step_hybrid(
                tick=idx,
                features=encoded,
                delta_utility=delta_utility,
                delta_entropy_info=1.0,
                num_spikes=0,
                enforce_gate=True,
            )

            # Simplex fail-closed check: fall back to classical prior if Sevo blocks or sigma_Q too high.
            if hybrid.gate_blocked or sigma_q > self._max_unc:
                ranked.append(
                    RankedCandidate(
                        material_id=cand.material_id,
                        score=float(cand.classical_prior_score),
                        uncertainty=float(cand.classical_uncertainty),
                        source="classical_fallback",
                        quantum_energy_w=hybrid.sevo.estimated_energy_w,
                        quantum_coherence_phi=hybrid.coherence_phi,
                        sevo_approved=hybrid.sevo.approved,
                        fallback_triggered=True,
                    )
                )
            else:
                # More negative binding energy => stronger affinity => higher score.
                # Combine quantum affinity estimate with classical prior weighted by inverse uncertainty.
                q_norm_score = float(np.clip(-energy_kcal / 15.0, 0.0, 1.5))
                combined_score = 0.85 * q_norm_score + 0.15 * float(cand.classical_prior_score)
                ranked.append(
                    RankedCandidate(
                        material_id=cand.material_id,
                        score=combined_score,
                        uncertainty=sigma_q,
                        source="quantum",
                        quantum_energy_w=hybrid.sevo.estimated_energy_w,
                        quantum_coherence_phi=hybrid.coherence_phi,
                        sevo_approved=True,
                        fallback_triggered=False,
                    )
                )

        ranked.sort(key=lambda r: r.score, reverse=True)
        return ranked
