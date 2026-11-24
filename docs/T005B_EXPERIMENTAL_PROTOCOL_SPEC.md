# T005-B — Experimental Protocol & Implementation Specification (`b_speace/continuity/`)

- **Document ID**: `B-SPEACE / T005-B` (v1.0, 2026-11-24)
- **Charter**: [T005 — Multi-Substrate Functional Continuity Transfer Lab](T005_CONTINUITY_TRANSFER_LAB_SPEC.md)
- **Scientific Foundations**: [T005-A](T005A_FUNCTIONAL_CONTINUITY_FOUNDATIONS.md)
- **Living Task Registry**: [T005_TASKS.md](T005_TASKS.md)

---

## 1. Mandate, Component Status & Integration Constraints

**Implementation Objective**: Build the modular package `b_speace/continuity/` (CPU-only,
Python + NumPy, reusing `b_speace.bioelectric.FitzHughNagumoAdapter` and
`b_speace.interop` where appropriate) to execute reproducible verification of task
recovery (`H1`), authority/state integrity (`H2`), fair bio-inspired vs. classical
temporal-memory utility (`H3`), and analytical quantum equivalence (`H4`), feeding
validated primitives into `q_speace` (`T005-XFER-01..05`).

| Status | Component | Planned Role |
|---|---|---|
| Present on `main` | `b_speace.bioelectric.FitzHughNagumoAdapter`, `b_speace.interop`, `b_speace.bcel.BCELCatalog` | Reuse excitable dynamics, quantum interop port, and BCEL governance without modifying organoid safety envelopes or stimulation interlocks. |
| Increment `M0` (`T005-IMP-01`) | `b_speace/continuity/{types,protocols,engine}.py` + CLI `bspace continuity run` | Core virtual state-machine replication, epoch grants, destination deduplication, and deterministic baseline regression. |
| Increment `M1` (`T005-IMP-02`) | `b_speace/continuity/campaign.py` + `bspace continuity evaluate --config FILE --output DIR` | Versioned input manifests, fault injection, independent prefix state oracle, rejection reason logs, and `H1`/`H2`/`H4` suites. |
| Increment `M2` (`T005-IMP-03..04`) | `b_speace/continuity/h3_benchmark.py` | Independently labeled latent-bit generator, fair classical EMA temporal control, paired bootstrap (`H3`), combined fault anti-abstention metric (`M2b`), and cost accounting. |
| Increment `M3` (`T005-IMP-05`) | `b_speace/continuity/multiprocess.py` | Separate OS coordinator & virtual replica processes using host monotonic clock, IPC fault injection, and real recovery latency distributions. |

**BCEL & Safety Perimeter**:
- Functional in runtime: state reconstruction, prefix synchronization, epoch authority
  transfer, destination idempotency, and signal transformations.
- Prohibited in runtime: subjective continuity claims, consciousness assertions, and
  physical actuator commands (all endpoints remain virtual).

---

## 2. Core Contracts & Tick Transitions

| Contract | Minimum Fields & Semantics |
|---|---|
| `Observation` | `session_id`, `source_id`, `local_seq`, `acquired_tick`, `delivered_tick`, `value`, `valid`. Finite values enforced fail-closed; acquisition and delivery clocks have distinct roles. |
| `CommittedFrame` | `session_id`, `frame_index` (contiguous), `present_channels_mask`, `observations`, `schema_version`. Append-only; late arrivals never mutate an already committed frame. |
| `ReplicaState` | `replica_id`, `next_frame_cursor`, `context`, `synthetic_goal`, `last_confirmed_action`. In campaign mode, goal and confirmations must derive strictly from committed log events. |
| `Grant` / `Command` | `session_id`, `epoch`, `holder_id`, `tick`, `action_id`, `targets`. At most one logical command per tick (may address multiple virtual targets). |
| `RunRecord` | `input_hash`, `seed`, `mode`, `fault_spec`, `backend`, `versions`, `events`, `decisions`, `rejections`, `metrics`, `final_state`. Ground-truth task labels remain strictly outside controller inputs. |

### Per-Tick Execution Sequence
1. Apply scheduled fault injection and, if primary fails, revoke current holder by
   incrementing `epoch`.
2. Deliver due observations, deduplicate by `(session_id, source_id, local_seq)`, and
   commit the next contiguous `CommittedFrame`.
3. Each reachable replica consumes frames in strict index order up to its per-tick
   replay budget `r`.
