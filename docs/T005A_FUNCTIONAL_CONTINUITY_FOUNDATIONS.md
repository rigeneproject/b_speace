# T005-A — Multi-Substrate Functional Continuity: Scientific & Engineering Foundations

- **Document ID**: `B-SPEACE / T005-A` (v1.0, 2026-11-24)
- **Charter**: [T005 — Multi-Substrate Functional Continuity Transfer Lab](T005_CONTINUITY_TRANSFER_LAB_SPEC.md)
- **Companion Spec**: [T005-B — Experimental Protocol & Implementation Spec](T005B_EXPERIMENTAL_PROTOCOL_SPEC.md)
- **Living Task Registry**: [T005_TASKS.md](T005_TASKS.md)

---

## 1. Indirect Research Mandate & Technology Transfer to `q_speace` / `b_speace`

This document establishes the scientific and engineering foundations for **T005**, an
experimental brainstorming and stress-testing lab inside `b_speace`. Its explicit
engineering purpose is **indirect technology transfer**: extracting rigorously verified
software primitives (state-machine replication, epoch fencing, fair bio-inspired vs.
classical temporal baselines, analytical quantum dequantization gates, and
anti-abstention metrics) and transferring them into **`q_speace`** and **`b_speace`**.

### Transfer Matrix Overview

| T005 Hypothesis | Engineering Primitive Extracted | Target Module(s) |
|---|---|---|
| **`H1` · Warm vs. Cold Recovery** | Closed-form catch-up replay oracle & warm-standby cost accounting | `q_speace/singularity/micro_node.py` (`T239`), `federation_benchmark.py` (`T238`) |
| **`H2` · Authority & State Integrity** | Append-only prefix framing, monotonic epoch fencing & idempotent destination deduplication | `q_speace/bridge/protocol.py` (`T245`), `q_speace/ptaa/delegation.py` |
| **`H3` · Fair Bio-Inspired (`B`) Contribution** | Information-matched FitzHugh–Nagumo vs. classical EMA control with disjoint splits & paired bootstrap | `q_speace/experiments/context_decay.py` (`T228`/`T229`), `q_speace/spiking/`, `b_speace/bioelectric/` |
| **`H4` · Quantum (`Q`) Analytical Equivalence** | Exact `<= 1e-12` dequantization verification against `cos^2[pi*(x-p)/2]` + classical-sufficiency gate | `b_speace/interop/adapters.py`, `q_speace/self_improvement_cortex/quantum_engine.py` |
| **`H2+H3` · Anti-Abstention Metric** | Joint executed-command accuracy and evaluable-tick coverage (counting missed actions as failures) | `q_speace/vertical_slice/evaluator.py` (`T244`), `b_speace/benchmarks/water_filter/` (`T003`) |

---

## 2. Research Question & Feasibility Boundary

A single supervisory controller can coordinate multiple heterogeneous virtual, robotic,
or bio-inspired extensions. If each extension maintains an up-to-date representation of
the task state, to what extent can the most suitable replica resume control when the
primary controller becomes unavailable?

A separate philosophical question sometimes accompanies this topic—namely whether a
biological subject could experience first-person persistence on an external substrate
after biological failure.

**Feasibility Conclusion (BCEL & `AGENTS.md` §2):**
- It is fully feasible to build a reproducible CPU-based benchmark on **informational**
  and **operational** continuity (`H1`–`H4`).
- A separate ethics-reviewed VR telepresence protocol (`H5`, deferred) can measure what
  a living participant perceives during virtual interface switches.
- For **subjective persistence after biological loss**, neither this program nor the
  reviewed literature provides an observable capable of distinguishing continuation of
  a first-person subject from continuation of external behavior [7]. Accordingly, any
  claim of mind-copying, consciousness, or subjective persistence is strictly excluded
  from `b_speace` runtime semantics and deliverables.

| Level | Operational Definition | Obtainable Evidence | Scope in `T005` |
|---|---|---|---|
| **Informational Continuity** | Independent replicas reconstruct identical task state from the same event prefix. | Comparison against an independent prefix reference oracle (task memory & last applied frame). | **In scope (`M1`, `H1`/`H2`)** |
| **Operational Continuity** | At most one valid authority issues an accepted command per scheduled deadline. | Missed, duplicate, or invalid commands and recovery latency; an authority gap is valid if no eligible replica exists. | **In scope (`M1`/`M3`, `H1`/`H2`)** |
| **Perceived Continuity** | A living participant evaluates control over multiple virtual bodies and switch detectability. | Per-stream task performance, real vs. sham switch detection, VEQ agency/ownership scores [5, 6]. | **Deferred separate protocol (`H5`)** |
| **Subjective Persistence After Biological Loss** | First-person continuity of a subject on another substrate. | Non-observable: distinct subjective histories could produce identical external traces [7]. | **Out of scope / Excluded** |

