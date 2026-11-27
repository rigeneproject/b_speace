"""BCEL catalog — biological & wetware equivalences for B-SPEACE (T001).

Implements the Biological-Cybernetic Equivalence gate mirroring
``q_speace/bcel/catalog.py``: each biological/bio-inspired concept is
classified as ``accidental`` (carbon-substrate narrative or non-operational
metaphor removed in silicon) or ``functional`` (testable mathematical,
control-theoretic, or software-safety rule retained in code).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BCELClassification = Literal["accidental", "functional"]


@dataclass(frozen=True)
class BCELEquivalence:
    """Single BCEL classification entry."""

    concept: str
    classification: BCELClassification
    digital_rule: str


_BIO_EQUIVALENCES: tuple[BCELEquivalence, ...] = (
    BCELEquivalence(
        concept="Excitable membrane dynamics (FitzHugh-Nagumo / Hodgkin-Huxley)",
        classification="functional",
        digital_rule=(
            "Keep as deterministic coupled ODE integrators over bounded membrane "
            "potential and recovery variables with finite-value validation; models "
            "nonlinear excitability and refractory pacing without claiming biological life."
        ),
    ),
    BCELEquivalence(
        concept="Gap-junction bio-electric coupling",
        classification="functional",
        digital_rule=(
            "Keep as a symmetric sparse diffusive coupling matrix (graph Laplacian) "
            "modulating inter-channel current exchange."
        ),
    ),
    BCELEquivalence(
        concept="Wetware-in-the-loop MEA closed-loop stimulation envelope",
        classification="functional",
        digital_rule=(
            "Keep as a fail-closed software interlock enforcing bounded voltage, "
            "current, pulse duration, charge density per phase, stimulation frequency, "
            "and environmental telemetry (temperature, pH, viability) before any "
            "stimulation dispatch."
        ),
    ),
    BCELEquivalence(
        concept="Organoid plasticity / adaptive excitability",
        classification="functional",
        digital_rule=(
            "Keep as bounded state-dependent gain/threshold adaptation tracked via "
            "deterministic telemetry and reversible calibration resets."
        ),
    ),
    BCELEquivalence(
        concept="Bio-quantum signal encoding & Sevo entropic efficiency gate",
        classification="functional",
        digital_rule=(
            "Keep as angle/amplitude classical-to-quantum feature mapping feeding "
            "q_speace circuits, gated by positive entropic efficiency Sevo = dU / dS_info "
            "and finite energy budgets. Entanglement is strictly a computational binding "
            "resource (no-communication theorem)."
        ),
    ),
    BCELEquivalence(
        concept="Organoid consciousness, sentience, or subjective experience",
        classification="accidental",
        digital_rule=(
            "Removed in silicon and prohibited in runtime claims: bio-electric "
            "oscillations and MEA closed-loop feedback are signal-processing dynamics, "
            "never evidence of consciousness, pain, or moral agency."
        ),
    ),
    BCELEquivalence(
        concept="Vitalist 'living intelligence' or teleological wetware agency",
        classification="accidental",
        digital_rule=(
            "Removed: narrative metaphor only; runtime components expose explicit "
            "lifecycle states, typed errors, and bounded control contracts."
        ),
    ),
    BCELEquivalence(
        concept="Non-local bio-quantum telepathy or FTL neural entanglement",
        classification="accidental",
        digital_rule=(
            "Removed and prohibited: all bio-to-quantum and quantum-to-bio exchanges "
            "occur via classical measurement outcomes and classical telemetry packets."
        ),
    ),
    # --- T002 / T003: Industry P-Q-B & Cell-Free Water-Filter Benchmark ---
    BCELEquivalence(
        concept="Cell-free allosteric threshold biosensing (ROSALIND-style Hill transduction)",
        classification="functional",
        digital_rule=(
            "Keep as a calibrated Hill transfer function with explicit incubation lag, "
            "stochastic readout noise, matrix interference, and drift parameters, always "
            "paired with independent reference assay verification."
        ),
    ),
    BCELEquivalence(
        concept="Fixed-bed breakthrough dynamics normalized by treated volume (Thomas / Bohart-Adams)",
        classification="functional",
        digital_rule=(
            "Keep as a hidden-state physical twin separating equilibrium capacity from "
            "mass-transfer kinetics across flow rates at equal treated volume V = Q * t."
        ),
    ),
    BCELEquivalence(
        concept="Simplex-inspired uncertainty and drift fail-closed switching (P-Q-B)",
        classification="functional",
        digital_rule=(
            "Keep as a deterministic supervisor downgrading B on reference-assay "
            "disagreement/drift or downgrading Q on high uncertainty / Sevo gate block, "
            "falling back safely to classical models and reference assays."
        ),
    ),
    BCELEquivalence(
        concept="Speculative retrocausal bio-quantum learning or vitalist wetware optimization",
        classification="accidental",
        digital_rule=(
            "Removed: excluded from runtime architecture and claims; P-Q-B value is "
            "established solely through causal closed-loop provenance and pre-registered "
            "4-way ablations (P, P+B, P+Q, P+Q+B)."
        ),
    ),
    # --- T005: Multi-Substrate Functional Continuity Transfer Lab (b_speace -> q_speace) ---
    BCELEquivalence(
        concept="Replicated state-machine prefix framing, epoch fencing, and destination idempotency (T005 H1/H2)",
        classification="functional",
        digital_rule=(
            "Keep as deterministic append-only CommittedFrame logs, monotonic epoch "
            "mandates rejecting stale holders (including same-ID re-assignment), "
            "out-of-order gap cursors, and idempotent destination deduplication per "
            "(session, tick, action_id)."
        ),
    ),
    BCELEquivalence(
        concept="Information-matched bio-inspired vs. classical EMA temporal ablation (T005 H3)",
        classification="functional",
        digital_rule=(
            "Keep as a fairness control comparing FitzHugh-Nagumo features against "
            "classical EMA memory on identical inputs, equal hyperparameter grid "
            "budgets, disjoint seed splits, and paired bootstrap CI (archiving null "
            "results explicitly)."
        ),
    ),
    BCELEquivalence(
        concept="Analytical quantum dequantization equivalence gate (T005 H4)",
        classification="functional",
        digital_rule=(
            "Keep as a numerical verification gate checking single-qubit embeddings "
            "against closed-form cos^2[pi*(x-p)/2] within 1e-12 and explicitly "
            "declaring classical sufficiency whenever quantum advantage is absent."
        ),
    ),
    BCELEquivalence(
        concept="Anti-abstention coverage-weighted fault evaluation metric (T005 M2b)",
        classification="functional",
        digital_rule=(
            "Keep as joint reporting of accuracy on executed commands and fraction of "
            "evaluable ticks with a correct accepted action (counting missed actions "
            "as failures) so fail-closed controllers cannot inflate accuracy by abstaining."
        ),
    ),
    BCELEquivalence(
        concept="Multi-substrate subjective consciousness continuity or mind-copying persistence (T005)",
        classification="accidental",
        digital_rule=(
            "Removed and prohibited in runtime claims: state synchronization and "
            "authority failover establish only operational continuity of software "
            "replicas, never continuation of first-person subjective experience."
        ),
    ),
    # --- T006: Industry P-Q-B Triadic Safeguard, Anti-Polycrisis & Voluntary Habitat (q_speace T254) ---
    BCELEquivalence(
        concept="Planetary organism gestation or infallible off-world ark teleology (T006)",
        classification="accidental",
        digital_rule=(
            "Removed from runtime claims: P-Q-B software and wetware twins hold zero "
            "conscious planetary identity, cannot guarantee physical survival without "
            "real-world civil/aerospace/ecological qualification, and forbid coercive "
            "relocation or abandonment of Earth's biosphere."
        ),
    ),
    BCELEquivalence(
        concept="Industry P-Q-B non-compensable triadic substrate & polycrisis shield (T006)",
        classification="functional",
        digital_rule=(
            "Keep as an exact 3x4 CME Leontief floor check over Earth, Human Civilization, "
            "and Tech Infrastructure coupled with 5-domain discrete polycrisis propagation, "
            "anti-risk-transfer bounds, and P-Q-B Simplex Sevo/biosensor/wetware gates (C6, C7)."
        ),
    ),
    BCELEquivalence(
        concept="P-Q-B bioregenerative voluntary protective habitat protocol (T006)",
        classification="functional",
        digital_rule=(
            "Keep as opt-in individual admission and guaranteed free exit (polycrisis_protection "
            "or personal_wellbeing), N+2 Leontief capacity across water, food, oxygen, clean "
            "power, medical, and psychosocial wellbeing stocks, reference-verified B-layer "
            "loop monitoring, and non-abandonment of Earth (C8)."
        ),
    ),
)


class BCELCatalog:
    """Query interface for B-SPEACE BCEL classifications."""

    def __init__(self, entries: tuple[BCELEquivalence, ...] | None = None) -> None:
        self._entries: tuple[BCELEquivalence, ...] = (
            entries if entries is not None else _BIO_EQUIVALENCES
        )

    def all(self) -> list[BCELEquivalence]:
        """Return all registered BCEL equivalences."""
        return list(self._entries)

    def functional(self) -> list[BCELEquivalence]:
        """Return concepts kept as mathematical or software rules."""
        return [e for e in self._entries if e.classification == "functional"]

    def accidental(self) -> list[BCELEquivalence]:
        """Return concepts removed as non-operational metaphors."""
        return [e for e in self._entries if e.classification == "accidental"]

    def summary(self) -> dict[str, int]:
        """Return counts by classification."""
        func_count = sum(1 for e in self._entries if e.classification == "functional")
        acc_count = sum(1 for e in self._entries if e.classification == "accidental")
        return {
            "total": len(self._entries),
            "functional": func_count,
            "accidental": acc_count,
        }
