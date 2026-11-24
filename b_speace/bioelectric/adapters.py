"""Abstract base and reference in-silico adapters for bio-electric simulation (T001)."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Sequence

import numpy as np

from .types import (
    BioSignalFrame,
    BioSignalValidationError,
    EncodedBioFeatures,
    IonChannelParams,
    MembraneState,
    StimulationPulse,
)


class BaseBioElectricAdapter(ABC):
    """Abstract base adapter handling validation and pulse scheduling."""

    simulator_name: str = "abstract_bioelectric"

    def __init__(
        self,
        num_channels: int,
        dt_ms: float = 0.5,
        channel_ids: Sequence[str] | None = None,
        seed: int | None = None,
    ) -> None:
        if num_channels < 1:
            raise BioSignalValidationError(f"num_channels must be >= 1 (got {num_channels})")
        if not math.isfinite(dt_ms) or dt_ms <= 0.0:
            raise BioSignalValidationError(f"dt_ms must be finite and > 0 (got {dt_ms})")
        if channel_ids is not None:
            ids = tuple(channel_ids)
            if len(ids) != num_channels or len(set(ids)) != num_channels:
                raise BioSignalValidationError(
                    "channel_ids must have unique entries matching num_channels"
                )
        else:
            ids = tuple(f"bio_ch_{i}" for i in range(num_channels))

        self.num_channels: int = num_channels
        self.dt_ms: float = float(dt_ms)
        self.channel_ids: tuple[str, ...] = ids
        self._seed: int | None = seed
        self._rng = np.random.default_rng(seed)

    def _validate_external_current(
        self, external_current: Sequence[float] | np.ndarray | None
    ) -> np.ndarray:
        if external_current is None:
            return np.zeros(self.num_channels, dtype=np.float64)
        arr = np.asarray(external_current, dtype=np.float64).ravel()
        if arr.size != self.num_channels:
            raise BioSignalValidationError(
                f"external_current length {arr.size} != num_channels {self.num_channels}"
            )
        if not np.all(np.isfinite(arr)):
            raise BioSignalValidationError("external_current contains non-finite values")
        return arr

    @abstractmethod
    def reset(self, seed: int | None = None) -> MembraneState:
        """Reset simulator state."""

    @abstractmethod
    def state_snapshot(self) -> MembraneState:
        """Return a defensive copy of current state."""

    @abstractmethod
    def _integrate_step(self, currents: np.ndarray) -> BioSignalFrame:
        """Advance state by one step using validated channel currents."""

    def step(self, external_current: Sequence[float] | np.ndarray | None = None) -> BioSignalFrame:
        currents = self._validate_external_current(external_current)
        return self._integrate_step(currents)

    def run(
        self, steps: int, pulses: Sequence[StimulationPulse] | None = None
    ) -> list[BioSignalFrame]:
        if steps < 0:
            raise BioSignalValidationError(f"steps must be >= 0 (got {steps})")
        validated_pulses: list[StimulationPulse] = []
        if pulses is not None:
            for pulse in pulses:
                pulse.validate(num_channels=self.num_channels)
                validated_pulses.append(pulse)

        frames: list[BioSignalFrame] = []
        for _ in range(steps):
            t_now = self.state_snapshot().time_ms
            currents = np.zeros(self.num_channels, dtype=np.float64)
            for pulse in validated_pulses:
                if pulse.start_ms <= t_now < pulse.start_ms + pulse.duration_ms:
                    elapsed = t_now - pulse.start_ms
                    if pulse.biphasic and elapsed >= 0.5 * pulse.duration_ms:
                        # Charge-balanced anodic/cathodic second phase.
                        eff_amp = -pulse.amplitude_ua
                    else:
                        eff_amp = pulse.amplitude_ua
                    for idx in pulse.channel_indices:
                        currents[idx] += eff_amp
            frames.append(self._integrate_step(currents))
        return frames


class FitzHughNagumoAdapter(BaseBioElectricAdapter):
    """Deterministic multi-channel FitzHugh-Nagumo bio-electric simulator.

    Integrates:
        dv_i/dt = v_i - v_i^3 / 3 - w_i + I_i + sum_j G_ij (v_j - v_i)
        dw_i/dt = (v_i + a - b * w_i) / tau

    using Heun's second-order Runge-Kutta scheme. Gap-junction coupling is
    modeled via an optional symmetric non-negative coupling matrix ``G``.
    """

    simulator_name = "fitzhugh_nagumo"

    def __init__(
        self,
        num_channels: int = 4,
        dt_ms: float = 0.25,
        params: IonChannelParams | None = None,
        coupling_strength: float = 0.05,
        noise_std: float = 0.0,
        channel_ids: Sequence[str] | None = None,
        seed: int | None = None,
    ) -> None:
        super().__init__(
            num_channels=num_channels,
            dt_ms=dt_ms,
            channel_ids=channel_ids,
            seed=seed,
        )
        self.params = params or IonChannelParams()
        self.params.validate()
        if not math.isfinite(coupling_strength) or coupling_strength < 0.0:
            raise BioSignalValidationError(
                f"coupling_strength must be finite and >= 0 (got {coupling_strength})"
            )
        if not math.isfinite(noise_std) or noise_std < 0.0:
            raise BioSignalValidationError(f"noise_std must be finite and >= 0 (got {noise_std})")
        self._coupling_strength = float(coupling_strength)
        self._noise_std = float(noise_std)
        self._laplacian = self._build_ring_laplacian(num_channels, self._coupling_strength)
        self._state = self.reset(seed=seed)

    @staticmethod
    def _build_ring_laplacian(n: int, strength: float) -> np.ndarray:
        mat = np.zeros((n, n), dtype=np.float64)
        if n <= 1 or strength == 0.0:
            return mat
        for i in range(n):
            left = (i - 1) % n
            right = (i + 1) % n
            mat[i, left] += strength
            mat[i, right] += strength
            mat[i, i] -= 2.0 * strength
        return mat

    def reset(self, seed: int | None = None) -> MembraneState:
        effective_seed = self._seed if seed is None else seed
        self._rng = np.random.default_rng(effective_seed)
        # Resting equilibrium approximation for standard FHN (a=0.7, b=0.8).
        v0 = np.full(self.num_channels, -1.1994, dtype=np.float64)
        w0 = np.full(self.num_channels, -0.6243, dtype=np.float64)
        self._state = MembraneState(potentials=v0, recovery=w0, time_ms=0.0)
        return self._state.copy()

    def state_snapshot(self) -> MembraneState:
        return self._state.copy()

    def _derivatives(
        self, v: np.ndarray, w: np.ndarray, currents: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        p = self.params
        # Convert microamp-scale input currents into bounded dimensionless drive.
        drive = np.clip(currents * 0.1, -5.0, 5.0)
        coupled = self._laplacian @ v
        dv = v - (v**3) / 3.0 - w + drive + coupled
        dw = (v + p.a - p.b * w) / p.tau
        return dv, dw

    def _integrate_step(self, currents: np.ndarray) -> BioSignalFrame:
        v = self._state.potentials
        w = self._state.recovery
        dt = self.dt_ms

        dv1, dw1 = self._derivatives(v, w, currents)
        v_pred = np.clip(v + dt * dv1, -5.0, 5.0)
        w_pred = np.clip(w + dt * dw1, -5.0, 5.0)
        dv2, dw2 = self._derivatives(v_pred, w_pred, currents)

        v_next = v + 0.5 * dt * (dv1 + dv2)
        w_next = w + 0.5 * dt * (dw1 + dw2)
        if self._noise_std > 0.0:
            v_next = v_next + self._rng.normal(0.0, self._noise_std * math.sqrt(dt), size=v.size)

        v_next = np.clip(v_next, -5.0, 5.0)
        w_next = np.clip(w_next, -5.0, 5.0)
        next_time = self._state.time_ms + dt
        self._state = MembraneState(potentials=v_next, recovery=w_next, time_ms=next_time)

        p = self.params
        potentials_mv = tuple(
            float(p.resting_potential_mv + (val + 1.1994) * p.voltage_scale_mv) for val in v_next
        )
        spike_mask = tuple(bool(val >= p.spike_threshold) for val in v_next)
        # Modeled instantaneous metabolic/electrical dissipation proxy (uW).
        power_uw = float(
            0.05 * self.num_channels
            + 0.25 * sum(1 for s in spike_mask if s)
            + 0.02 * float(np.sum(np.abs(currents)))
        )
        return BioSignalFrame(
            timestamp_ms=next_time,
            channel_ids=self.channel_ids,
            potentials_mv=potentials_mv,
            spike_mask=spike_mask,
            instantaneous_power_uw=power_uw,
            metadata={"mean_recovery": float(np.mean(w_next))},
        )


class PopulationRateCodec:
    """Bidirectional bio-signal encoder/decoder (rate + phase encoding).

    Implements both :class:`BioSignalEncoder` and :class:`BioSignalDecoder`.
    """

    encoder_name: str = "population_rate_phase_encoder"
    decoder_name: str = "population_rate_pulse_decoder"

    def __init__(
        self,
        max_pulse_amplitude_ua: float = 15.0,
        default_pulse_duration_ms: float = 2.0,
    ) -> None:
        if not math.isfinite(max_pulse_amplitude_ua) or max_pulse_amplitude_ua <= 0.0:
            raise BioSignalValidationError("max_pulse_amplitude_ua must be finite and > 0")
        if not math.isfinite(default_pulse_duration_ms) or default_pulse_duration_ms <= 0.0:
            raise BioSignalValidationError("default_pulse_duration_ms must be finite and > 0")
        self._max_amp = float(max_pulse_amplitude_ua)
        self._default_dur = float(default_pulse_duration_ms)

    def encode(self, frames: Sequence[BioSignalFrame]) -> EncodedBioFeatures:
        if not frames:
            raise BioSignalValidationError("frames must be non-empty")
        channel_ids = frames[0].channel_ids
        n_ch = len(channel_ids)
        if n_ch == 0:
            raise BioSignalValidationError("frames must contain >= 1 channel")
        for f in frames:
            if f.channel_ids != channel_ids:
                raise BioSignalValidationError("all frames must share identical channel_ids")

        potentials = np.array([f.potentials_mv for f in frames], dtype=np.float64)
        spikes = np.array([f.spike_mask for f in frames], dtype=np.float64)

        # Positive rectified depolarization above -70 mV plus spike weight.
        depol = np.maximum(potentials + 70.0, 0.0).mean(axis=0)
        spike_rates = spikes.mean(axis=0)
        raw_activity = depol * 0.05 + spike_rates + 1e-6
        total = float(raw_activity.sum())
        norm_activity = raw_activity / total

        # Map mean channel potential into quantum-compatible rotation angles [0, pi].
        mean_v = potentials.mean(axis=0)
        clipped_unit = np.clip((mean_v + 80.0) / 120.0, 0.0, 1.0)
        phases = clipped_unit * math.pi

        # Firing rate estimate across observation window.
        if len(frames) >= 2:
            span_ms = max(frames[-1].timestamp_ms - frames[0].timestamp_ms, 1e-3)
        else:
            span_ms = 1.0
        firing_rate_hz = float((spikes.sum() / n_ch) / (span_ms / 1000.0))

        # Kuramoto order parameter proxy over channel phase angles.
        complex_phases = np.exp(1j * phases)
        synchrony = float(np.abs(np.mean(complex_phases)))

        # Shannon entropy of normalized channel activity distribution (bits).
        probs = np.clip(norm_activity, 1e-12, 1.0)
        entropy_bits = float(-np.sum(probs * np.log2(probs)))

        return EncodedBioFeatures(
            channel_ids=channel_ids,
            normalized_activity=tuple(float(x) for x in norm_activity),
            phase_angles_rad=tuple(float(x) for x in phases),
            firing_rate_hz=firing_rate_hz,
            synchrony_index=synchrony,
            shannon_entropy_bits=entropy_bits,
        )

    def decode(self, control_vector: Sequence[float], channel_count: int) -> list[StimulationPulse]:
        if channel_count < 1:
            raise BioSignalValidationError(f"channel_count must be >= 1 (got {channel_count})")
        vec = np.asarray(control_vector, dtype=np.float64).ravel()
        if vec.size != channel_count:
            raise BioSignalValidationError(
                f"control_vector length {vec.size} != channel_count {channel_count}"
            )
        if not np.all(np.isfinite(vec)):
            raise BioSignalValidationError("control_vector contains non-finite values")
        if np.any(vec < 0.0) or np.any(vec > 1.0):
            raise BioSignalValidationError("control_vector entries must be in [0.0, 1.0]")

        pulses: list[StimulationPulse] = []
        for idx, weight in enumerate(vec):
            if weight <= 1e-4:
                continue
            pulses.append(
                StimulationPulse(
                    channel_indices=(idx,),
                    amplitude_ua=float(weight * self._max_amp),
                    duration_ms=self._default_dur,
                    start_ms=0.0,
                    frequency_hz=10.0,
                    biphasic=True,
                )
            )
        return pulses
