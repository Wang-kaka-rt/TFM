from __future__ import annotations

import asyncio
import math
import struct
import wave
from pathlib import Path

from app.core.config import Settings
from app.services.denoiser import NullDenoiser, create_denoiser
from app.services.recorder import get_wav_rms
from app.services.session_service import SessionService
from app.services.transcriber import WordTiming


def _write_wav(path: Path, *, amplitude: float, duration_seconds: float = 0.1, sample_rate: int = 16_000) -> None:
    frame_count = max(1, int(duration_seconds * sample_rate))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frame_count):
            value = int(amplitude * 32767 * math.sin(2.0 * math.pi * 220 * index / sample_rate))
            wav_file.writeframes(struct.pack("<h", value))


def test_word_timing_defaults_to_full_probability():
    word = WordTiming(word="hola", start=0.0, end=0.2)
    assert word.probability == 1.0


def test_get_wav_rms_distinguishes_silence_from_signal(tmp_path):
    silent = tmp_path / "silent.wav"
    loud = tmp_path / "loud.wav"
    _write_wav(silent, amplitude=0.0)
    _write_wav(loud, amplitude=0.5)

    assert get_wav_rms(silent) == 0.0
    assert get_wav_rms(loud) > 0.1


def test_create_denoiser_defaults_to_null():
    assert isinstance(create_denoiser("null"), NullDenoiser)
    assert isinstance(create_denoiser("unknown-backend"), NullDenoiser)
    assert create_denoiser("null").denoise(Path("does-not-matter.wav")) is False


def test_energy_gate_drops_near_silent_chunks(tmp_path):
    settings = Settings(
        samples_root=tmp_path / "samples",
        chunk_duration_seconds=0.05,
        max_chunks_per_session=2,
        session_poll_interval_seconds=0.01,
        recorder_backend="mock",
        transcriber_backend="mock",
        enable_energy_gate=True,
        min_chunk_rms=1.0,  # impossibly high → every chunk is gated as "silence"
    )
    service = SessionService(settings)

    async def scenario():
        await service.start("gate01")
        await asyncio.sleep(0.15)
        await service.stop("gate01")
        for _ in range(50):
            session = service.get("gate01")
            if session is not None and session.state.value == "stopped":
                return session
            await asyncio.sleep(0.02)
        raise AssertionError("session did not finish stopping in time")

    session = asyncio.run(scenario())

    assert session.chunk_count == 2
    assert session.word_count == 0  # all chunks gated → no words exported
    metrics = service.get_metrics()
    assert metrics["energy_gated_chunk_count"] == 2


def test_confidence_filter_drops_low_probability_words(tmp_path, monkeypatch):
    from app.services import session_service as session_service_module

    settings = Settings(
        samples_root=tmp_path / "samples",
        chunk_duration_seconds=0.05,
        max_chunks_per_session=1,
        session_poll_interval_seconds=0.01,
        recorder_backend="mock",
        transcriber_backend="mock",
        word_min_probability=0.5,
    )
    service = SessionService(settings)

    # Force the mock transcriber to emit one confident word and one noisy word.
    def fake_transcribe(audio_path, *, chunk_index):
        return [
            WordTiming(word="hola", start=0.0, end=0.1, probability=0.9),
            WordTiming(word="ruido", start=0.1, end=0.2, probability=0.2),
        ]

    monkeypatch.setattr(service._transcriber, "transcribe", fake_transcribe)

    async def scenario():
        await service.start("conf01")
        await asyncio.sleep(0.1)
        await service.stop("conf01")
        for _ in range(50):
            session = service.get("conf01")
            if session is not None and session.state.value == "stopped":
                return session
            await asyncio.sleep(0.02)
        raise AssertionError("session did not finish stopping in time")

    session = asyncio.run(scenario())

    assert session.word_count == 1  # only the confident word survives
    metrics = service.get_metrics()
    assert metrics["low_confidence_word_drops"] >= 1
