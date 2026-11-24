"""Reproducible paired experiment runner for P vs P+B and 4-way P-Q-B ablations (T003)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from b_speace.biomolecular import (
    BiosensorCalibration,
    CellFreeThresholdSensorAdapter,
    SimulatedReferenceAssayAdapter,
)

from .controller import (
    AblationMode,
    CampaignResult,
    FilterTrialConfig,
    FilterTrialController,
)
from .model import FilterMaterial, WaterFilterTwin
from .rankers import CandidateRanker, ClassicalBaselineRanker, QuantumInteractionRanker


@dataclass(frozen=True)
class ModeAggregate:
    """Multi-seed aggregated metrics for a single ablation configuration."""

    mode: str
    seeds: int
    mean_time_to_confirm_min: float
    mean_trials_started: float
    mean_early_stops: float
    mean_treated_volume_l: float
    mean_ref_assays: float
    mean_b_assays: float
    wrong_selection_rate: float
    high_flow_rate: float
    mean_marginal_cost_usd: float
    fixed_setup_cost_usd: float
    mean_energy_wh: float
    b_fallback_rate: float
    q_fallback_rate: float


@dataclass(frozen=True)
class AblationReport:
    """Paired ablation comparison with per-mode aggregates and sample provenance trace."""

    experiment_name: str
    seeds: tuple[int, ...]
    aggregates: dict[str, ModeAggregate]
    sample_campaigns: dict[str, CampaignResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_name": self.experiment_name,
            "seeds": list(self.seeds),
            "aggregates": {k: asdict(v) for k, v in self.aggregates.items()},
            "sample_decision_traces": {
                k: [asdict(rec) for rec in camp.decision_trace]
                for k, camp in self.sample_campaigns.items()
            },
        }


@dataclass(frozen=True)
class SweepPoint:
    """One operating point in the (delay_B, noise_B, drift_B) convenience map."""

    incubation_delay_min: float
    noise_std: float
    drift_rate_per_min: float
    p_mean_time_min: float
    pb_mean_time_min: float
    time_saved_min: float
    time_saved_pct: float
    p_wrong_rate: float
    pb_wrong_rate: float
    pb_fallback_rate: float
    recommended_for_lab: bool


def _aggregate(mode: AblationMode, results: Sequence[CampaignResult]) -> ModeAggregate:
    n = len(results)
    if n == 0:
        raise ValueError("results must be non-empty")
    return ModeAggregate(
        mode=mode.value,
        seeds=n,
        mean_time_to_confirm_min=round(sum(r.time_to_confirm_min for r in results) / n, 3),
        mean_trials_started=round(sum(r.trials_started for r in results) / n, 3),
        mean_early_stops=round(sum(r.early_stops for r in results) / n, 3),
        mean_treated_volume_l=round(sum(r.total_treated_volume_l for r in results) / n, 3),
        mean_ref_assays=round(sum(r.reference_assays_used for r in results) / n, 3),
        mean_b_assays=round(sum(r.biosensor_assays_used for r in results) / n, 3),
        wrong_selection_rate=round(sum(0 if r.selection_correct else 1 for r in results) / n, 4),
        high_flow_rate=round(sum(1 if r.high_flow_confirmed else 0 for r in results) / n, 4),
        mean_marginal_cost_usd=round(sum(r.marginal_campaign_cost_usd for r in results) / n, 2),
        fixed_setup_cost_usd=round(results[0].fixed_setup_cost_usd, 2),
        mean_energy_wh=round(sum(r.estimated_energy_wh for r in results) / n, 4),
        b_fallback_rate=round(sum(1 if r.b_fallback_triggered else 0 for r in results) / n, 4),
        q_fallback_rate=round(sum(1 if r.q_fallback_triggered else 0 for r in results) / n, 4),
    )


def _run_modes(
    *,
    experiment_name: str,
    modes: Sequence[AblationMode],
    seeds: Sequence[int],
    materials: Sequence[FilterMaterial] | None = None,
    calibration: BiosensorCalibration | None = None,
    config: FilterTrialConfig | None = None,
    quantum_noise_std_kcal_mol: float = 0.6,
    max_quantum_uncertainty: float = 1.5,
    prefer_qspeace: bool = True,
) -> AblationReport:
    controller = FilterTrialController(config=config)
    seed_tuple = tuple(int(s) for s in seeds)
    if not seed_tuple:
        raise ValueError("seeds must be non-empty")

    per_mode: dict[AblationMode, list[CampaignResult]] = {m: [] for m in modes}

    for s in seed_tuple:
        for mode in modes:
            twin = WaterFilterTwin(materials=materials)
            cal = calibration or BiosensorCalibration(
                contaminant=twin.contaminant,
                threshold_mg_l=twin.limit_concentration_mg_l,
                kd_mg_l=twin.limit_concentration_mg_l,
                hill_n=3.0,
                incubation_delay_min=5.0,
                noise_std=0.04,
                drift_rate_per_min=0.0,
            )
            sensor = CellFreeThresholdSensorAdapter(calibration=cal, seed=s)
            ref = SimulatedReferenceAssayAdapter(seed=s)

            ranker: CandidateRanker
            if mode in (AblationMode.P_PLUS_Q, AblationMode.P_PLUS_Q_PLUS_B):

                def _estimator(
                    mid: str,
                    rng: np.random.Generator,
                    _twin: WaterFilterTwin = twin,
                    _noise: float = quantum_noise_std_kcal_mol,
                ) -> tuple[float, float]:
                    return _twin.estimate_quantum_binding_energy(
                        mid, noise_std_kcal_mol=_noise, rng=rng
                    )

                ranker = QuantumInteractionRanker(
                    binding_estimator=_estimator,
                    max_quantum_uncertainty=max_quantum_uncertainty,
                    prefer_qspeace=prefer_qspeace,
                    seed=s,
                )
            else:
                ranker = ClassicalBaselineRanker()

            res = controller.run_campaign(
                twin,
                mode=mode,
                reference_assay=ref,
                biosensor=(
                    sensor
                    if mode in (AblationMode.P_PLUS_B, AblationMode.P_PLUS_Q_PLUS_B)
                    else None
                ),
                ranker=ranker,
                seed=s,
            )
            per_mode[mode].append(res)

    aggregates = {m.value: _aggregate(m, per_mode[m]) for m in modes}
    samples = {m.value: per_mode[m][0] for m in modes}
    return AblationReport(
        experiment_name=experiment_name,
        seeds=seed_tuple,
        aggregates=aggregates,
        sample_campaigns=samples,
    )


def run_p_vs_pb_experiment(
    *,
    seeds: Sequence[int] = (11, 22, 33, 44, 55),
    materials: Sequence[FilterMaterial] | None = None,
    calibration: BiosensorCalibration | None = None,
    config: FilterTrialConfig | None = None,
) -> AblationReport:
    """Experiment 1 (T003): paired P vs P+B closed-loop biosensor feedback comparison."""
    return _run_modes(
        experiment_name="T003_experiment_1_P_vs_PB",
        modes=(AblationMode.P_ONLY, AblationMode.P_PLUS_B),
        seeds=seeds,
        materials=materials,
        calibration=calibration,
        config=config,
    )


def run_four_way_ablation(
    *,
    seeds: Sequence[int] = (11, 22, 33, 44, 55),
    materials: Sequence[FilterMaterial] | None = None,
    calibration: BiosensorCalibration | None = None,
    config: FilterTrialConfig | None = None,
    quantum_noise_std_kcal_mol: float = 0.6,
    max_quantum_uncertainty: float = 1.5,
    prefer_qspeace: bool = True,
) -> AblationReport:
    """Experiment 2 (T003): full T002 4-way ablation (P, P+B, P+Q, P+Q+B)."""
    return _run_modes(
        experiment_name="T003_experiment_2_four_way_PQB",
        modes=(
            AblationMode.P_ONLY,
            AblationMode.P_PLUS_B,
            AblationMode.P_PLUS_Q,
            AblationMode.P_PLUS_Q_PLUS_B,
        ),
        seeds=seeds,
        materials=materials,
        calibration=calibration,
        config=config,
        quantum_noise_std_kcal_mol=quantum_noise_std_kcal_mol,
        max_quantum_uncertainty=max_quantum_uncertainty,
        prefer_qspeace=prefer_qspeace,
    )


def run_parametric_b_sweep(
    *,
    delays_min: Sequence[float] = (2.0, 5.0, 15.0),
    noise_stds: Sequence[float] = (0.02, 0.08, 0.22),
    drift_rates: Sequence[float] = (0.0, 0.004),
    seeds: Sequence[int] = (11, 22, 33),
    materials: Sequence[FilterMaterial] | None = None,
    config: FilterTrialConfig | None = None,
) -> list[SweepPoint]:
    """Sweep biosensor (delay, noise, drift) to map lab-viability operating regimes."""
    points: list[SweepPoint] = []
    for delay in delays_min:
        for noise in noise_stds:
            for drift in drift_rates:
                cal = BiosensorCalibration(
                    contaminant="Pb2+",
                    threshold_mg_l=0.10,
                    kd_mg_l=0.10,
                    hill_n=3.0,
                    incubation_delay_min=delay,
                    noise_std=noise,
                    drift_rate_per_min=drift,
                )
                rep = run_p_vs_pb_experiment(
                    seeds=seeds,
                    materials=materials,
                    calibration=cal,
                    config=config,
                )
                p_agg = rep.aggregates[AblationMode.P_ONLY.value]
                pb_agg = rep.aggregates[AblationMode.P_PLUS_B.value]
                saved = p_agg.mean_time_to_confirm_min - pb_agg.mean_time_to_confirm_min
                pct = (
                    (saved / p_agg.mean_time_to_confirm_min) * 100.0
                    if p_agg.mean_time_to_confirm_min > 0.0
                    else 0.0
                )
                recommended = (
                    saved > 0.0
                    and pb_agg.wrong_selection_rate <= p_agg.wrong_selection_rate
                    and pb_agg.b_fallback_rate < 0.5
                )
                points.append(
                    SweepPoint(
                        incubation_delay_min=float(delay),
                        noise_std=float(noise),
                        drift_rate_per_min=float(drift),
                        p_mean_time_min=p_agg.mean_time_to_confirm_min,
                        pb_mean_time_min=pb_agg.mean_time_to_confirm_min,
                        time_saved_min=round(saved, 3),
                        time_saved_pct=round(pct, 2),
                        p_wrong_rate=p_agg.wrong_selection_rate,
                        pb_wrong_rate=pb_agg.wrong_selection_rate,
                        pb_fallback_rate=pb_agg.b_fallback_rate,
                        recommended_for_lab=recommended,
                    )
                )
    return points
