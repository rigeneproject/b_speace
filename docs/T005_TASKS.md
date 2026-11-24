# T005 — Task Registry: Multi-Substrate Continuity Transfer Lab (`b_speace` → `q_speace`)

Living engineering task sequence for the **T005 Transfer Lab** ([`T005_CONTINUITY_TRANSFER_LAB_SPEC.md`](T005_CONTINUITY_TRANSFER_LAB_SPEC.md)).
Every task explicitly tracks its **target publication artifact** and its **downstream
transfer value** for `q_speace` and `b_speace`.

Legend: `[x]` Done · `[-]` In Progress · `[ ]` Planned

---

## Phase A — Scientific & Engineering Documentation Publication on GitHub

Ordered sequence to prepare, validate, and publish the scientific documents derived from
the initial study (`docs/Project_1/`) cleanly on GitHub:

| Order | Task ID | Status | Task Description | Output / Deliverable |
|---:|---|---|---|---|
| 1 | `T005-DOC-01` | `[x]` | Create the Transfer Lab engineering charter & task registry renumbering `T003` → `T005` to avoid collision with Water-Filter Benchmark (`T003`) | `docs/T005_CONTINUITY_TRANSFER_LAB_SPEC.md`, `docs/T005_TASKS.md` (`1760c29`, Issue `#1`) |
| 2 | `T005-DOC-02` | `[x]` | Publish sanitized & renumbered Scientific Foundations document (**T005-A**): adapt `T003A_FONDAMENTI_SCIENTIFICI.md` with explicit indirect-transfer framing, verified bibliography (11 primary references), and `q_speace` Transfer Matrix | `docs/T005A_FUNCTIONAL_CONTINUITY_FOUNDATIONS.md` (Issue `#2`) |
| 3 | `T005-DOC-03` | `[x]` | Publish sanitized & renumbered Experimental Protocol & Implementation Spec (**T005-B**): adapt `T003B_SPECIFICA_SPERIMENTALE.md` replacing references to the missing private patch with clean `b_speace/continuity/` contracts, `M1`–`M3` milestones, and anti-abstention metrics | `docs/T005B_EXPERIMENTAL_PROTOCOL_SPEC.md` (Issue `#3`) |
| 4 | `T005-DOC-04` | `[x]` | Record `T005` BCEL classifications in `b_speace/bcel/catalog.py` (functional: replicated state machine, epoch fencing, fair EMA control, analytical dequantization check, anti-abstention metric; accidental: subjective consciousness continuity / mind-copying) | `b_speace/bcel/catalog.py` + `tests/test_bcel.py` (Issue `#4`) |
| 5 | `T005-DOC-05` | `[ ]` | Update `README.md` and GitHub Wiki (`rigeneproject/b_speace/wiki`) with a dedicated **T005 Transfer Lab** section linking `T005`, `T005A`, `T005B`, and the GitHub Project board | `README.md` + GitHub Wiki page `T005-Continuity-Transfer-Lab` |
| 6 | `T005-DOC-06` | `[ ]` | Clean up / archive local private staging folder (`docs/Project_1/` kept untracked or removed after `T005A`/`T005B` are committed) so no duplicate `T003` draft files pollute `main` | Clean `git status` on `main` |

---

## Phase B — Experimental Implementation Milestones (`b_speace/continuity/`)

