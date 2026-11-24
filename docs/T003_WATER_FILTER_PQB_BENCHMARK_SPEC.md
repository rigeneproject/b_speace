# T003 — Digital Water-Treatment Filter Testbed & P–Q–B Closed-Loop Benchmark Specification

- **Status**: Active (v0.1.0)
- **Parent Framework**: [T002 — Industry P–Q–B](T002_INDUSTRY_PQB_FRAMEWORK.md)
- **Scientific Grounding**: [`docs/fonti scientifiche.txt`](fonti%20scientifiche.txt)
- **Living Task Tracker**: [`docs/T003_TASKS.md`](T003_TASKS.md)

---

## 1. Scientific & Engineering Motivation

As established in `T002` and reviewed against the literature in `docs/fonti scientifiche.txt`:

1. **Layer B (most mature / field-ready)** — Cell-free allosteric transcription-factor
   (aTF) biosensors with fluorescent aptamer readouts (e.g., ROSALIND — Jung et al.,
   *Nature Biotechnology* 2020) provide low-cost, low-energy, freeze-dried threshold
   detection of water contaminants (metals, antibiotics, small molecules), subject to
   incubation delay, readout noise, matrix interference, and calibration drift.
2. **Layer Q (active research / bounded scope)** — Quantum binding-energy estimation
   for porous sorbents/filters (e.g., qubit-ADAPT-VQE for MOF/DAC binding potentials,
   Barroca et al. 2024, *arXiv:2404.13122* / *APL Quantum*) estimates molecular-scale
   contaminant–site affinity with explicit uncertainty and must be benchmarked directly
   against classical chemistry surrogates (DFT / force fields / ML potentials) at
   comparable compute budgets.
3. **Closed-loop Governance (Simplex-inspired fail-closed switching)** — Hybrid
   quantum-classical and bio-classical loops require explicit uncertainty propagation
   and a **Simplex-style monitor** that falls back to high-reliability classical
   models/assays whenever `B` exhibits excessive false alarms/drift or `Q` exceeds
   uncertainty or `Sevo` metabolic bounds.
4. **Strict BCEL Exclusion** — Speculative claims (such as "retrocausal learning",
   organoid consciousness, or unverified universal quantum advantage) are classified
   as `accidental` and excluded from `b_speace` runtime semantics.

---

## 2. Core Research Questions (Phased)

### Experiment 1 (`P` vs `P + B` — Closed-Loop Biosensor Feedback)
> *If classical controller `P` receives an early contaminant breakthrough signal from
> cell-free biosensor `B`, can it select or revise the next trial earlier while
> preserving material-selection accuracy?*

- **Strict parity**: `P` and `P + B` run on identical paired scenarios, identical
  candidate sets, identical final confirmation rule (only the independent reference
  assay can confirm a material), and **equal target treated volume**
  $V_{\text{target}}$ across both flow rates ($Q_{\text{high}}, Q_{\text{low}}$).
- **Separated primary outcomes**:
  - Wall-clock time to confirmed material (minutes) — captures savings from early
    stopping of failing trials even when trial count is unchanged;
  - Number of physical trials started & early stops;
  - Wrong-selection rate (false acceptance of a non-compliant material or missing
    a compliant material).

### Experiment 2 (`P`, `P + B`, `P + Q`, `P + Q + B` — 4-Way Ablation)
> *When `Q` provides a bounded molecular-scale interaction estimate to reorder
> candidate materials (gated by Simplex uncertainty and `Sevo`), how much does each
> layer contribute individually and does the full triad outperform partial ablations?*

---

## 3. System Architecture & Mathematical Models

### 3.1 Hidden Physical Filter Twin (`b_speace/benchmarks/water_filter/model.py`)

Each candidate material $m$ has **hidden** physical parameters never exposed to
controller `P`:
- Equilibrium adsorption capacity $q_{\max}$ (mg contaminant / g media)
- Mass-transfer / kinetic rate constant $k_a$ (L / (mg · min))
- Optional selectivity / matrix interference factor $\eta \in (0, 1]$

For a filter bed of mass $M_{\text{bed}}$ operating at flow rate $Q \in \{Q_{\text{high}}, Q_{\text{low}}\}$
with inlet concentration $C_0$, the effluent concentration as a function of **treated
volume** $V(t) = Q \cdot t$ follows a Thomas / Bohart–Adams fixed-bed breakthrough curve:

$$C_{\text{out}}(V; Q) = \frac{C_0}{1 + \exp\!\left(\frac{k_a}{Q} \cdot \left(\eta \, q_{\max} M_{\text{bed}} - C_0 V\right)\right)}$$

Key physical properties:
1. **Normalized by treated volume $V$**: A trial targeting $V_{\text{target}}$ requires
   duration $T(Q) = V_{\text{target}} / Q$. Lowering flow rate from $Q_{\text{high}}$
   to $Q_{\text{low}}$ increases trial duration by $Q_{\text{high}} / Q_{\text{low}}$,
   honestly penalizing unnecessary flow-rate reductions.