**Unit of Replication**: In the `T005` software testbed, replicas share structured
synthetic observations, operational context, synthetic task goal, and confirmed action
records. "Single identity" has a strictly operational meaning here: **at most one
authority holder per session epoch**.

---

## 3. Literature Synthesis

Narrative design review (updated 2026-11-24) prioritizing primary studies, measurement
instruments, and foundational distributed-systems references (not a meta-analysis and
not claiming universal perceptual thresholds):

- **Multi-Destination Presence**: Kishore et al. (2016) connected two physical robots
  and a virtual body with switching across destinations, demonstrating practical
  multi-endpoint telepresence [1]. Demonstrating truly simultaneous attention requires
  an additional control: overlapping target events measuring detection in each stream.
- **Body Ownership & Self-Location**: Guterstam et al. (2020) investigated illusions of
  dual full-body ownership under controlled multisensory stimulation, with dual
  self-location findings remaining exploratory and perspective-dependent [2]. Design
  consequence: separately measure ownership, agency, and perceived location [5].
- **Parallel Multi-Agent Control**: Serizawa et al. (2026) compared two visual and three
  tactile presentation methods during parallel control of two agents in a within-subject
  design, reporting stronger dual-body sensation under unified tactile feedback [3]. This
  informs multimodal interface comparisons without generalizing to three bodies or loss
  of a primary substrate.
- **Perception & Latency Measurement**: An unreported switch can reflect tight
  synchronization, task distraction, or low test sensitivity. Valid psychophysical
  protocols require sham switches, clearly detectable positive controls, presentation
  timestamps, external motion-to-photon latency measurement [6], and standardized
  embodiment instruments such as the VEQ [5].
- **Consciousness Indicators & Identity**: Butlin et al. (2025/2026) review indicator
  properties derived from competing neuroscientific theories [7]. Even hypothetical
  future indicator evidence leaves unresolved whether experience belongs to the same
  individual; a synchronized state log provides no discriminating observable.

---

## 4. Roles of `P`, `Q`, and `B` Under Industry P–Q–B

- **`P` · Classical Coordination**: An append-only frame log orders observations. Each
  replica applies identical updates to the same prefix. A coordinator elects an eligible
  up-to-date replica and issues a monotonically increasing mandate number (`epoch`).
  The destination endpoint rejects stale epochs and enforces idempotency per
  `(session, tick, action_id)`. Classic state-machine replication and consensus
  literature [8, 9] govern ordering and fault models; tolerances for coordinator loss
  belong to separate consensus studies (`M3+`).
- **`B` · Bio-Inspired Dynamics (`FitzHugh–Nagumo`)**: The FitzHugh–Nagumo ODE [4]
  models excitable dynamics and refractory recovery in reduced form. Because adding a
  dynamical channel alters both temporal filtering and input weighting, a shift in
  replica choice proves sensitivity—not task improvement. Therefore `T005-B` mandates a
  **fair classical temporal-memory control (EMA)** with identical inputs, identical
  hyperparameter grid budget, and an external ground-truth task (`H3`).
- **`Q` · Profile Matching & Analytical Dequantization Check**: Context `x` and
  candidate profile `p` are encoded as single-qubit real states whose fidelity equals
  `cos^2[pi * (x - p) / 2]` analytically. Following quantum ML benchmarking discipline
  [10], the scientific role of `Q` here is verifying numerical equivalence (`<= 1e-12`)
  and explicitly allowing the benchmark to conclude that classical computation is
  sufficient for separable single-qubit scoring (`H4`).

---

## 5. Verifiable Hypotheses & Investment Sequencing

