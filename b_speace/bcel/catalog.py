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
