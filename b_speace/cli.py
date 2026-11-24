"""B-SPEACE command-line interface (`bspace`).

Mirrors the Typer subcommand structure of ``q_speace/cli.py``:
  - ``bspace bcel ...``      — Biological-Cybernetic Equivalence gate catalog
  - ``bspace bio ...``       — Bio-electric signal simulation
  - ``bspace organoid ...``  — Wetware-in-the-loop MEA twin probe
  - ``bspace bridge ...``    — Hybrid bio-quantum orchestrator loop
  - ``bspace benchmark ...`` — Industry P-Q-B reproducible benchmarks (T003)
  - ``bspace continuity ...``— T005 functional continuity & transfer lab (M0/M1)
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from .bcel import BCELCatalog
from .benchmarks import (
    run_four_way_ablation,
    run_p_vs_pb_experiment,
    run_parametric_b_sweep,
)
from .bioelectric import FitzHughNagumoAdapter, PopulationRateCodec, StimulationPulse
from .continuity import (
    ContinuityEngine,
    ContinuityMode,
    FaultSpec,
    StandbyMode,
    run_m1_regression_matrix,
    write_campaign_bundle,
)
from .orchestrator import BioOrchestrator
from .organoid import SimulatedOrganoidAdapter, StimulationCommand

app = typer.Typer(help="B-SPEACE biological & bio-inspired layer CLI")
bcel_app = typer.Typer(help="BCEL biological-cybernetic equivalence catalog")
bio_app = typer.Typer(help="Bio-electric signal simulation")
organoid_app = typer.Typer(help="Wetware-in-the-loop computational organoid twin")
bridge_app = typer.Typer(help="Hybrid B-SPEACE <-> Q-SPEACE orchestrator")
benchmark_app = typer.Typer(help="Industry P-Q-B closed-loop benchmarks (T003)")
continuity_app = typer.Typer(help="T005 functional continuity verification (M0/M1)")

app.add_typer(bcel_app, name="bcel")
app.add_typer(bio_app, name="bio")
app.add_typer(organoid_app, name="organoid")
app.add_typer(bridge_app, name="bridge")
app.add_typer(benchmark_app, name="benchmark")
app.add_typer(continuity_app, name="continuity")


@bcel_app.command("list")
def bcel_list() -> None:
    """Print registered BCEL functional/accidental equivalences."""
    catalog = BCELCatalog()
    typer.echo(f"BCEL summary: {catalog.summary()}")
    for entry in catalog.all():
        typer.echo(f"[{entry.classification.upper()}] {entry.concept}")
        typer.echo(f"  -> {entry.digital_rule}")


@bio_app.command("simulate")
def bio_simulate(
    channels: int = typer.Option(4, "--channels", "-c", min=1, max=64),
    steps: int = typer.Option(20, "--steps", "-s", min=1),
    amplitude_ua: float = typer.Option(12.0, "--amplitude", "-a"),
    seed: int = typer.Option(42, "--seed"),
) -> None:
    """Run a deterministic FitzHugh-Nagumo bio-electric simulation."""
    sim = FitzHughNagumoAdapter(num_channels=channels, seed=seed)
    pulse = StimulationPulse(
        channel_indices=(0,),
        amplitude_ua=amplitude_ua,
        duration_ms=2.0,
        start_ms=0.5,
        biphasic=True,
    )
    frames = sim.run(steps=steps, pulses=[pulse])
    features = PopulationRateCodec().encode(frames)
    payload = {
        "simulator": sim.simulator_name,
        "steps": len(frames),
        "total_spikes": sum(f.spike_count for f in frames),
        "firing_rate_hz": round(features.firing_rate_hz, 3),
        "synchrony_index": round(features.synchrony_index, 4),
        "shannon_entropy_bits": round(features.shannon_entropy_bits, 4),
    }
    typer.echo(json.dumps(payload, indent=2))


@organoid_app.command("probe")
def organoid_probe(
    channels: int = typer.Option(4, "--channels", "-c", min=1, max=32),
    ticks: int = typer.Option(3, "--ticks", "-t", min=1),
    seed: int = typer.Option(42, "--seed"),
) -> None:
    """Run an in-silico Wetware-in-the-loop MEA calibration and stimulation probe."""

    async def _run() -> dict[str, object]:
        adapter = SimulatedOrganoidAdapter(num_channels=channels, seed=seed)
        await adapter.connect()
        health = await adapter.calibrate()
        total_spikes = 0
        try:
            first_ch = adapter.channels()[0].channel_id
            cmd = StimulationCommand(
                target_channels=(first_ch,),
                amplitude_ua=3.0,
                voltage_mv=150.0,
                duration_ms=1.0,
                frequency_hz=10.0,
                biphasic=True,
            )
            for _ in range(ticks):
                res = await adapter.closed_loop_step(cmd, record_duration_ms=2.0)
                total_spikes += res.recording.total_spikes
        finally:
            await adapter.shutdown()
        return {
            "adapter": adapter.adapter_name,
            "is_simulated": adapter.is_simulated,
            "calibrated_viability": health.viability_index,
            "ticks": ticks,
            "total_spikes": total_spikes,
            "final_lifecycle": adapter.lifecycle_state().value,
        }

    typer.echo(json.dumps(asyncio.run(_run()), indent=2))


@bridge_app.command("run")
def bridge_run(
    ticks: int = typer.Option(5, "--ticks", "-t", min=1),
    channels: int = typer.Option(4, "--channels", "-c", min=1, max=8),
    prefer_qspeace: bool = typer.Option(True, "--prefer-qspeace/--standalone"),
    seed: int = typer.Option(42, "--seed"),
) -> None:
    """Run the BioOrchestrator coupled to the hybrid classical-quantum kernel."""

    async def _run() -> dict[str, float | int | str]:
        orch = BioOrchestrator(
            num_channels=channels,
            prefer_qspeace=prefer_qspeace,
            seed=seed,
        )
        try:
            await orch.run(ticks=ticks)
            return orch.report()
        finally:
            await orch.stop()

    typer.echo(json.dumps(asyncio.run(_run()), indent=2))


@benchmark_app.command("water-filter")
def benchmark_water_filter(
    mode: str = typer.Option("four-way", "--mode", "-m", help="p-vs-pb | four-way | sweep"),
    seeds: int = typer.Option(5, "--seeds", "-n", min=1, max=50),
    prefer_qspeace: bool = typer.Option(True, "--prefer-qspeace/--standalone"),
    out: Annotated[
        Path | None, typer.Option("--out", "-o", help="Optional JSON output file")
    ] = None,
) -> None:
    """Run the T003 digital water-treatment filter P-Q-B closed-loop benchmark."""
    seed_list = tuple(11 * (i + 1) for i in range(seeds))
    if mode == "p-vs-pb":
        report = run_p_vs_pb_experiment(seeds=seed_list)
        payload: dict[str, object] = report.to_dict()
    elif mode == "four-way":
        report = run_four_way_ablation(seeds=seed_list, prefer_qspeace=prefer_qspeace)
        payload = report.to_dict()
    elif mode == "sweep":
        points = run_parametric_b_sweep(seeds=seed_list[: min(3, len(seed_list))])
        payload = {
            "experiment_name": "T003_parametric_b_sweep",
            "points": [asdict(p) for p in points],
        }
    else:
        raise typer.BadParameter("mode must be one of: p-vs-pb, four-way, sweep")

    rendered = json.dumps(payload, indent=2)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + "\n", encoding="utf-8")
    typer.echo(rendered)


@continuity_app.command("run")
def continuity_run(
    mode: str = typer.Option("P", "--mode", "-m", help="P | P+Q | P+B | P+Q+B"),
    standby: str = typer.Option("warm", "--standby", "-s", help="warm | cold"),
    fault_tick: int = typer.Option(8, "--fault-tick", "-f", min=0),
    replay_budget: int = typer.Option(2, "--replay-budget", "-r", min=1),
    ticks: int = typer.Option(24, "--ticks", "-t", min=1),
    seed: int = typer.Option(42, "--seed"),
) -> None:
    """Run a single deterministic T005 functional continuity session (M0)."""
    try:
        c_mode = ContinuityMode(mode)
    except ValueError as exc:
        raise typer.BadParameter("mode must be one of: P, P+Q, P+B, P+Q+B") from exc
    try:
        s_mode = StandbyMode(standby)
    except ValueError as exc:
        raise typer.BadParameter("standby must be one of: warm, cold") from exc

    engine = ContinuityEngine()
    rec = engine.run(
        mode=c_mode,
        fault=FaultSpec(fault_tick=fault_tick, replay_budget=replay_budget, standby_mode=s_mode),
        horizon_ticks=ticks,
        seed=seed,
    )
    payload = {
        "session_id": rec.session_id,
        "input_hash": rec.input_hash,
        "mode": rec.mode.value,
        "standby_mode": rec.standby_mode.value,
        "fault_tick": rec.fault_tick,
        "replay_budget": rec.replay_budget,
        "first_recovery_tick": rec.first_recovery_tick,
        "missed_actions": rec.missed_actions,
        "expected_missed_actions": rec.expected_missed_actions,
        "background_updates_before_fault": rec.background_updates_before_fault,
        "authority_violations": rec.authority_violations,
        "duplicate_effects": rec.duplicate_effects,
        "max_context_error": rec.max_context_error,
        "winner_replica": rec.winner_replica,
    }
    typer.echo(json.dumps(payload, indent=2))


@continuity_app.command("evaluate")
def continuity_evaluate(
    seed: int = typer.Option(42, "--seed"),
    ticks: int = typer.Option(24, "--ticks", "-t", min=1),
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Directory for M1 campaign bundle")
    ] = None,
) -> None:
    """Run the full T005-B M1 regression matrix, H2 fault drills, and H4 equivalence gate."""
    summary = run_m1_regression_matrix(seed=seed, horizon_ticks=ticks)
    written: dict[str, str] = {}
    if output is not None:
        paths = write_campaign_bundle(output, summary)
        written = {k: str(v) for k, v in paths.items()}
    payload = {
        "all_passed": summary.all_passed,
        "total_matrix_runs": summary.total_matrix_runs,
        "oracle_exact_matches": summary.oracle_exact_matches,
        "q_on_off_exact_matches": summary.q_on_off_exact_matches,
        "total_authority_violations": summary.total_authority_violations,
        "total_duplicate_effects": summary.total_duplicate_effects,
        "max_context_error": summary.max_context_error,
        "h2_drills_passed": summary.h2_drills.all_passed,
        "h4_grid_points": summary.h4_equivalence.grid_points_tested,
        "h4_max_abs_error": summary.h4_equivalence.max_abs_error,
        "h4_classical_sufficient": summary.h4_equivalence.classical_sufficient,
        "bundle_files": written,
    }
    typer.echo(json.dumps(payload, indent=2))