| Hypothesis | Decisive Test | Decision Rule Changing Engineering |
|---|---|---|
| **`H1` · Recovery** | Measure missed deadlines and background pre-alignment cost for warm vs. cold replicas across `(f, r)` grids against the deterministic catch-up formula. | Discrepancy with analytical oracle flags an ordering/counting bug; realistic latency/cost bounds define operational break-even. |
| **`H2` · Integrity** | Compare reconstructed state and accepted commands against a fault-free prefix oracle under delays, duplicates, stale epochs, and lagging replicas. | Any stale-epoch acceptance, double effect, or divergent state invalidates the configuration. |
| **`H3` · Fair `B` Contribution** | Measure held-out balanced accuracy of `P+B` (FHN) vs. `P + EMA` on identical observation histories and equal hyperparameter budgets. | If advantage disappears (95% bootstrap lower CI `<= +0.02`), attribute gains to generic temporal memory and record a null result without claiming biological specificity. |
| **`H4` · `Q` Equivalence** | Compare every quantum score and winner against `cos^2[pi * (x - p) / 2]` on `[0, 1]^2` (`step = 0.01`), including ties and invalid inputs. | Error `> 1e-12` flags a numerical/backend defect; agreement validates interoperability and classical sufficiency. |
| **`H5` · Perception (Deferred)** | Within-subject comparison of 1 avatar, 2 alternating avatars, and 2 concurrent streams with overlapping targets and real/sham switches. | Frequent misses or detectable switches bound achievable multi-perception; strictly separate ethics-reviewed protocol. |

**Investment Sequencing**:
1. **Immediate (CPU, Python + NumPy)**: `M0`–`M2` (`H1`–`H4`, fault injection, prefix oracle, fair EMA control, campaign bundles) — feeds `T005-XFER-01..05` directly into `q_speace`.
2. **Next (`M3`)**: Separate OS processes with monotonic host clock to measure real IPC failover latency and destination authority.
3. **Optional Offline Biological Compatibility**: Replay public PhysioNet EEG Motor Movement/Imagery recordings [11] strictly as a signal-decoding/compatibility test (classical substrate, no live loop, no persistence claim).
4. **Deferred (`H5`)**: Reversible virtual VR studies only with informed consent, ethics review, and immediate voluntary stop.

---

## 6. Primary References

1. Kishore, S. et al. (2016). *Multi-Destination Beaming: Apparently Being in Three Places at Once through Robotic and Virtual Embodiment*. Frontiers in Robotics and AI. https://doi.org/10.3389/frobt.2016.00065
2. Guterstam, A., Larsson, D. E. O., Szczotka, J., & Ehrsson, H. H. (2020). *Duplication of the bodily self: a perceptual illusion of dual full-body ownership and dual self-location*. Royal Society Open Science. https://doi.org/10.1098/rsos.201911
3. Serizawa, M., Pannattee, P., Fukuchi, Y., Yem, V., Ikei, Y., & Nishiuchi, N. (2026). *Dual Body Sensation: Effects of Visio-Tactile Presentation Methods in Parallel Agent Control*. IEEE TVCG, 32, 3914–3923. https://doi.org/10.1109/TVCG.2026.3679124
4. FitzHugh, R. (1961). *Impulses and Physiological States in Theoretical Models of Nerve Membrane*. Biophysical Journal, 1, 445–466. https://doi.org/10.1016/S0006-3495(61)86902-6
5. Roth, D., & Latoschik, M. E. (2020). *Construction of the Virtual Embodiment Questionnaire (VEQ)*. IEEE TVCG, 26, 3546–3556. https://doi.org/10.1109/TVCG.2020.3023603
6. Warburton, M., Mon-Williams, M., Mushtaq, F., & Morehead, J. R. (2023). *Measuring motion-to-photon latency for sensorimotor experiments with virtual reality systems*. Behavior Research Methods, 55, 3658–3678. https://doi.org/10.3758/s13428-022-01983-5
7. Butlin, P. et al. (2025/2026). *Identifying indicators of consciousness in AI systems*. Trends in Cognitive Sciences, 30, 488–501. https://doi.org/10.1016/j.tics.2025.10.011
8. Schneider, F. B. (1990). *Implementing fault-tolerant services using the state machine approach: a tutorial*. ACM Computing Surveys, 22, 299–319. https://doi.org/10.1145/98163.98167
9. Ongaro, D., & Ousterhout, J. (2014). *In Search of an Understandable Consensus Algorithm*. USENIX ATC, 305–319. https://www.usenix.org/conference/atc14/technical-sessions/presentation/ongaro
10. Bowles, J., Ahmed, S., & Schuld, M. (2024). *Better than classical? The subtle art of benchmarking quantum machine learning models*. arXiv:2403.07059. https://arxiv.org/abs/2403.07059
11. Schalk, G. (2009). *EEG Motor Movement/Imagery Dataset*, v1.0.0, PhysioNet. https://physionet.org/content/eegmmidb/1.0.0/
