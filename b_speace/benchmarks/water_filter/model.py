"""Hidden-state physical water-filter twin (Thomas / Bohart-Adams model, T003).

The controller ``P`` NEVER receives :class:`FilterMaterial` ground-truth kinetic
or equilibrium parameters; it only observes public :class:`CandidateDescriptor`
metadata and measurements returned by biosensors or reference assays.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from b_speace.biomolecular.types import ChemicalSample


@dataclass(frozen=True)
class FilterMaterial:
    """Hidden physical ground-truth parameters of a candidate filter medium.

    Attributes
    ----------
    material_id:
        Unique candidate identifier.
    q_max_mg_g:
        Equilibrium adsorption capacity (mg contaminant / g filter media).
    k_a_l_mg_min:
        Thomas mass-transfer / kinetic rate constant (L / (mg * min)).
    selectivity:
        Effective fraction of capacity available under real water matrix (0, 1].
    true_binding_energy_kcal_mol:
        Microscopic contaminant-binding-site interaction energy (more negative
        implies stronger equilibrium binding affinity, estimated noisily by Q).
    classical_prior_score:
        Cheap historical/classical screening score known before trials.
    classical_uncertainty:
        Uncertainty of the classical prior estimate.
    matrix_interference:
        Relative matrix perturbation seen by cell-free biosensors.
    """

    material_id: str
    q_max_mg_g: float
    k_a_l_mg_min: float
    selectivity: float = 1.0
    true_binding_energy_kcal_mol: float = -8.0
    classical_prior_score: float = 0.5
    classical_uncertainty: float = 0.25
    matrix_interference: float = 0.0

    def validate(self) -> None:
        if not self.material_id:
            raise ValueError("material_id must be non-empty")
        for name, val in (
            ("q_max_mg_g", self.q_max_mg_g),
            ("k_a_l_mg_min", self.k_a_l_mg_min),
            ("selectivity", self.selectivity),
            ("true_binding_energy_kcal_mol", self.true_binding_energy_kcal_mol),
            ("classical_prior_score", self.classical_prior_score),
            ("classical_uncertainty", self.classical_uncertainty),
            ("matrix_interference", self.matrix_interference),
        ):
            if not math.isfinite(val):
                raise ValueError(f"{name} must be finite (got {val!r})")
        if self.q_max_mg_g <= 0.0 or self.k_a_l_mg_min <= 0.0:
            raise ValueError("q_max_mg_g and k_a_l_mg_min must be > 0")
        if not (0.0 < self.selectivity <= 1.0):
            raise ValueError("selectivity must be in (0, 1]")
        if self.classical_uncertainty < 0.0:
            raise ValueError("classical_uncertainty must be >= 0")


@dataclass(frozen=True)
class CandidateDescriptor:
    """Public candidate view exposed to controller P and rankers (zero leakage)."""

    material_id: str
    classical_prior_score: float
    classical_uncertainty: float
    site_feature_vector: tuple[float, ...]


def default_water_filter_materials() -> tuple[FilterMaterial, ...]:
    """Canonical 5-material suite spanning poor, kinetic-limited, marginal, and optimal media.

    In classical historical order, low-capacity candidates appear first while
    stronger candidates appear later — testing both early-stop feedback (B)
    and molecular affinity re-ranking (Q).
    """
    return (
        FilterMaterial(
            material_id="mat_weak_a",
            q_max_mg_g=4.0,
            k_a_l_mg_min=0.15,
            selectivity=1.0,
            true_binding_energy_kcal_mol=-4.2,
            classical_prior_score=0.72,
            classical_uncertainty=0.30,
        ),
        FilterMaterial(
            material_id="mat_weak_b",
            q_max_mg_g=6.5,
            k_a_l_mg_min=0.12,
            selectivity=0.90,
            true_binding_energy_kcal_mol=-5.8,
            classical_prior_score=0.68,
            classical_uncertainty=0.28,
        ),
        FilterMaterial(
            material_id="mat_kinetic_c",
            q_max_mg_g=13.0,
            k_a_l_mg_min=0.08,
            selectivity=1.0,
            true_binding_energy_kcal_mol=-11.6,
            classical_prior_score=0.62,
            classical_uncertainty=0.25,
        ),
        FilterMaterial(
            material_id="mat_marginal_d",
            q_max_mg_g=10.6,
            k_a_l_mg_min=0.14,
            selectivity=0.98,
            true_binding_energy_kcal_mol=-8.4,
            classical_prior_score=0.58,
            classical_uncertainty=0.22,
        ),
        FilterMaterial(
            material_id="mat_optimal_e",
            q_max_mg_g=14.5,
            k_a_l_mg_min=0.16,
            selectivity=1.0,
            true_binding_energy_kcal_mol=-13.2,
            classical_prior_score=0.54,
            classical_uncertainty=0.20,
        ),
    )


class WaterFilterTwin:
    """Hidden-state fixed-bed filter physical twin (Thomas / Bohart-Adams model).

    Effluent concentration at treated volume ``V = Q * t``:
        C_out(V; Q) = C_0 / (1 + exp((k_a / Q) * (selectivity * q_max * M_bed - C_0 * V)))
    """

    def __init__(
        self,
        materials: Sequence[FilterMaterial] | None = None,
        *,
        contaminant: str = "Pb2+",
        inlet_concentration_mg_l: float = 1.0,
        limit_concentration_mg_l: float = 0.10,
        bed_mass_g: float = 10.0,
        target_volume_l: float = 100.0,
        flow_high_l_min: float = 2.0,
        flow_low_l_min: float = 0.8,
    ) -> None:
        mats = tuple(materials) if materials is not None else default_water_filter_materials()
        if not mats:
            raise ValueError("materials must be non-empty")
        seen: set[str] = set()
        for mat in mats:
            mat.validate()
            if mat.material_id in seen:
                raise ValueError(f"duplicate material_id: {mat.material_id!r}")
            seen.add(mat.material_id)
        for name, val in (
            ("inlet_concentration_mg_l", inlet_concentration_mg_l),
            ("limit_concentration_mg_l", limit_concentration_mg_l),
            ("bed_mass_g", bed_mass_g),
            ("target_volume_l", target_volume_l),
            ("flow_high_l_min", flow_high_l_min),
            ("flow_low_l_min", flow_low_l_min),
        ):
            if not math.isfinite(val) or val <= 0.0:
                raise ValueError(f"{name} must be finite and > 0 (got {val!r})")
        if limit_concentration_mg_l >= inlet_concentration_mg_l:
            raise ValueError("limit_concentration_mg_l must be < inlet_concentration_mg_l")
        if flow_low_l_min >= flow_high_l_min:
            raise ValueError("flow_low_l_min must be < flow_high_l_min")

        self._materials: dict[str, FilterMaterial] = {m.material_id: m for m in mats}
        self._order: tuple[str, ...] = tuple(m.material_id for m in mats)
        self.contaminant: str = contaminant
        self.inlet_concentration_mg_l: float = float(inlet_concentration_mg_l)
        self.limit_concentration_mg_l: float = float(limit_concentration_mg_l)
        self.bed_mass_g: float = float(bed_mass_g)
        self.target_volume_l: float = float(target_volume_l)
        self.flow_high_l_min: float = float(flow_high_l_min)
        self.flow_low_l_min: float = float(flow_low_l_min)
        self._sample_counter = 0

    def descriptors(self) -> tuple[CandidateDescriptor, ...]:
        """Return ONLY public descriptors visible to controller P (no hidden ground truth)."""
        out: list[CandidateDescriptor] = []
        for idx, mid in enumerate(self._order):
            m = self._materials[mid]
            # Public molecular-site descriptor (normalized geometry/polarity proxy).
            # Intentionally omits hidden kinetics (k_a) and capacity (q_max).
            norm_prior = float(np.clip(m.classical_prior_score, 0.0, 1.0))
            norm_unc = float(np.clip(m.classical_uncertainty, 0.0, 1.0))
            site_idx = (idx + 1) / max(len(self._order), 1)
            out.append(
                CandidateDescriptor(
                    material_id=mid,
                    classical_prior_score=m.classical_prior_score,
                    classical_uncertainty=m.classical_uncertainty,
                    site_feature_vector=(norm_prior, norm_unc, site_idx, 1.0 - norm_unc),
                )
            )
        return tuple(out)

    def _effluent_concentration(
        self, material_id: str, flow_rate_l_min: float, treated_volume_l: float
    ) -> float:
        m = self._materials[material_id]
        effective_capacity_mg = m.selectivity * m.q_max_mg_g * self.bed_mass_g
        exponent = (m.k_a_l_mg_min / flow_rate_l_min) * (
            effective_capacity_mg - self.inlet_concentration_mg_l * treated_volume_l
        )
        # Clamp exponent for numerical stability against overflow.
        clamped = max(-60.0, min(60.0, exponent))
        return float(self.inlet_concentration_mg_l / (1.0 + math.exp(clamped)))

    def sample_effluent(
        self,
        *,
        material_id: str,
        flow_rate_l_min: float,
        treated_volume_l: float,
        sampled_at_min: float,
    ) -> ChemicalSample:
        """Draw a downstream water sample to pass exclusively to sensor/assay adapters."""
        if material_id not in self._materials:
            raise KeyError(f"unknown material_id: {material_id!r}")
        if flow_rate_l_min <= 0.0 or treated_volume_l < 0.0 or sampled_at_min < 0.0:
            raise ValueError("flow_rate_l_min must be > 0; treated_volume_l and time >= 0")
        self._sample_counter += 1
        c_out = self._effluent_concentration(material_id, flow_rate_l_min, treated_volume_l)
        m = self._materials[material_id]
        return ChemicalSample(
            sample_id=f"smp_{self._sample_counter:05d}_{material_id}",
            sampled_at_min=sampled_at_min,
            treated_volume_l=treated_volume_l,
            contaminant=self.contaminant,
            true_concentration_mg_l=c_out,
            matrix_interference=m.matrix_interference,
        )

    def estimate_quantum_binding_energy(
        self,
        material_id: str,
        *,
        noise_std_kcal_mol: float,
        rng: np.random.Generator,
    ) -> tuple[float, float]:
        """Simulate a molecular-scale binding energy estimate (kcal/mol, uncertainty).

        Reflects molecular affinity (barring macroscopic mass-transfer kinetics k_a),
        aligned with Barroca et al. (2024) VQE binding-potential workflows.
        """
        m = self._materials[material_id]
        sigma = max(0.0, float(noise_std_kcal_mol))
        noise = float(rng.normal(0.0, sigma)) if sigma > 0.0 else 0.0
        return float(m.true_binding_energy_kcal_mol + noise), sigma

    def oracle_is_compliant(self, material_id: str, flow_rate_l_min: float) -> bool:
        """Post-hoc ground-truth check (evaluator only, never called by controller P)."""
        c_final = self._effluent_concentration(material_id, flow_rate_l_min, self.target_volume_l)
        return c_final <= self.limit_concentration_mg_l

    def oracle_has_any_compliant(self) -> bool:
        """Return True if at least one candidate passes at either high or low flow."""
        return any(
            self.oracle_is_compliant(mid, self.flow_high_l_min)
            or self.oracle_is_compliant(mid, self.flow_low_l_min)
            for mid in self._order
        )

    def oracle_has_high_flow_compliant(self) -> bool:
        """Return True if at least one candidate passes at the high flow rate."""
        return any(self.oracle_is_compliant(mid, self.flow_high_l_min) for mid in self._order)
