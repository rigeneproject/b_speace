# T003 — Living Engineering Task Registry & Roadmap (`b_speace`)

This living document tracks all engineering tasks for the **Water-Treatment Filter P–Q–B
Benchmark** (`T003`) and subsequent `b_speace` developments. Update task status,
verification evidence, and measured benchmark outcomes on every milestone.

Legend: `[x]` Done · `[-]` In Progress · `[ ]` Planned / Backlog

---

## Phase 0 — Foundation & Framework Alignment (Completed)

| ID | Task | Status | Deliverable / Evidence |
|---|---|---|---|
| `T001-01` | Bootstrap `b_speace` package (`bioelectric`, `organoid`, `interop`, `bcel`, `orchestrator`, `cli`) | `[x]` | Commit `25eff33`, 17 tests, 90.5% cov |
| `T002-01` | Publish Industry P–Q–B framework specification & GitHub Wiki docs | `[x]` | `docs/T002_INDUSTRY_PQB_FRAMEWORK.md`, commit `08fc182` |
| `T003-00` | Analyze `docs/fonti scientifiche.txt` & create T003 spec + living task tracker | `[x]` | `docs/T003_WATER_FILTER_PQB_BENCHMARK_SPEC.md`, `docs/T003_TASKS.md` |

---

## Phase 1 — Experiment 1: `P` vs `P + B` Closed-Loop Water-Filter Testbed (Completed)

| ID | Task | Status | Deliverable / Evidence |
|---|---|---|---|
| `T003-01` | Update BCEL catalog with cell-free Hill transduction, Thomas breakthrough, Simplex fallback & exclusion of speculative quantum-bio claims | `[x]` | `b_speace/bcel/catalog.py` |
| `T003-02` | Implement `b_speace.biomolecular` Protocols & Adapters (ROSALIND-inspired allosteric Hill cell-free threshold biosensor with lag/noise/drift + simulated reference assay) | `[x]` | `b_speace/biomolecular/{types,protocols,adapters}.py`, `tests/test_biomolecular.py` |
| `T003-03` | Implement hidden-state `WaterFilterTwin` (Thomas / Bohart–Adams breakthrough normalized by treated volume $V = Q \cdot t$, kinetic vs. capacity material archetypes) | `[x]` | `b_speace/benchmarks/water_filter/model.py` |
| `T003-04` | Implement classical controller `P` (`P_ONLY` and `P_PLUS_B`), causal `DecisionRecord` trace, equal-volume comparison, and Simplex fail-closed `B` drift monitor | `[x]` | `b_speace/benchmarks/water_filter/controller.py` |
| `T003-05` | Implement reproducible paired benchmark runner (`P` vs `P+B`), fixed vs. marginal cost & energy accounting, and parametric sweep over `(delay_B, noise_B, drift_B)` | `[x]` | `b_speace/benchmarks/water_filter/runner.py` |

---

## Phase 2 — Experiment 2: Adding `Q` (Full 4-Way Ablation `P`, `P+B`, `P+Q`, `P+Q+B`) (Completed)

| ID | Task | Status | Deliverable / Evidence |
|---|---|---|---|
| `T003-06` | Define `CandidateRanker` Protocol + `ClassicalBaselineRanker` + `QuantumInteractionRanker` (using `b_speace.interop.QuantumKernelPort`, `Sevo` gate & Simplex uncertainty fallback $\sigma_Q \le \sigma_{\max}$) | `[x]` | `b_speace/benchmarks/water_filter/rankers.py` |
| `T003-07` | Extend runner & CLI (`bspace benchmark water-filter`) to run full 4-way ablation (`P`, `P+B`, `P+Q`, `P+Q+B`), multi-seed aggregation, and parametric convenience map | `[x]` | `b_speace/cli.py`, `b_speace/benchmarks/water_filter/runner.py` |
| `T003-08` | Add comprehensive test suite (anti-leakage, determinism, equal-volume invariant, Simplex fallback drills, 4-way ablation, live `q_speace` interop) & pass all CI gates | `[x]` | `tests/test_biomolecular.py`, `tests/test_water_filter_benchmark.py` — 26 passed, 91.5% cov, `ruff`/`black`/`mypy` clean |
| `T003-09` | Record reproducible baseline experiment evidence (JSON + summary table in this tracker) | `[x]` | `artifacts/T003_water_filter_baseline.json` |

---

## Phase 3 — Future `b_speace` Developments (Backlog)

