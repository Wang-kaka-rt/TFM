from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


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
        stop_requested: Callable[[], bool] | None = None,
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
        stop_requested: Callable[[], bool] | None = None,
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
        stop_requested: Callable[[], bool] | None = None,
    ) -> ChunkAudioInfo:
        frame_count = max(1, int(duration_seconds * sample_rate))
        block_size = min(2048, frame_count)
        captured_frames = 0
        captured_bytes = bytearray()

        with self._sounddevice.RawInputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            device=self._device,
            blocksize=block_size,
        ) as stream:
            while captured_frames < frame_count:
                if stop_requested is not None and stop_requested():
                    break

                frames_to_read = min(block_size, frame_count - captured_frames)
                buffer, _overflowed = stream.read(frames_to_read)
                captured_bytes.extend(buffer)
                captured_frames += frames_to_read

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(bytes(captured_bytes))

        return ChunkAudioInfo(
            duration_seconds=captured_frames / sample_rate,
            sample_rate=sample_rate,
            channels=channels,
            sample_width=2,
        )


def create_recorder(backend: str, *, microphone_device: int | None = None) -> BaseRecorder:
    if backend == "microphone":
        return MicrophoneRecorder(device=microphone_device)
    return MockToneRecorder()
