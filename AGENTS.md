# B-SPEACE — Agentic Engineering Guide

B-SPEACE is the biological and bio-inspired computational layer for the SPEACE
framework, designed as a modular peer of `q_speace` and `cellular_speace`.

## 1. Modes

### Vibe mode (exploration)
- New analogies / bio-computational concepts under `docs/`.
- Clearly mark output as experimental.
- Do not touch safety-critical paths (`organoid` safety envelopes, interlocks, or metabolic gates).

### Agentic mode (production)
Required for changes to `b_speace/` source, tests, CLI, and interop bridges.
1. Write/update a spec (`docs/Txxx_*_SPEC.md`).
2. Pass the BCEL gate: classify each bio-computational concept as `accidental`
   (remove in silicon / non-operational metaphor) or `functional` (keep as a
   testable mathematical or engineering rule). Record in `b_speace/bcel/catalog.py`.
3. Add/extend tests under `tests/`.
4. Run `pytest`, `ruff`, `black`, `mypy` on touched files.

## 2. Invariants (must never be weakened)
- **No claim of biological consciousness, sentience, or moral agency** for simulated
  or organoid-interfaced computational layers.
- **No direct physical wetware actuation without explicit safety envelope & interlocks**:
  every `OrganoidInterface` adapter MUST enforce a bounded `WetwareSafetyEnvelope`
  (voltage, current, charge density, stimulation frequency, temperature/pH window)
  and an explicit metabolic / `Sevo` efficiency gate.
- **Fail-closed numerical validation**: non-finite values (`NaN`, `±inf`) or out-of-range
  electrode/signal parameters MUST raise typed errors or block stimulation.
- **No faster-than-light / non-local signaling claim** across the `q_speace` hybrid bridge:
  entanglement in `q_speace` is strictly a computational binding resource.
- Every feature needs tests and passes the BCEL filter.

## 3. Quality gates
- [ ] `pytest` passes.
- [ ] `python -m compileall -q b_speace` clean.
- [ ] `ruff check b_speace tests` clean.
- [ ] `black --check b_speace tests` clean.
- [ ] `mypy b_speace` clean.

## 4. Prohibited
- Weakening safety envelopes, interlocks, or the no-consciousness / no-communication invariants.
- Introducing dependencies without updating `pyproject.toml`.
- Deleting tests to raise coverage.
