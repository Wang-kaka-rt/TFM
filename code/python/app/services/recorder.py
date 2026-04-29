from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ChunkAudioInfo:
    duration_seconds: float
    sample_rate: int
    channels: int
    sample_width: int


class BaseRecorder:
    def record_chunk(
        self,
        output_path: Path,
        *,
        duration_seconds: float,
        sample_rate: int,
        channels: int,
        chunk_index: int,
    ) -> ChunkAudioInfo:
        raise NotImplementedError


class MockToneRecorder(BaseRecorder):
    def record_chunk(
        self,
        output_path: Path,
        *,
        duration_seconds: float,
        sample_rate: int,
        channels: int,
        chunk_index: int,
    ) -> ChunkAudioInfo:
        frame_count = max(1, int(duration_seconds * sample_rate))
        frequency = 220 + (chunk_index % 5) * 55
        amplitude = 0.25

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            for frame_index in range(frame_count):
                value = int(
                    amplitude
                    * 32767
                    * math.sin((2.0 * math.pi * frequency * frame_index) / sample_rate)
                )
                packed = struct.pack("<h", value)
                wav_file.writeframesraw(packed * channels)

        return ChunkAudioInfo(
            duration_seconds=frame_count / sample_rate,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=2,
        )


class MicrophoneRecorder(BaseRecorder):
    def __init__(self, *, device: int | None = None) -> None:
        try:
            import sounddevice as sd  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on local hardware setup
            raise RuntimeError(
                "sounddevice is required for microphone recording. "
                "Install it or switch STRUDEL_RECORDER_BACKEND to 'mock'."
            ) from exc

        self._sounddevice = sd
        self._device = device

    def record_chunk(
        self,
        output_path: Path,
        *,
        duration_seconds: float,
        sample_rate: int,
        channels: int,
        chunk_index: int,
    ) -> ChunkAudioInfo:
        frame_count = max(1, int(duration_seconds * sample_rate))
        recording = self._sounddevice.rec(
            frame_count,
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            device=self._device,
        )
        self._sounddevice.wait()

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(recording.tobytes())

        return ChunkAudioInfo(
            duration_seconds=frame_count / sample_rate,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=2,
        )


def create_recorder(backend: str, *, microphone_device: int | None = None) -> BaseRecorder:
    if backend == "microphone":
        return MicrophoneRecorder(device=microphone_device)
    return MockToneRecorder()