2. **Separates thermodynamics from kinetics**:
   - *Low-capacity material* ($\eta q_{\max} M_{\text{bed}} \ll C_0 V_{\text{target}}$):
     breaks through early at **both** $Q_{\text{high}}$ and $Q_{\text{low}}$.
   - *Kinetically limited material* (adequate $\eta q_{\max} M_{\text{bed}}$, low $k_a$):
     exhibits early mass-transfer breakthrough at $Q_{\text{high}}$, but passes the
     threshold $C_{\text{out}}(V_{\text{target}}) \le C_{\text{limit}}$ at $Q_{\text{low}}$
     because residence time increases ($k_a / Q$ grows).
   - *Optimal material* (high $\eta q_{\max}$, high $k_a$): passes at $Q_{\text{high}}$.
   - *Marginal material*: hovers near $C_{\text{limit}}$ at $V_{\text{target}}$, stress-testing
     biosensor noise, drift, and false-alarm handling.

### 3.2 Cell-Free Biomolecular Sensor (`b_speace/biomolecular/`)

Inspired by ROSALIND (Jung et al. 2020):
- **Protocols**: `@runtime_checkable` `BiomolecularSensor` and `ReferenceAssayPort`.
- **Allosteric Hill response** (`CellFreeThresholdSensorAdapter`):
  $$y(c, t) = F_{\min} + (F_{\max} - F_{\min}) \frac{c_{\text{eff}}^{n}}{K_d(t)^n + c_{\text{eff}}^{n}} + \epsilon, \quad \epsilon \sim \mathcal{N}(0, \sigma^2)$$
  where $K_d(t) = K_{d,0} \cdot (1 + \delta \cdot t)$ models calibration/reagent drift,
  $c_{\text{eff}} = c \cdot (1 + \beta_{\text{matrix}})$ captures matrix interference,
  and readings arrive after configurable incubation delay $\Delta t_B$.
- **Threshold decision**: `threshold_crossed = (y >= y_threshold)` with an estimated
  confidence/uncertainty score returned in `BiosensorReading`.
- **Reference Assay (`SimulatedReferenceAssayAdapter`)**: models ICP-MS / LC-MS
  verification with low measurement noise, longer laboratory turnaround $\Delta t_{\text{ref}}$,
  and higher marginal cost per sample.

### 3.3 Classical Controller `P` & Simplex Fail-Closed Monitor (`controller.py`)

- **Candidate Ranking Protocol (`CandidateRanker`)**:
  - `ClassicalBaselineRanker`: orders candidates using noisy classical surrogate scores
    (or fixed order) without accessing hidden filter parameters.
  - `QuantumInteractionRanker` (Experiment 2): delegates selected candidates to
    `b_speace.interop.QuantumKernelPort` (`QSpeaceKernelAdapter` when `q_speace` is
    installed, else `StandaloneQuantumKernelAdapter`), enforcing the `Sevo` gate and
    Simplex uncertainty threshold $\sigma_Q \le \sigma_{\max}$.
- **Closed-Loop Feedback & Simplex Monitor**:
  - During a trial at $Q_{\text{high}}$, `P` receives scheduled reference assays at
    volume intervals $\Delta V_{\text{ref}}$; in `P+B` / `P+Q+B`, `P` also polls `B`
    at finer intervals $\Delta V_B$.
  - On **confirmed** or **early `B` breakthrough** (above threshold after persistence
    debounce), `P` triggers `EARLY_STOP`:
    - If on $Q_{\text{high}}$, schedules `RETRY_LOW_FLOW` ($Q_{\text{low}}$) to test
      whether contact time / kinetics limited removal.
    - If already on $Q_{\text{low}}$, triggers `DISCARD_MATERIAL`.
  - **Simplex monitor for `B`**: every arriving reference assay cross-checks `B`'s
    corresponding prediction. If disagreements exceed `max_b_disagreements`, `P` emits
    `FALLBACK_DISABLE_B` and completes the campaign in safe `P-only` mode.
  - **Final acceptance invariant**: only a complete trial reaching $V_{\text{target}}$
    with final **reference assay** $C_{\text{ref}} \le C_{\text{limit}}$ can emit
    `CONFIRM_MATERIAL`.
- **Causal Decision Provenance (`DecisionRecord`)**:
  Every state change records `(step_index, time_min, material_id, flow_rate_l_min,
  treated_volume_l, trigger_source, trigger_summary, action, rationale)`.

---

## 4. Pre-Registered Cost & Metric Accounting

Every benchmark run reports:
- `time_to_confirm_min` (elapsed wall-clock time including assay turnaround)
- `trials_started`, `early_stops`, `low_flow_retries`
- `total_treated_volume_l`
- `reference_assays_used`, `biosensor_assays_used`, `quantum_evals_used`
- `confirmed_material_id`, `confirmed_flow_rate`, `selection_correct`, `optimal_throughput_hit`
- `fixed_setup_cost_usd` vs `marginal_campaign_cost_usd` (explicit break-even separation)
- `estimated_energy_wh` across `P`, `Q`, and `B`
- `b_fallback_triggered`, `q_fallback_triggered`
- Full `decision_trace` for auditability.

---

## 5. Quality & Anti-Leakage Verification Gates

1. **Zero leakage**: `FilterTrialController` never receives or inspects `FilterMaterial`
   ground-truth kinetic/capacity fields.
2. **Determinism**: identical seeds produce bit-for-bit identical traces and metrics.
3. **Fail-closed safety**: invalid biosensor/filter parameters, non-finite inputs, or
   excessive drift/uncertainty must raise typed errors or trigger Simplex fallback.
4. **CI Gates**: `ruff`, `black`, `mypy`, `compileall`, and `pytest` with ≥ 70% coverage.
