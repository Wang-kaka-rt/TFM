from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(slots=True)
class ChunkAudioInfo:
    duration_seconds: float
    sample_rate: int
    channels: int
    sample_width: int


class BaseRecorder:
    def validate_input(self, *, sample_rate: int, channels: int) -> None:
        return None

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


class BrowserRecorder(BaseRecorder):
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
        raise RuntimeError("BrowserRecorder does not support local record_chunk calls.")


class MicrophoneRecorder(BaseRecorder):
    def __init__(self, *, device: int | None = None) -> None:
        self._sounddevice = _load_sounddevice_module()
        self._device = device

    def validate_input(self, *, sample_rate: int, channels: int) -> None:
        selected_device = self._resolve_selected_device()
        if selected_device is None:
            raise RuntimeError(
                "No usable input microphone is available. Check Windows microphone permission and audio device settings."
            )

        try:
            device_info = self._sounddevice.query_devices(selected_device, "input")
            max_input_channels = int(device_info["max_input_channels"])
        except Exception as exc:
            raise RuntimeError(f"Failed to inspect input device {selected_device}: {exc}") from exc

        if max_input_channels < channels:
            raise RuntimeError(
                f"Input device {selected_device} only supports {max_input_channels} input channels; "
                f"the app requires {channels}."
            )

        try:
            self._sounddevice.check_input_settings(
                device=selected_device,
                samplerate=sample_rate,
                channels=channels,
                dtype="int16",
            )
        except Exception as exc:
            raise RuntimeError(
                "The selected microphone is not compatible with the current recording settings "
                f"(device={selected_device}, sample_rate={sample_rate}, channels={channels}): {exc}"
            ) from exc

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

    def _resolve_selected_device(self) -> int | None:
        if self._device is not None:
            return self._device

        input_devices = _list_input_devices(self._sounddevice.query_devices())
        default_input_device = _normalize_default_input_index(getattr(self._sounddevice.default, "device", None))
        return _pick_input_device(default_input_device, input_devices)


def _build_device_summary(index: int, info: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": index,
        "name": str(info.get("name") or f"Device {index}"),
        "max_input_channels": int(info.get("max_input_channels") or 0),
        "default_samplerate": float(info.get("default_samplerate") or 0.0),
    }


def _list_input_devices(all_devices: Any) -> list[dict[str, Any]]:
    input_devices: list[dict[str, Any]] = []
    for index, info in enumerate(all_devices):
        if int(info.get("max_input_channels") or 0) <= 0:
            continue
        input_devices.append(_build_device_summary(index, info))
    return input_devices


def _normalize_default_input_index(default_pair: Any) -> int | None:
    if isinstance(default_pair, (list, tuple)) and default_pair:
        return None if default_pair[0] in (None, -1) else int(default_pair[0])
    if isinstance(default_pair, int):
        return None if default_pair == -1 else default_pair
    return None


def _pick_input_device(default_input_index: int | None, input_devices: list[dict[str, Any]]) -> int | None:
    if default_input_index is not None:
        for item in input_devices:
            if item["index"] == default_input_index:
                return default_input_index
    if input_devices:
        return int(input_devices[0]["index"])
    return None


def _format_sounddevice_runtime_error(exc: BaseException) -> str:
    details = str(exc).strip() or exc.__class__.__name__
    message = f"PortAudio runtime could not be loaded: {details}"
    if "libportaudioarm64.dll" in details or "libportaudio64bit.dll" in details:
        message += (
            ". This usually means the packaged PortAudio DLL does not match the target "
            "Windows architecture or a required runtime dependency is missing."
        )
    return message


def _load_sounddevice_module() -> Any:
    try:
        import sounddevice as sd  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on local hardware setup
        raise RuntimeError(
            "sounddevice is required for microphone recording. "
            "Install it or switch STRUDEL_RECORDER_BACKEND to 'mock'."
        ) from exc
    except OSError as exc:  # pragma: no cover - depends on local hardware setup
        raise RuntimeError(_format_sounddevice_runtime_error(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime protection
        raise RuntimeError(f"sounddevice failed to initialize: {exc}") from exc
    return sd


def get_wav_audio_info(audio_path: Path) -> ChunkAudioInfo:
    with wave.open(str(audio_path), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
    return ChunkAudioInfo(
        duration_seconds=0.0 if sample_rate <= 0 else frame_count / sample_rate,
        sample_rate=sample_rate,
        channels=channels,
        sample_width=sample_width,
    )


def get_microphone_diagnostics(
    *,
    device: int | None,
    sample_rate: int,
    channels: int,
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "library": "sounddevice",
        "library_available": False,
        "input_devices": [],
        "input_device_count": 0,
        "default_input_device": None,
        "selected_input_device": None,
        "selected_input_device_source": None,
        "input_settings_ok": False,
        "error": None,
    }
    try:
        sd = _load_sounddevice_module()
    except RuntimeError as exc:
        diagnostics["error"] = str(exc)
        diagnostics["import_error"] = str(exc)
        return diagnostics

    diagnostics["library_available"] = True
    try:
        all_devices = sd.query_devices()
    except Exception as exc:
        diagnostics["error"] = f"Failed to enumerate audio input devices: {exc}"
        return diagnostics

    input_devices = _list_input_devices(all_devices)
    diagnostics["input_devices"] = input_devices
    diagnostics["input_device_count"] = len(input_devices)

    default_input_index = _normalize_default_input_index(getattr(sd.default, "device", None))
    selected_index = (
        int(device) if device is not None else _pick_input_device(default_input_index, input_devices)
    )
    device_by_index = {item["index"]: item for item in input_devices}
    diagnostics["default_input_device"] = device_by_index.get(default_input_index)
    diagnostics["selected_input_device"] = device_by_index.get(selected_index)
    diagnostics["selected_input_device_source"] = (
        "configured"
        if device is not None
        else "default"
        if selected_index == default_input_index and selected_index is not None
        else "first_available"
        if selected_index is not None
        else None
    )

    if selected_index is None:
        diagnostics["error"] = (
            "No usable input microphone is available. Connect a microphone and allow microphone access."
        )
        return diagnostics

    try:
        sd.check_input_settings(
            device=selected_index,
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
        )
    except Exception as exc:
        diagnostics["error"] = (
            "The selected microphone failed the recording compatibility check "
            f"(device={selected_index}, sample_rate={sample_rate}, channels={channels}): {exc}"
        )
        return diagnostics

    diagnostics["input_settings_ok"] = True
    return diagnostics


def create_recorder(backend: str, *, microphone_device: int | None = None) -> BaseRecorder:
    if backend == "browser":
        return BrowserRecorder()
    if backend == "microphone":
        return MicrophoneRecorder(device=microphone_device)
    return MockToneRecorder()