4. If no active holder exists, admit only available replicas with complete committed
   prefix and verified state.
5. Elect the top eligible replica, emit at most one `Command`, and record the
   destination endpoint's acceptance or motivated rejection.

### Incomplete Inputs & Out-of-Order Delivery
- When link faults deliver a future frame out of order, the replica buffers it and
  holds `next_frame_cursor` at the first missing gap until prefix replay fills it (no
  double updates).
- Under source-channel dropout, missing channels are recorded in `present_channels_mask`
  and every arm applies the identical policy: average across available channels, or
  hold previous context if all channels are absent, tagged with a quality flag.
  Retroactive rewriting of past decisions is forbidden.

### Destination Authority & Idempotency
- Stale epochs are rejected even if messages arrive in order, including after
  re-assignment to the same `replica_id`.
- The destination endpoint tracks deduplication per `(session_id, tick)`: retrying the
  same `action_id` returns the original confirmation without repeating side-effects; a
  conflicting `action_id` on the same tick is rejected with a logged reason.
- Rejection/acceptance logging, virtual effect, and confirmation form one atomic
  transition in the simulator. Lost confirmations retransmit without re-executing.

### Independent Prefix Oracle
Recomputes expected state directly from the source prefix without calling
`Replica.replay`: baseline context starts at `0.5` and updates via
`context_t = 0.5 * (context_{t-1} + agg_obs_t)`. Verifies goals and confirmations
against actually accepted destination effects.

---

## 3. Experiment 1 — Fault Recovery, Integrity & `Q` Equivalence (`H1`, `H2`, `H4`)

### Deterministic Regression Matrix (`H1`)
- Duration `T = 24` ticks, `seed = 42`.
- Cross fault tick `f in {1, 2, 7, 8, 17}` with per-replica replay budget
  `r in {1, 2, 3, 4, 8}` and `warm` vs. `cold` standby across all four modes
  (`P`, `P+Q`, `P+B`, `P+Q+B`) — 50 deterministic combinations per mode family, holding
  committed frames identical across each warm/cold pair, plus a fault-free reference.
- **Closed-Form Availability Oracle**: With 1 frame/tick, fault occurring before frame
  `f`, cold backlog `f`, and election permitted after same-tick replay:
  - At post-fault tick `j >= 1`, cold backlog equals `max(0, f - j * (r - 1))`.
  - Missed cold actions equal `min(T - f, ceil(f / (r - 1)) - 1)` for `r > 1`, and
    `T - f` for `r = 1`.
  - Missed warm actions equal `0` under zero-delay links (with explicit pre-alignment
    update count reported).

### Mandatory Fault-Injection Drills (`H2`)

| Fault Case | Required Verification |
|---|---|
| Late command with stale epoch (other fields valid) | Motivated epoch rejection, including after re-election of the same `replica_id`. |
| Duplicate command or lost confirmation | Exactly one virtual effect applied; trace links retry to original confirmation. |
| Out-of-order frame, replica pause & rejoin | Cursor halts at first missing index; rejoins after prefix replay with zero double updates. |
| Profile-favored replica lagging; all replicas disconnected | Lagging replica stays excluded until caught up; total blackout logs missed recovery within horizon. |
| `Q` backend unavailable, non-finite score, exact tie | Classical fallback on valid input when `Q` is unavailable; non-finite input rejected & logged; ties within 12 decimals broken lexicographically by replica name. |

### Analytical Quantum Equivalence Check (`H4`)
- Construct full Cartesian grid `(x, p) in [0, 1] x [0, 1]` at step `0.01`.
- Compare single-qubit state-vector fidelity against exact `cos^2[pi * (x - p) / 2]`.
- Pass criterion: maximum absolute error `<= 1e-12`, plus exact-tie and near-tie
  triples preserving identical winners between `Q` and classical formula.

### Pass Criteria (`M1`)
Exact match against deterministic availability counts, **zero** authority violations or
duplicate effects, context error `<= 1e-12` on comparable ticks, and actions equivalent
to the independent oracle.

---

## 4. Experiment 2 — Fair Bio-Inspired Utility & Anti-Abstention (`H3`, `M2`)

### Independently Labeled Task Generator
- Episode length: `160` ticks (exclude first `10` warm-up ticks from scoring).
- Latent binary state `z_t in {0, 1}` initialized uniformly (`p = 0.5`), flipping each
  tick with probability `0.06`.
