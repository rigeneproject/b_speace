# T002 — Industry P–Q–B: Hybrid Classical–Quantum–Biological Computing Architecture

- **Status**: Conceptual Framework & Evaluation Reference (v0.1.0)
- **Scope**: Systemic P–Q–B architecture, closed-loop uncertainty governance,
  worked industrial case study (water-treatment filter development), and
  ablation methodology for `b_speace` and `q_speace`.

## 1. Architecture Overview

**Industry P–Q–B** is a proposed architecture for integrating three distinct
modes of information processing—**classical (`P`)**, **quantum (`Q`)**, and
**biological (`B`)** computing—within a shared experimental or operational
workflow:

- **P (Procedural / Classical computing)**: by convention, denotes the entire
  classical computing stack, including parallel processing, multiscale numerical
  modelling, process control, experimental design, and statistical analysis.
- **Q (Quantum computing)**: executes selected subproblems on quantum processors
  (or noise-modeled quantum simulators), such as estimating molecular-scale
  electronic structure or binding interactions.
- **B (Biological computing)**: processes information through calibrated cellular
  or biomolecular mechanisms—for example, cell-free molecular circuits that
  transduce a chemical input into a thresholded output, or bio-electric /
  organoid signal-processing substrates.

The triad becomes **systemic** through **closed-loop coordination**. The three
layers continuously exchange predictions, measurements, and explicit **estimates
of uncertainty** so that an output from one component can revise which
experiment is performed or which computation is requested next.

### Fail-Closed Uncertainty Governance

To prevent cross-layer error amplification, closed-loop coordination must remain
**fail-closed**:

- Whenever quantum estimation uncertainty exceeds predefined bounds, or the
  metabolic/entropic efficiency gate (`Sevo`) rejects a quantum dispatch, `P`
  falls back to classical surrogate models.
- Whenever biosensor calibration drift, matrix interference, or wetware health
  telemetry breaches the safety/validity envelope, `P` downgrades `B` and routes
  verification to reference classical instrumentation.

### Why Industry First?

Industrial adoption provides a disciplined proving ground for the paradigm. An
industrial operator can translate a concrete operational requirement into
measurable technical specifications, test whether closed-loop P–Q–B coordination
produces a net benefit under realistic constraints, and standardize reusable
interfaces and validation protocols. Once validated, those interfaces and
evaluation methods can be transferred to scientific research, environmental
monitoring, and economic resource management.

---

## 2. Worked Example — Developing Filters for Water Treatment

Consider a manufacturer developing a filter material that removes a target
contaminant within strict cost, flow-rate, and service-life requirements.

| Component | Role in the Proposed Workflow |
|---|---|
| **P · Classical computing** | Shortlists candidate materials from historical measurements and classical surrogate models; acts as the **multiscale integrator** coupling molecular-scale estimates with macroscopic transport/adsorption models; specifies comparable trial conditions (flow rate, inlet concentration, sampling schedule) and governs uncertainty-aware iteration. |
| **Q · Quantum computing** | For shortlisted candidates, estimates the interaction/binding energy between the target contaminant and a representative binding site. Its predictive value is benchmarked directly against the strongest feasible classical chemistry baseline (e.g., DFT or machine-learned interatomic potentials) at comparable compute budgets. |
| **B · Biological computing** | A calibrated cell-free molecular circuit screens downstream water samples in-situ and signals which concentration thresholds have been crossed. This provides rapid, low-energy feedback between periodic laboratory reference checks (e.g., LC-MS / ICP-MS) used to bound false-positive and false-negative rates. |

### Closing the Cross-Scale Feedback Loop

The feedback loop closes when downstream measurements actively change the next
decision:

1. Suppose the molecular-scale estimate from `Q` predicts strong binding, yet
   the downstream cell-free assay `B` indicates that the specified concentration
   threshold is crossed earlier than expected.
2. `P` uses this cross-scale discrepancy to formulate a falsifiable hypothesis:
   - **Kinetic / mass-transfer hypothesis**: schedule a follow-up trial at a
     lower flow rate to test whether contact time or pore diffusion limits
     contaminant removal.
   - **Affinity / selectivity hypothesis**: if the discrepancy persists at lower
     flow rate, penalize the candidate material, recalibrate the multiscale
     mapping, and select an alternative candidate.

Bridging molecular interaction estimates (`Q`) with macroscopic flow-through
performance (`B` + `P`) gives the workflow an actionable, physical basis for
revising each subsequent experiment.

---

## 3. Ablation Protocol & Success Metrics

Whether P–Q–B yields a net industrial advantage is an empirical question that
must be tested against current practice and partial configurations:

| Configuration | Active Layers | Evaluation Question |
|---|---|---|
| **Baseline (`P-only`)** | Classical chemistry surrogate + standard lab analytics | Incumbent industrial development baseline |
| **Partial (`P + Q`)** | `P` + quantum interaction estimates (without `B`) | Marginal predictive value of `Q` vs classical chemistry at equal compute budget |
| **Partial (`P + B`)** | `P` + cell-free threshold biosensor (without `Q`) | Marginal speedup, energy, and per-sample cost value of `B` in iterative screening |
| **Full Triad (`P + Q + B`)** | Closed-loop triad + periodic analytical reference checks | Net synergistic benefit over `P-only`, `P + Q`, and `P + B` |

### Pre-Registered Metrics

- **Primary outcome**: number of physical filter trials required to identify a
  material meeting a predefined removal target at specified flow rate and
  service life.
- **Secondary operational metrics**:
  - Total elapsed wall-clock time;
  - End-to-end energy consumption across `P`, `Q`, and `B`;
  - Cost accounting separating **fixed one-time setup/calibration costs**
    (Hamiltonian formulation/embedding for `Q`; cell-free circuit design and
    calibration for `B`) from **marginal per-trial costs**, establishing the
    break-even horizon across material campaigns;
  - Analytical verification agreement (false-positive / false-negative rate of
    `B` against reference lab instrumentation).

---

## 4. Mapping to `b_speace` & `q_speace` (BCEL Alignment)

- **P layer**: `BioOrchestrator` (`b_speace/orchestrator.py`), classical control
  and evaluation contracts (`q_speace/vertical_slice/`).
- **Q layer**: `QuantumKernelPort` / `QSpeaceKernelAdapter` (`b_speace/interop/`)
  wrapping `q_speace` quantum circuits and `QuantumCostModel` (`Sevo` gate).
- **B layer**: `b_speace/bioelectric/` (excitable membrane simulators & codecs),
  `b_speace/organoid/` (safety-gated Wetware-in-the-loop MEA interfaces), and
  future `b_speace/biomolecular/` adapters for cell-free chemical threshold
  circuits.
- **BCEL non-claims**: no claim of universal quantum advantage, biological
  sentience, or self-validating operational autonomy is implied. Every layer is
  treated strictly as a calibrated, falsifiable computational resource subject
  to safety envelopes and empirical ablation.