| Order | Task ID | Status | Milestone & Scope | Primary Hypothesis |
|---:|---|---|---|---|
| 7 | `T005-IMP-01` | `[ ]` | **M0 · Core Continuity Contracts**: implement `b_speace/continuity/{types,protocols,engine}.py` (`Observation`, `CommittedFrame`, `ReplicaState`, `Grant`, `Command`, idempotent destination deduplication, `bspace continuity run`) | Baseline regression |
| 8 | `T005-IMP-02` | `[ ]` | **M1 · Fault Injection & Oracles (`H1`/`H2`/`H4`)**: 50-case deterministic warm/cold matrix (`f ∈ {1,2,7,8,17}`, `r ∈ {1,2,3,4,8}`), stale-epoch/duplicate/out-of-order/all-disconnected drills, independent prefix oracle, and 1-qubit vs. `cos^2[pi(x-p)/2]` grid check (`<= 1e-12`) | `H1`, `H2`, `H4` |
| 9 | `T005-IMP-03` | `[ ]` | **M2 · Fair Bio-Inspired vs. EMA Benchmark (`H3`)**: 160-tick PCG64 latent-bit generator, disjoint splits (`0–63` fit, `100–131` select, `1000–1127` held-out), L2 logistic decoder, 3-point grid for EMA & FHN, 10,000-resample paired bootstrap (`seed=20261124`) | `H3` |
| 10 | `T005-IMP-04` | `[ ]` | **M2b · Combined Fault + Anti-Abstention Evaluation**: run `H3` traces with tick-64 fault (`r=2`), reporting executed-command accuracy AND evaluable-tick accuracy (missed actions = failures) + campaign bundle (`manifest.json`, `trials.jsonl`, `trace.jsonl`, `summary.json`) | `H2 + H3` |
| 11 | `T005-IMP-05` | `[ ]` | **M3 · Multi-Process Latency & Failover Harness**: separate OS coordinator/replica processes using host monotonic clock, fault injector, median/p95 recovery latency, gap & recovery-fraction reporting | `H1`, `H2` (real timing) |
| 12 | `T005-IMP-06` | `[ ]` | **Quality Gates & Reproducible Evidence**: full `pytest`, `ruff`, `black`, `mypy`, `compileall` pass + save reproducible campaign summary in `artifacts/T005_continuity_eval/` | CI Green |

---

## Phase C — Technology Transfer to `q_speace` & `b_speace`

| Order | Task ID | Status | Primitive to Transfer | Destination Repo / Module | Gate |
|---:|---|---|---|---|---|
| 13 | `T005-XFER-01` | `[ ]` | Warm/cold replay budget & out-of-order gap cursor model | `q_speace/singularity/micro_node.py` & `federation_benchmark.py` (`T238`/`T239`) | `H1` verified |
| 14 | `T005-XFER-02` | `[ ]` | Destination idempotency & incompatible-tick-ID rejection contract | `q_speace/bridge/protocol.py` (`T245`) & `q_speace/ptaa/` | `H2` zero violations |
| 15 | `T005-XFER-03` | `[ ]` | Fair temporal-memory (`EMA`) control + paired bootstrap evaluation harness | `q_speace/experiments/context_decay.py` (`T228`/`T229`) & `q_speace/vertical_slice/` | `H3` evaluated (even if null) |
| 16 | `T005-XFER-04` | `[ ]` | Analytical dequantization check (`<= 1e-12` gate + classical sufficiency flag) | `b_speace/interop/adapters.py` & `q_speace/self_improvement_cortex/quantum_engine.py` | `H4` verified |
| 17 | `T005-XFER-05` | `[ ]` | Anti-abstention coverage-weighted accuracy metric & standard `manifest/trials/trace/summary` bundle | `q_speace/vertical_slice/evaluator.py` (`T244`) & `b_speace/benchmarks/water_filter/` (`T003`) | `M2b` verified |

---

## Phase D — Deferred / Optional Separate Protocol (Non-Blocking)

| Task ID | Status | Description |
|---|---|---|
| `T005-DEF-01` | `[ ]` | Offline replay compatibility adapter for public PhysioNet EEG Motor Movement/Imagery dataset (optional extra; decoding test only, no persistence claim) |
| `T005-DEF-02` | `[ ]` | Separate ethics-reviewed VR telepresence protocol (`H5`: VEQ, real vs. sham switches, motion-to-photon latency) — only after `M1`–`M3` complete |
