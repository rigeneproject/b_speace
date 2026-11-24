"""End-to-end tests for BioOrchestrator and the `bspace` CLI."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from b_speace.cli import app
from b_speace.orchestrator import BioOrchestrator
from b_speace.organoid import OrganoidLifecycleState

runner = CliRunner()


@pytest.mark.asyncio
async def test_bio_orchestrator_end_to_end() -> None:
    orch = BioOrchestrator(num_channels=4, prefer_qspeace=False, seed=42)
    reports = await orch.run(ticks=5)
    assert len(reports) == 5
    assert all(r.viability_index > 0.7 for r in reports)
    assert all(not r.gate_blocked for r in reports)
    summary = orch.report()
    assert summary["ticks"] == 5
    assert summary["blocked_ticks"] == 0
    await orch.stop()
    assert orch.organoid.lifecycle_state() is OrganoidLifecycleState.SHUTDOWN


def test_cli_commands_smoke() -> None:
    res_bcel = runner.invoke(app, ["bcel", "list"])
    assert res_bcel.exit_code == 0
    assert "FUNCTIONAL" in res_bcel.stdout
    assert "ACCIDENTAL" in res_bcel.stdout

    res_bio = runner.invoke(app, ["bio", "simulate", "--channels", "4", "--steps", "10"])
    assert res_bio.exit_code == 0
    bio_payload = json.loads(res_bio.stdout)
    assert bio_payload["simulator"] == "fitzhugh_nagumo"
    assert bio_payload["steps"] == 10

    res_org = runner.invoke(app, ["organoid", "probe", "--channels", "4", "--ticks", "2"])
    assert res_org.exit_code == 0
    org_payload = json.loads(res_org.stdout)
    assert org_payload["is_simulated"] is True
    assert org_payload["final_lifecycle"] == "shutdown"

    res_bridge = runner.invoke(
        app, ["bridge", "run", "--ticks", "3", "--channels", "4", "--standalone"]
    )
    assert res_bridge.exit_code == 0
    bridge_payload = json.loads(res_bridge.stdout)
    assert bridge_payload["ticks"] == 3
    assert bridge_payload["blocked_ticks"] == 0
