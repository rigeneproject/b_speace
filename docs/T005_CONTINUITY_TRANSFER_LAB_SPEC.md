# T005 — Multi-Substrate Functional Continuity Transfer Lab (`b_speace` → `q_speace`)

- **Status**: Active Research Charter (v0.1.0)
- **Renumbering Note**: Supersedes draft ID `T003` from local archive `docs/Project_1/`
  to avoid collision with `T003` (Digital Water-Treatment Filter Benchmark) and `T004`
  (Biomolecular Backlog).
- **Parent Paradigm**: [T002 — Industry P–Q–B](T002_INDUSTRY_PQB_FRAMEWORK.md)
- **Living Task Tracker**: [`docs/T005_TASKS.md`](T005_TASKS.md)

---

## 1. Mission: Indirect Brainstorming & Technology Transfer Lab

**T005** is intentionally structured as an **experimental brainstorming and engineering
transfer lab** inside `b_speace`. Rather than pursuing speculative or non-observable
objectives (such as mind-copying or subjective consciousness transfer), T005 uses the
demanding distributed-systems and signal-processing subproblems inspired by
*multi-substrate functional continuity* as a stress-test generator to discover, falsify,
and promote reusable software primitives into **`q_speace`** and **`b_speace`**.

### Operational Principles
1. **Indirect Value First**: Every milestone (`M0`–`M3`) MUST map to at least one
   concrete beneficiary module in `q_speace` or `b_speace`.
2. **Strict BCEL & `AGENTS.md` Perimeter**:
   - **Functional (in scope)**: deterministic state-machine replication, append-only
     event framing, epoch fencing, idempotent destination deduplication, bio-inspired
     dynamical feature filtering vs. classical memory baselines, analytical quantum
     dequantization checks, and anti-abstention evaluation metrics.
   - **Accidental / Out of scope**: any claim of biological or quantum consciousness,
     sentience, personal subjective persistence across substrates, or physical actuator
     command execution.
3. **Null Results Are First-Class Outputs**: A negative or null result (e.g., proving
   that FitzHugh–Nagumo does not beat a fair EMA baseline, or that a 1-qubit embedding
   reduces exactly to a classical trigonometric formula) is archived as a verified
   engineering finding rather than discarded.

---

## 2. Four-Level Taxonomy & Scope Boundary

| Level | Operational Definition | Scope in `T005` |
|---|---|---|
| **Informational Continuity** | Independent replicas reconstruct identical task state from the same event prefix. | **In scope (`M1`, `H1`/`H2`)** |
| **Operational Continuity** | At most one valid authority issues an accepted command per deadline; stale epochs and duplicate actions are rejected. | **In scope (`M1`/`M3`, `H1`/`H2`)** |
| **Perceived Continuity** | Living human operator evaluates multi-agent virtual control and interface-switch detectability under ethical VR protocol. | **Deferred separate protocol (`H5`, non-blocking)** |
| **Subjective Persistence Beyond Biological Loss** | First-person personal identity continuation after biological failure. | **Out of scope / Non-observable** (excluded from runtime claims per `AGENTS.md` §2) |

---

## 3. Hypotheses & Technology Transfer Matrix (`T005` → `q_speace` / `b_speace`)

