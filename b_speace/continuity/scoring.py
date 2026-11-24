"""Profile matching and H4 analytical quantum dequantization verification (T005)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from .types import ContinuityValidationError

_TIE_DECIMALS = 12


def _validate_unit_scalar(val: float, name: str) -> float:
    if not math.isfinite(val):
        raise ContinuityValidationError(f"{name} must be finite (got {val!r})")
    if not (0.0 <= val <= 1.0):
        raise ContinuityValidationError(f"{name} must be in [0, 1] (got {val!r})")
    return float(val)


def _pick_winner(scores: dict[str, float]) -> tuple[str, float]:
    if not scores:
        raise ContinuityValidationError("profiles must be non-empty")
    # Ties within 12 decimal places break lexicographically by replica name (T005-B §3).
    winner = min(
        scores.keys(),
        key=lambda rid: (-round(scores[rid], _TIE_DECIMALS), rid),
    )
    return winner, scores[winner]


class ClassicalTrigonometricMatcher:
    """Exact closed-form profile scorer: ``cos^2[pi * (x - p) / 2]``."""

    matcher_name: str = "classical_cos2_matcher"
    uses_quantum: bool = False

    def score(self, context: float, profile: float) -> float:
        x = _validate_unit_scalar(context, "context")
        p = _validate_unit_scalar(profile, "profile")
        val = math.cos(0.5 * math.pi * (x - p)) ** 2
        return float(val)

    def select_winner(
        self, context: float, profiles: Mapping[str, float]
    ) -> tuple[str, float, dict[str, float]]:
        scores = {rid: self.score(context, prof) for rid, prof in profiles.items()}
        winner, best = _pick_winner(scores)
        return winner, best, scores


class QuantumSingleQubitMatcher:
    """Single-qubit real state-vector overlap scorer with fail-closed fallback (H4).

    Encodes ``|psi(theta)> = cos(pi*theta/2)|0> + sin(pi*theta/2)|1>`` and computes
    state fidelity ``|<psi(x)|psi(p)>|^2``. Analytically identical to
    ``cos^2[pi*(x - p)/2]`` (used to verify numerical equivalence within ``1e-12``
    and explicitly report classical sufficiency per T005-A/B).
    """

    matcher_name: str = "quantum_1qubit_overlap_matcher"
    uses_quantum: bool = True

    def __init__(self, *, backend_unavailable: bool = False) -> None:
        self.backend_unavailable: bool = backend_unavailable
        self._fallback = ClassicalTrigonometricMatcher()
        self.fallback_count: int = 0

    @staticmethod
    def _state_vector(theta: float) -> np.ndarray:
        half = 0.5 * math.pi * theta
        return np.array([math.cos(half), math.sin(half)], dtype=np.complex128)

    def score(self, context: float, profile: float) -> float:
        # Always validate inputs fail-closed BEFORE any backend fallback.
        x = _validate_unit_scalar(context, "context")
        p = _validate_unit_scalar(profile, "profile")
        if self.backend_unavailable:
            self.fallback_count += 1
            return self._fallback.score(x, p)
        psi_x = self._state_vector(x)
        psi_p = self._state_vector(p)
        overlap = np.vdot(psi_x, psi_p)
        fidelity = float(np.abs(overlap) ** 2)
        return fidelity

    def select_winner(
        self, context: float, profiles: Mapping[str, float]
    ) -> tuple[str, float, dict[str, float]]:
        scores = {rid: self.score(context, prof) for rid, prof in profiles.items()}
        winner, best = _pick_winner(scores)
        return winner, best, scores


@dataclass(frozen=True)
class H4EquivalenceReport:
    """Verification report for H4 analytical quantum dequantization gate."""

    grid_points_tested: int
    max_abs_error: float
    tolerance: float
    grid_passed: bool
    tie_cases_passed: bool
    fallback_passed: bool
    invalid_input_rejected: bool
    classical_sufficient: bool

    @property
    def all_passed(self) -> bool:
        return (
            self.grid_passed
            and self.tie_cases_passed
            and self.fallback_passed
            and self.invalid_input_rejected
        )


def verify_h4_equivalence_grid(*, step: float = 0.01, tol: float = 1e-12) -> H4EquivalenceReport:
    """Execute T005-B §3 H4 full Cartesian grid + tie + fallback + invalid-input checks."""
    if not math.isfinite(step) or step <= 0.0 or step > 0.5:
        raise ContinuityValidationError(f"step must be in (0, 0.5] (got {step!r})")
    classical = ClassicalTrigonometricMatcher()
    quantum = QuantumSingleQubitMatcher(backend_unavailable=False)

    n_steps = round(1.0 / step)
    axis = [round(i * step, 10) for i in range(n_steps + 1)]
    max_err = 0.0
    tested = 0
    for x in axis:
        for p in axis:
            c_val = classical.score(x, p)
            q_val = quantum.score(x, p)
            err = abs(q_val - c_val)
            if err > max_err:
                max_err = err
            tested += 1

    # Exact tie & near-tie triples (including symmetric profiles around x=0.5).
    tie_triples: list[tuple[float, dict[str, float]]] = [
        (0.5, {"robotica": 0.3, "bio_robotica": 0.7, "digitale": 0.1}),
        (0.5, {"z_replica": 0.5, "a_replica": 0.5, "m_replica": 0.2}),
        (0.5, {"r1": 0.5 + 1e-7, "r2": 0.5 - 2e-7, "r3": 0.9}),
    ]
    ties_ok = True
    for ctx, profs in tie_triples:
        w_c, s_c, _ = classical.select_winner(ctx, profs)
        w_q, s_q, _ = quantum.select_winner(ctx, profs)
        if w_c != w_q or abs(s_c - s_q) > tol:
            ties_ok = False
            break

    # Backend-unavailable fallback on valid input.
    q_down = QuantumSingleQubitMatcher(backend_unavailable=True)
    fb_score = q_down.score(0.42, 0.65)
    fallback_ok = q_down.fallback_count == 1 and abs(fb_score - classical.score(0.42, 0.65)) <= tol

    # Non-finite input must fail closed even when backend is unavailable.
    invalid_rejected = False
    try:
        q_down.score(float("nan"), 0.5)
    except ContinuityValidationError:
        invalid_rejected = True

    return H4EquivalenceReport(
        grid_points_tested=tested,
        max_abs_error=max_err,
        tolerance=tol,
        grid_passed=max_err <= tol,
        tie_cases_passed=ties_ok,
        fallback_passed=fallback_ok,
        invalid_input_rejected=invalid_rejected,
        classical_sufficient=True,
    )