- Digital channel observation: `clip(z_t + N(0, 0.55^2), 0, 1)`.
- Robotic channel observation: `clip(z_{t-2} + N(0, 0.35^2), 0, 1)` (using `z_0` for
  ticks `0` and `1`).
- Bio-inspired channel `B`: receives **only** the digital channel and transforms it via
  `FitzHughNagumoAdapter`. Ground-truth label is `z_t`. Reset all states per episode.

### Fair Arms Comparison

| Arm | Features & Model | Role |
|---|---|---|
| **`P`** | `[digital, robotic]` → L2 logistic decoder (`threshold = 0.5`) | Static classical baseline |
| **`P + Classical EMA`** | `[digital, robotic, EMA(digital)]` → identical L2 logistic decoder | **Primary fair control for `H3`** |
| **`P + B (FHN)`** | `[digital, robotic, normalized FHN(digital)]` → identical L2 logistic decoder | Bio-inspired candidate (same feature count & grid budget) |
| **`Q` on/off** | Profile selector downstream of state estimate | Verify winner preservation across `Q` vs. analytical classical |

### Strict Data Hygiene & Statistical Test
- RNG: `numpy.random.PCG64` with independent substreams for state, noise, and faults.
- Disjoint seed partitions: **fit** `0–63`, **hyperparameter selection** `100–131`,
  **held-out final evaluation** `1000–1127`.
- Equal 3-point selection grid: EMA decay `alpha in {0.2, 0.5, 0.8}`; FHN input gain
  `g in {10.0, 20.0, 30.0}` (selected by balanced accuracy on `100–131`; first grid
  value breaks ties).
- Standardize features using **fit-split statistics only**. Logistic regression with
  mean log-loss, L2 penalty `0.01` on weights (unpenalized intercept), converged to
  gradient norm `<= 1e-8`. Freeze weights, hashes, and config before touching `1000–1127`.
- **Primary metric & contrast**: per-episode balanced accuracy on fault-free held-out
  episodes (episodes missing a class flagged non-evaluable and counted). Paired contrast
  `delta = BalAcc(P+B) - BalAcc(P+EMA)` across matched seeds; 95% percentile CI via
  `10,000` whole-episode bootstrap resamples (`seed = 20261124`).
- **Promotion rule**: pursue `B` specificity only if lower 95% CI bound `> +0.02`
  absolute; otherwise publish point estimate, CI, and null conclusion explicitly.

### Combined Fault & Anti-Abstention Evaluation (`M2b`)
Repeat on identical held-out traces with primary fault at tick `64` and replay budget
`r = 2`. Report **both**:
1. Accuracy on executed commands;
2. Fraction of all evaluable ticks with a correct accepted action (counting missed
   actions as failures to prevent gaming via abstention).

Track CPU wall time, background replica updates, and memory separately; report energy
in Joules only when measured with documented instrumentation.

---

## 5. Campaign Evidence Bundle & Milestones

Every `bspace continuity evaluate` run writes a deterministic directory:
- `manifest.json`: schema version, git SHA, SHA-256 of config & data, Python/NumPy
  versions, PCG64 seed partitions, replay budgets, clock type.
- `trials.jsonl`: one JSON line per run (`run_id`, arm, first recovery tick or `null`,
  missed actions, backlog, violations, cost, censorship reason).
- `trace.jsonl`: causal record linking observation → cursor → epoch → election →
  decision → destination confirmation.
- `summary.json`: denominators, paired contrasts, bootstrap CIs, and explicit null
  outcomes.

### Milestones & Downstream `q_speace` Transfer Gates
- **`M0` · Baseline Contracts**: deterministic `continuity run` + regression tests.
- **`M1` · Correctness (`H1`/`H2`/`H4`)**: feeds `T005-XFER-01` (`q_speace/singularity`),
  `T005-XFER-02` (`q_speace/bridge`), and `T005-XFER-04` (`b_speace/interop` / `q_speace/quantum`).
- **`M2` · Functional Validity (`H3` + `M2b`)**: feeds `T005-XFER-03`
  (`q_speace/experiments/context_decay.py`) and `T005-XFER-05` (`q_speace/vertical_slice`).
- **`M3` · Separate Processes**: host monotonic clock latency (detection, election,
  application; median & p95 recovery latency + recovery fraction). Consensus modeling
  is added only if coordinator failure is explicitly studied.
- **Deferred (`H5` VR Protocol)**: strictly separate ethics-reviewed protocol; closed-loop
  virtual-cursor scene feedback verified before any human-subject session.