| Hypothesis | Decisive Engineering Test | Promotion / Rejection Rule | Target Modules in `q_speace` / `b_speace` |
|---|---|---|---|
| **`H1` · Warm vs. Cold Recovery** | Compare missed deadlines and background pre-alignment work across fault tick `f ∈ {1,2,7,8,17}` and replay budget `r ∈ {1,2,3,4,8}` against closed-form analytical catch-up oracle `max(0, f - j(r-1))`. | Exact deterministic match with analytical oracle; characterize break-even between warm standby cost and blackout window. | `q_speace/singularity/micro_node.py` (`T239`), `q_speace/singularity/federation_benchmark.py` (`T238`) |
| **`H2` · Authority & State Integrity** | Inject stale epochs (including re-assignment to same replica ID), duplicate commands, lost acknowledgements, out-of-order frames, and lagging replicas. | **Zero** stale-epoch acceptances, **zero** duplicate side-effects, context drift `<= 1e-12` vs. independent prefix oracle. | `q_speace/bridge/protocol.py` (`T245` fencing & WAL), `q_speace/ptaa/delegation.py` |
| **`H3` · Fair Bio-Inspired (`B`) Contribution** | Compare `P+B` (FitzHugh–Nagumo) vs. `P + Classical EMA` on independent latent-bit task (160-tick episodes, disjoint splits: seeds `0–63` fit, `100–131` select, `1000–1127` held-out; 3-point grid each; L2 logistic decoder; 10,000-resample paired bootstrap, seed `20261124`). | Promote `B` feature claim **only if** lower 95% bootstrap CI of `(B - EMA)` balanced accuracy `> +0.02`; else archive null result and attribute gains to generic temporal memory. | `q_speace/experiments/context_decay.py` (`T228`/`T229`), `q_speace/spiking/`, `b_speace/bioelectric/` |
| **`H4` · Quantum (`Q`) Analytical Equivalence** | Evaluate 1-qubit state fidelity vs. closed-form `cos^2[pi*(x - p)/2]` on full `[0, 1] x [0, 1]` grid (step `0.01`), plus exact/near ties and backend-unavailable fallback. | Max absolute error `<= 1e-12` validates kernel numerics and explicitly documents when classical evaluation is sufficient (dequantization gate). | `b_speace/interop/adapters.py`, `q_speace/quantum/`, `q_speace/self_improvement_cortex/quantum_engine.py` |
| **`H2+H3` · Anti-Abstention Combined Metric** | Run `H3` traces with fault at tick 64 (`r = 2`), reporting **both** accuracy on executed commands and fraction of evaluable ticks with correct action (missed actions count as failures). | Prevents fail-closed controllers from inflating apparent accuracy via abstention. | `q_speace/vertical_slice/evaluator.py` (`T231`/`T244`), `b_speace/benchmarks/water_filter/` (`T003`) |

---

## 4. Core Software Contracts (Target Module: `b_speace/continuity/`)

All endpoints remain strictly virtual (no hardware actuation):

- **`Observation`**: `(session_id, source_id, local_seq, acquired_tick, delivered_tick, value, valid)` — distinguishes acquisition clock from arrival clock; finite checks enforced fail-closed.
- **`CommittedFrame`**: append-only ordered frame `(session_id, frame_index, present_channels_mask, observations, schema_version)` — late arrivals never retroactively rewrite committed decisions.
- **`ReplicaState`**: `(replica_id, next_frame_cursor, context, synthetic_goal, last_confirmed_action)` — out-of-order frames hold cursor at first gap until prefix replay completes.
- **`Grant` / `Command`**: `(session_id, epoch, holder_id, tick, action_id, targets)` — destination deduplication enforces idempotency on retry and rejects conflicting `action_id` on the same tick.
- **`RunRecord` & Standard Campaign Bundle**:
  - `manifest.json` (schema, git SHA, config/data SHA-256, Python/NumPy versions, PCG64 seeds)
  - `trials.jsonl` (per-run metrics, first recovery tick, missed deadlines, violations, censorship reasons)
  - `trace.jsonl` (causal link: observation → cursor → epoch → election → decision → confirmation)
  - `summary.json` (paired contrasts, bootstrap CIs, denominators, explicit null-result reporting)

---

## 5. Publication & Governance Workflow

1. Scientific source documents (`T005A` Foundations, `T005B` Experimental Protocol) are
   sanitized, renumbered (`T003` → `T005`), enriched with the `q_speace` Transfer Matrix,
   and published as versioned Markdown in `b_speace/docs/` (never exposing private
   unreviewed drafts).
2. Execution and transfer decisions are tracked transparently on the GitHub Project
   board at `https://github.com/users/rigeneproject/projects` linked to Issues in
   `rigeneproject/b_speace` (and downstream transfer Issues/PRs in `rigeneproject/q_speace`).
