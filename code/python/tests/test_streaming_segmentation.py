"""Tests for streaming silence-based segmentation in MicrophoneRecorder.

These exercise the RMS state machine in `record_segment` with a synthetic audio
stream (no real microphone), covering the three behaviors that replace fixed
2.5s slicing: clean speech segmentation, the latency hard cap, and discarding
spurious noise onsets.
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from app.services.recorder import MicrophoneRecorder

SAMPLE_RATE = 16_000
BLOCK = int(0.03 * SAMPLE_RATE)


def _block(amplitude: float) -> bytes:
    return b"".join(
        struct.pack("<h", int(amplitude * 32767 * math.sin(2 * math.pi * 220 * i / SAMPLE_RATE)))
        for i in range(BLOCK)
    )


SILENCE = _block(0.001)
SPEECH = _block(0.10)


class _FakeStream:
    def __init__(self, script: list[bytes]) -> None:
        self._script = script
        self._index = 0

    def __enter__(self) -> "_FakeStream":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self, _frames: int) -> tuple[bytes, bool]:
        block = self._script[self._index] if self._index < len(self._script) else SILENCE
        self._index += 1
        return block, False


class _FakeSounddevice:
    def __init__(self, script: list[bytes]) -> None:
        self._script = script

    def RawInputStream(self, **_kwargs: object) -> _FakeStream:  # noqa: N802 - mirrors sounddevice API
        return _FakeStream(self._script)


def _run(script: list[bytes], output_path: Path) -> float:
    recorder = MicrophoneRecorder.__new__(MicrophoneRecorder)
    recorder._sounddevice = _FakeSounddevice(script)  # type: ignore[attr-defined]
    recorder._device = None  # type: ignore[attr-defined]

    calls = {"n": 0}

    def stop_requested() -> bool:
        calls["n"] += 1
        return calls["n"] > 2000  # safety brake so the loop cannot hang

    info = recorder.record_segment(
        output_path,
        sample_rate=SAMPLE_RATE,
        channels=1,
        chunk_index=1,
        stop_requested=stop_requested,
    )
    return info.duration_seconds


def test_speech_is_segmented_at_surrounding_silence(tmp_path: Path) -> None:
    # 5 silence -> 30 speech (~0.9s) -> trailing silence beyond the hangover.
    script = [SILENCE] * 5 + [SPEECH] * 30 + [SILENCE] * 40
    out = tmp_path / "segment.wav"

    duration = _run(script, out)

    # preroll + speech + hangover, never cut mid-speech.
    assert 1.2 <= duration <= 2.2
    with wave.open(str(out)) as wav_file:
        assert wav_file.getnframes() > 0


def test_continuous_speech_is_cut_at_latency_cap(tmp_path: Path) -> None:
    # 12s of uninterrupted speech must be force-cut near the 8s cap.
    duration = _run([SPEECH] * 400, tmp_path / "long.wav")
    assert 7.5 <= duration <= 8.6


def test_spurious_noise_blip_is_discarded(tmp_path: Path) -> None:
    # An onset shorter than min_speech_seconds followed by silence yields no segment.
    out = tmp_path / "blip.wav"
    duration = _run([SILENCE] * 3 + [SPEECH] * 3 + [SILENCE] * 60, out)
    assert duration == 0.0
    assert not out.exists()
