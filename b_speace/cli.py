"""B-SPEACE command-line interface (`bspace`).

Mirrors the Typer subcommand structure of ``q_speace/cli.py``:
  - ``bspace bcel ...``      — Biological-Cybernetic Equivalence gate catalog
  - ``bspace bio ...``       — Bio-electric signal simulation
  - ``bspace organoid ...``  — Wetware-in-the-loop MEA twin probe
  - ``bspace bridge ...``    — Hybrid bio-quantum orchestrator loop
"""

from __future__ import annotations

import asyncio
import json

import typer

from .bcel import BCELCatalog
from .bioelectric import FitzHughNagumoAdapter, PopulationRateCodec, StimulationPulse
from .orchestrator import BioOrchestrator
from .organoid import SimulatedOrganoidAdapter, StimulationCommand

app = typer.Typer(help="B-SPEACE biological & bio-inspired layer CLI")
bcel_app = typer.Typer(help="BCEL biological-cybernetic equivalence catalog")
bio_app = typer.Typer(help="Bio-electric signal simulation")
organoid_app = typer.Typer(help="Wetware-in-the-loop computational organoid twin")
bridge_app = typer.Typer(help="Hybrid B-SPEACE <-> Q-SPEACE orchestrator")

app.add_typer(bcel_app, name="bcel")
app.add_typer(bio_app, name="bio")
app.add_typer(organoid_app, name="organoid")
app.add_typer(bridge_app, name="bridge")


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
