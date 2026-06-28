from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from app.services.session_service import export_wav_slice


def _write_tone(path: Path, duration_seconds: float, sample_rate: int = 16_000) -> None:
    frame_count = int(duration_seconds * sample_rate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frame_count):
            value = int(0.5 * 32767 * math.sin(2.0 * math.pi * 220 * index / sample_rate))
            wav_file.writeframes(struct.pack("<h", value))


def _duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        return wav_file.getnframes() / wav_file.getframerate()


def test_padding_widens_the_slice_on_both_sides(tmp_path):
    source = tmp_path / "src.wav"
    _write_tone(source, duration_seconds=2.0)

    plain = tmp_path / "plain.wav"
    padded = tmp_path / "padded.wav"
    assert export_wav_slice(source, plain, 0.5, 1.0, pad_seconds=0.0)
    assert export_wav_slice(source, padded, 0.5, 1.0, pad_seconds=0.1)

    # 0.5s base window vs 0.5s + 2*0.1s padding window.
    assert _duration(plain) == 0.5
    assert abs(_duration(padded) - 0.7) < 0.01


def test_padding_clamps_to_source_bounds(tmp_path):
    source = tmp_path / "src.wav"
    _write_tone(source, duration_seconds=1.0)

    clip = tmp_path / "clip.wav"
    # Window touches both ends; padding must not read before 0 or past the source.
    assert export_wav_slice(source, clip, 0.0, 1.0, pad_seconds=0.2)
    assert _duration(clip) <= 1.0 + 1e-3
