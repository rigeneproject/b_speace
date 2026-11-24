# B-SPEACE — Biological & Bio-Inspired Layer for SPEACE

![CI](https://github.com/rigeneproject/b_speace/actions/workflows/ci.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Biological and bio-inspired computational layer for the **SPEACE** framework,
architected as a modular peer of [`q_speace`](https://github.com/rigeneproject/q_speace)
and `cellular_speace`.

B-SPEACE is **not** a living or conscious entity and makes **no** claim of
biological sentience. It is a typed, test-verified computational abstraction
layer that defines formal `Protocol` / `Adapter` contracts for:

1. **Bio-electric signal simulation** (`b_speace.bioelectric`): excitable
   membrane dynamics (e.g., FitzHugh–Nagumo reference simulator), multi-channel
   bio-potential frames, spike-rate/phase encoders and decoders.
2. **Computational organoids — Wetware-in-the-loop APIs** (`b_speace.organoid`):
   lifecycle-managed async MEA (Multi-Electrode Array) interfaces with
   fail-closed `WetwareSafetyEnvelope` interlocks (voltage, current, charge
   density, frequency, viability/temperature/pH bounds) and an in-silico
   reference twin (`SimulatedOrganoidAdapter`).
3. **Hybrid classical-quantum interoperability with `q_speace`** (`b_speace.interop`):
   structural `Protocol` ports (`QuantumKernelPort`, `BioQuantumAdapter`) and a
   zero-hard-dependency `QSpeaceKernelAdapter` that maps bio-electric/MEA
   activity into normalized neural vectors, named-role circuits
   (`BrainQuantumCircuit`), `QuantumNeuralBridge` bindings, and metabolic
   `Sevo` efficiency gating.
4. **BCEL Equivalence Gate** (`b_speace.bcel`): explicit classification of
   every bio-computational concept into `functional` (kept as mathematical /
   engineering rules) vs `accidental` (non-operational biological metaphor
   removed in silicon).

## Modular architecture

```text
b_speace/
├── bcel/           # Biological-Cybernetic Equivalence gate catalog
├── bioelectric/    # Bio-electric simulation Protocols, types & FitzHugh-Nagumo adapter
├── organoid/       # Wetware-in-the-loop async Protocols, safety envelope & MEA twin adapter
├── interop/        # Structural Protocols & adapters for q_speace hybrid quantum kernel
├── orchestrator.py # BioOrchestrator wiring bio-electric, organoid & quantum layers with Sevo gate
└── cli.py          # Typer CLI (`bspace`)
```

| Layer | Module | Key Protocols / Adapters |
|---|---|---|
| BCEL Gate | `b_speace/bcel/` | `BCELCatalog`, `BCELEquivalence` |
| Bio-Electric | `b_speace/bioelectric/` | `BioElectricSimulator`, `BioSignalEncoder`, `BioSignalDecoder`, `FitzHughNagumoAdapter`, `PopulationRateCodec` |
| Biomolecular (Cell-Free) | `b_speace/biomolecular/` | `BiomolecularSensor`, `ReferenceAssayPort`, `CellFreeThresholdSensorAdapter`, `SimulatedReferenceAssayAdapter` |
| Wetware-in-the-Loop | `b_speace/organoid/` | `OrganoidInterface`, `WetwareSafetyGate`, `BaseOrganoidAdapter`, `SimulatedOrganoidAdapter`, `ChargeDensitySafetyGate` |
| `q_speace` Interop | `b_speace/interop/` | `QuantumKernelPort`, `BioQuantumAdapter`, `QSpeaceKernelAdapter`, `StandaloneQuantumKernelAdapter` |
| P–Q–B Benchmarks | `b_speace/benchmarks/water_filter/` | `WaterFilterTwin`, `FilterTrialController`, `CandidateRanker`, `QuantumInteractionRanker`, `run_four_way_ablation` |
| Runtime | `b_speace/orchestrator.py` | `BioOrchestrator`, `BioTickReport` |

## Installation

```bash
cd b_speace
pip install -e ".[dev]"

# Optional interoperability with q_speace (when installed alongside):
pip install -e ".[qspeace]"
```

## Quickstart

```bash
pytest                      # run unit & interop test suite with coverage
bspace bcel list            # display BCEL functional/accidental classifications
bspace bio simulate -s 20   # run deterministic FitzHugh-Nagumo bio-electric simulation
bspace organoid probe -t 5  # run in-silico MEA organoid wetware-in-the-loop loop
bspace bridge run -t 10     # run BioOrchestrator coupled to hybrid quantum kernel
```

## Engineering Specifications & Invariants

- [T001 — B-SPEACE Modular Architecture & Protocol/Adapter Specification](docs/T001_BSPEACE_ARCHITECTURE_SPEC.md)
- [T002 — Industry P–Q–B: Hybrid Classical–Quantum–Biological Computing Architecture](docs/T002_INDUSTRY_PQB_FRAMEWORK.md)
- [T003 — Digital Water-Treatment Filter Testbed & P–Q–B Benchmark Spec](docs/T003_WATER_FILTER_PQB_BENCHMARK_SPEC.md) · [Living Task Tracker](docs/T003_TASKS.md)
- See [AGENTS.md](AGENTS.md) for engineering discipline, BCEL rules, and safety invariants.