| ID | Task | Status | Rationale / Source |
|---|---|---|---|
| `T004-01` | Multi-contaminant competitive adsorption & cross-reactive biosensor array | `[ ]` | Real water matrices contain competing ions & co-contaminants (`fonti scientifiche.txt` §1) |
| `T004-02` | Active-learning / Bayesian aTF calibration loop for cell-free biosensor drift compensation | `[ ]` | ML-guided aTF engineering & Bayesian hybrid UQ (`fonti scientifiche.txt` §1, §5) |
| `T004-03` | Ingest public ROSALIND / ICP-MS experimental calibration datasets (offline replay adapter) | `[ ]` | Replace purely synthetic Hill parameters with published wet-lab calibration curves |
| `T004-04` | VQE / Hamiltonian binding-energy adapter hook for MOF/sorbent candidates via `q_speace` Qiskit/Aer backend | `[ ]` | Align with Barroca et al. (2024) DAC/MOF binding energy workflows (`fonti scientifiche.txt` §2) |
| `T004-05` | Microfluidic / MEA hardware-in-the-loop transport adapter (gRPC/HTTP) behind `OrganoidInterface` & `BiomolecularSensor` | `[ ]` | Safe laboratory integration after confined twin validation |

---

## Measured Experiment Evidence Log (`T003-09`, 2026-11-24)

Source artifact: [`artifacts/T003_water_filter_baseline.json`](../artifacts/T003_water_filter_baseline.json)
Seeds: `(11, 22, 33, 44, 55)` · Live `q_speace` hybrid kernel enabled · Equal target volume $V_{\text{target}} = 100\text{ L}$ ($Q_{\text{high}} = 2.0\text{ L/min}$, $Q_{\text{low}} = 0.8\text{ L/min}$).

| Mode | Time to Confirm (min) | Trials Started | Early Stops | Treated Vol (L) | Ref Assays | B Assays | Wrong Rate | High-Flow Hit | Marginal Cost (USD) | Fixed Setup (USD) | Energy (Wh) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`P`** | `562.5` | `6.0` | `2.0` | `550.0` | `10.0` | `0.0` | `0.0%` | `0.0%` | `$570.00` | `$0.00` | `582.50` |
| **`P+B`** | `376.5` | `6.0` | `5.0` | `348.0` | `4.0` | `33.8` | `0.0%` | `0.0%` | `$350.70` | `$800.00` | `364.57` |
| **`P+Q`** | `105.0` | `1.0` | `0.0` | `100.0` | `2.0` | `0.0` | `0.0%` | `100.0%` | `$185.00` | `$2500.00` | `94.94` |
| **`P+Q+B`** | `105.0` | `1.0` | `0.0` | `100.0` | `2.0` | `10.0` | `0.0%` | `100.0%` | `$200.00` | `$3300.00` | `94.96` |

### Key Analytical Takeaways
1. **Experiment 1 (`P` vs `P+B`)**: With an **identical** number of started trials (`6.0`), early breakthrough alerts from `B` cut wall-clock time by **33.1%** (`562.5` → `376.5 min`), treated volume by **36.7%** (`550` → `348 L`), reference assays by **60%** (`10` → `4`), marginal cost by **38.5%** (`$570.00` → `$350.70`), and energy by **37.4%** (`582.5` → `364.6 Wh`) at **0% wrong-selection rate**. Fixed setup (`$800`) breaks even after ~4 material campaigns.
2. **Experiment 2 (`+Q` 4-way ablation)**: When `Q` surfaces a genuinely high-affinity, fast-kinetics candidate (`mat_optimal_e`) on trial #1, `P+Q` reduces physical trials from `6.0` → `1.0` (`105.0 min`) and hits high-flow compliance (`100%`). In this specific best-case scenario, adding `B` (`P+Q+B`) adds `$15.00` marginal biosensor cost and `$800` setup cost without further reducing trial time — demonstrating honestly that `B`'s marginal synergy over `P+Q` emerges specifically when `Q`'s top-ranked candidate suffers macroscopic kinetic/contact-time failure or matrix interference.
3. **Parametric `B` Sweep**: Across all 18 tested points (`delay ∈ {2, 5, 15} min`, `noise ∈ {0.02, 0.08, 0.22}`, `drift ∈ {0.0, 0.004}/min`), `P+B` saved time over `P` without degrading selection accuracy, while extreme drift is caught fail-closed by the Simplex `FALLBACK_DISABLE_B` monitor (verified in unit drill).
