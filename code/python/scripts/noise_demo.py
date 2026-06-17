"""Hands-on noise-robustness check.

Synthesizes a clean speech-like signal, adds white noise, then runs the
NoiseReduceDenoiser to measure how much noise it removes. Also exercises the
full SessionService pipeline with denoise + energy gate enabled.

Run:
    python -m scripts.noise_demo
"""
from __future__ import annotations

import asyncio
import math
import struct
import tempfile
import wave
from pathlib import Path

import numpy as np

from app.core.config import Settings
from app.services.denoiser import NoiseReduceDenoiser
from app.services.recorder import get_wav_rms
from app.services.session_service import SessionService

SAMPLE_RATE = 16_000


def _write_signal(path: Path, signal: np.ndarray) -> None:
    pcm = np.clip(signal, -1.0, 1.0)
    data = (pcm * 32767.0).astype(np.int16).tobytes()
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(data)


def _read_signal(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def _rms(signal: np.ndarray) -> float:
    return float(np.sqrt(np.mean(signal**2))) if signal.size else 0.0


def _build_voiced_and_silence(duration: float = 2.4):
    """Alternating 0.3s voiced bursts and 0.3s silence, so a denoiser has a
    real noise reference (the silent gaps). Returns (clean, voiced_mask)."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    seg = int(SAMPLE_RATE * 0.3)
    voiced_mask = (np.arange(n) // seg) % 2 == 0
    tone = 0.4 * np.sin(2 * np.pi * 180 * t) + 0.2 * np.sin(2 * np.pi * 360 * t)
    clean = np.where(voiced_mask, tone, 0.0)
    return clean, voiced_mask


def demo_denoise() -> None:
    print("=" * 60)
    print("1) DENOISE EFFECT (voiced bursts + silence gaps + constant noise)")
    print("=" * 60)
    clean, voiced_mask = _build_voiced_and_silence()
    silence_mask = ~voiced_mask
    rng = np.random.default_rng(42)
    noise = 0.05 * rng.standard_normal(clean.shape)
    noisy = clean + noise

    noise_floor_in = _rms(noisy[silence_mask])     # noise during silence
    signal_in = _rms(noisy[voiced_mask])           # signal+noise during speech
    snr_in = 20 * math.log10(signal_in / max(1e-9, noise_floor_in))

    print(f"{'prop_decrease':>13} {'stationary':>11} {'noise_floor':>12} {'signal_kept':>12} {'SNR_out':>9} {'gain':>7}")
    for stationary in (True, False):
        for prop in (0.6, 0.8, 0.9):
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "noisy.wav"
                _write_signal(p, noisy)
                NoiseReduceDenoiser(prop_decrease=prop, stationary=stationary).denoise(p)
                out = _read_signal(p)
            noise_floor_out = _rms(out[silence_mask])
            signal_out = _rms(out[voiced_mask])
            snr_out = 20 * math.log10(signal_out / max(1e-9, noise_floor_out))
            print(f"{prop:>13.1f} {str(stationary):>11} {noise_floor_out:>12.4f} {signal_out:>12.4f} {snr_out:>9.2f} {snr_out-snr_in:>+7.2f}")

    print()
    print(f"baseline noisy  -> noise_floor={noise_floor_in:.4f}  signal={signal_in:.4f}  SNR_in={snr_in:.2f} dB")
    print("(higher SNR_out + signal_kept close to baseline signal = good)")
    print()


def demo_pipeline() -> None:
    print("=" * 60)
    print("2) FULL PIPELINE WITH DENOISE + ENERGY GATE (real noisereduce)")
    print("=" * 60)
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(
            samples_root=Path(tmp) / "samples",
            chunk_duration_seconds=0.2,
            max_chunks_per_session=3,
            session_poll_interval_seconds=0.01,
            recorder_backend="mock",
            transcriber_backend="mock",
            enable_denoise=True,
            denoise_backend="noisereduce",
            enable_energy_gate=True,
            min_chunk_rms=0.001,
            word_min_probability=0.0,
        )
        service = SessionService(settings)

        async def scenario():
            await service.start("demo")
            await asyncio.sleep(0.4)
            await service.stop("demo")
            for _ in range(60):
                session = service.get("demo")
                if session is not None and session.state.value == "stopped":
                    return session
                await asyncio.sleep(0.02)
            raise AssertionError("session did not stop in time")

        session = asyncio.run(scenario())
        metrics = service.get_metrics()

    print(f"session state         : {session.state.value}")
    print(f"chunks processed      : {session.chunk_count}")
    print(f"words exported        : {session.word_count}")
    print(f"denoised_chunk_count  : {metrics['denoised_chunk_count']}")
    print(f"energy_gated_chunk_count : {metrics['energy_gated_chunk_count']}")
    print(f"low_confidence_word_drops: {metrics['low_confidence_word_drops']}")
    print(f"avg_chunk_latency_ms  : {metrics['avg_chunk_latency_ms']}")
    print()


if __name__ == "__main__":
    demo_denoise()
    demo_pipeline()
    print("Done.")
