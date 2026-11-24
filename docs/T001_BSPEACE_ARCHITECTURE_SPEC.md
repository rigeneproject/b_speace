# T001 — B-SPEACE Modular Architecture & Protocol/Adapter Specification

- **Status**: Active (Baseline v0.1.0)
- **Scope**: `b_speace/` package layout, abstract `Protocol` / `Adapter` contracts,
  safety envelopes, BCEL classifications, and `q_speace` interoperability.

## 1. Purpose

`b_speace` provides the biological and bio-inspired computational layer for the
SPEACE architecture. Following the same engineering discipline as `q_speace`
(notably `q_speace/spiking_brain/interface.py` and `q_speace/quantum/backends/base.py`),
all domain boundaries are defined through `@runtime_checkable` `typing.Protocol`
interfaces paired with explicit abstract base adapters (`ABC`) and deterministic
in-silico reference implementations.

## 2. Core Subpackages & Contracts

### 2.1 Bio-Electric Signal Simulation (`b_speace.bioelectric`)

- **Protocols**:
  - `BioElectricSimulator`: stateful step-wise generator of multi-channel membrane
    potentials (`BioSignalFrame`) driven by deterministic external currents
    (`StimulationPulse` or channel current arrays).
  - `BioSignalEncoder`: maps raw membrane potential / spike traces into normalized
    computational feature vectors suitable for downstream classical or quantum stages.
  - `BioSignalDecoder`: translates normalized control / modulation vectors back into
    bounded stimulation pulses.
- **Reference Adapters**:
  - `BaseBioElectricAdapter(ABC)`: validates finite inputs, channel counts, and dt.
  - `FitzHughNagumoAdapter`: deterministic two-variable excitable membrane ODE model
    ($dv/dt = v - v^3/3 - w + I$, $dw/dt = (v + a - b w)/\tau$) across $N$ coupled
    channels with optional diffusive gap-junction coupling matrix.
  - `PopulationRateCodec`: bidirectional spike-rate / phase-angle encoder and decoder.

### 2.2 Computational Organoids — Wetware-in-the-Loop APIs (`b_speace.organoid`)

- **Lifecycle**:
  `OFFLINE -> CALIBRATING -> READY -> STIMULATING -> READY -> SHUTDOWN` (plus `FAULT`).
- **Safety Invariant (Fail-Closed)**:
  - Every stimulation command MUST pass `WetwareSafetyGate.validate(command, health)`
    against a `WetwareSafetyEnvelope` bounding peak voltage (mV), peak current (µA),
    pulse duration (ms), charge density per phase (µC/cm²), stimulation frequency (Hz),
    culture temperature (°C), pH, and minimum viability index.
  - Non-finite values, uncalibrated or shut-down lifecycles, or envelope violations
    raise typed `OrganoidError` subclasses (`OrganoidSafetyViolationError`,
    `OrganoidUnavailableError`, `OrganoidCalibrationError`, `OrganoidHealthError`).
- **Protocols & Adapters**:
  - `OrganoidInterface`: async lifecycle (`connect`/`calibrate`/`shutdown`),
    `stimulate`, `record`, `closed_loop_step`, and `health`.
  - `BaseOrganoidAdapter(ABC)`: template class enforcing lifecycle transitions and
    mandatory safety-gate checks before delegating to hardware or simulator hooks.
  - `SimulatedOrganoidAdapter`: deterministic in-silico Multi-Electrode Array (MEA)
    twin backed by a `BioElectricSimulator` with simulated electrode impedance,
    refractory dynamics, and metabolic telemetry.

### 2.3 Hybrid Classical-Quantum Interoperability (`b_speace.interop`)

- **Design goal**: zero mandatory import-time dependency on `q_speace`, while
  supporting first-class native interoperability whenever `q_speace` is installed.
- **Structural Protocols**:
  - `QuantumKernelPort`: structural contract matching `q_speace` hybrid quantum
    execution (`register_channel`, `bind_channels`, `set_activity`, `execute_bio_packet`,
    `evaluate_sevo`).
  - `BioQuantumAdapter`: translates `BioSignalFrame` / `MEARecording` objects into
    `QuantumBioPacket` payloads (angle-encoded rotations, normalized activity vector,
    estimated energy & entropic efficiency `Sevo`), invokes the quantum kernel port,
    and returns classical feedback modulation (`HybridTickResult`).
- **Adapters**:
  - `StandaloneQuantumKernelAdapter`: lightweight deterministic numpy state-vector
    kernel implementing `QuantumKernelPort` so `b_speace` runs and tests standalone.
  - `QSpeaceKernelAdapter`: lazy-binding adapter wrapping `q_speace.QuantumNeuralBridge`,
    `q_speace.BrainQuantumCircuit`, `q_speace.QuantumBrainSimulator`, and
    `q_speace.QuantumCostModel`.

## 3. BCEL Gate & Non-Claims

All concepts introduced here are recorded in `b_speace/bcel/catalog.py`.
No claim of biological consciousness, wetware moral agency, physical hardware
qualification, or faster-than-light quantum signaling is made or implied.
