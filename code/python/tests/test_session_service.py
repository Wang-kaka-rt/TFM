import asyncio
import json
import wave
from io import BytesIO

import pytest

from app.core.config import Settings
from app.services import recorder as recorder_module
from app.services.session_service import SessionService
from app.services.transcriber import MockTranscriber, clean_token


def test_relative_samples_root_resolves_from_python_service_dir():
    settings = Settings(samples_root="../../samples")

    assert settings.samples_root.is_absolute()
    assert settings.samples_root.name == "samples"
    assert settings.samples_root.parent.name == "TFM"


def test_spanish_tokens_are_used_for_mock_and_cleaning(tmp_path):
    audio_path = tmp_path / "spanish.wav"
    service = SessionService(
        Settings(
            samples_root=tmp_path / "samples",
            recorder_backend="mock",
            transcriber_backend="mock",
        )
    )
    service._recorder.record_chunk(
        audio_path,
        duration_seconds=0.05,
        sample_rate=16_000,
        channels=1,
        chunk_index=1,
    )

    words = MockTranscriber(["hola", "niño", "canción"]).transcribe(audio_path, chunk_index=0)

    assert [word.word for word in words] == ["hola", "niño", "canción"]
    assert clean_token(" ¡Hola, canción! ") == "hola_canción"
    assert clean_token("ula") == "hola"
    assert clean_token("ola") == "hola"


def test_session_service_generates_artifacts(tmp_path):
    settings = Settings(
        samples_root=tmp_path / "samples",
        chunk_duration_seconds=0.05,
        max_chunks_per_session=2,
        session_poll_interval_seconds=0.01,
        recorder_backend="mock",
        transcriber_backend="mock",
        mock_transcript_words=["hola", "ritmo", "voz"],
    )
    service = SessionService(settings)

    async def scenario():
        await service.start("test01")
        await asyncio.sleep(0.15)
        stop_response = await service.stop("test01")
        for _ in range(50):
            session = service.get("test01")
            if session is not None and session.state.value == "stopped":
                return stop_response, session
            await asyncio.sleep(0.02)
        raise AssertionError("session did not finish stopping in time")

    stop_response, session = asyncio.run(scenario())

    assert stop_response.state.value == "processing"
    assert session.state.value == "stopped"
    assert session.chunk_count == 2
    assert session.word_count >= 2
    assert session.letter_count >= session.word_count
    assert session.metadata_path is not None
    assert session.samples_path is not None
    assert session.strudel_script_path is not None

    metadata_path = tmp_path / "samples" / "test01" / "metadata.json"
    samples_path = tmp_path / "samples" / "test01" / "samples.json"
    strudel_script_path = tmp_path / "samples" / "test01" / "strudel.js"

    assert metadata_path.exists()
    assert samples_path.exists()
    assert strudel_script_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    samples = json.loads(samples_path.read_text(encoding="utf-8"))

    assert len(metadata["chunks"]) == 2
    assert "processing_latency_seconds" in metadata["chunks"][0]
    assert "raw_word_count" in metadata["chunks"][0]
    assert "exported_word_count" in metadata["chunks"][0]
    assert len(samples["words"]) == session.word_count
    assert len(samples["letters"]) == session.letter_count
    assert samples["session_id"] == "test01"
    metrics = service.get_metrics()
    assert "avg_chunk_latency_ms" in metrics
    assert "p95_chunk_latency_ms" in metrics
    assert "word_retention_percent" in metrics
    assert "slice_success_rate_percent" in metrics


def test_session_service_blocks_start_when_microphone_backend_init_fails(tmp_path, monkeypatch):
    from app.services import session_service as session_service_module

    original_create_recorder = session_service_module.create_recorder

    def fake_create_recorder(backend, *, microphone_device=None):
        if backend == "microphone":
            raise RuntimeError("PortAudio runtime is missing")
        return original_create_recorder(backend, microphone_device=microphone_device)

    monkeypatch.setattr(session_service_module, "create_recorder", fake_create_recorder)

    service = SessionService(
        Settings(
            samples_root=tmp_path / "samples",
            recorder_backend="microphone",
            transcriber_backend="mock",
        )
    )

    with pytest.raises(RuntimeError, match="Microphone recording is unavailable"):
        asyncio.run(service.start("blocked01"))

    runtime = service.get_runtime_diagnostics()
    assert runtime["recorder"]["ready"] is False
    assert runtime["recorder"]["startup_blocked"] is True
    assert "PortAudio runtime is missing" in str(runtime["recorder"]["init_error"])


def test_microphone_diagnostics_falls_back_to_first_available_device(monkeypatch):
    class FakeSoundDevice:
        default = type("Default", (), {"device": (-1, -1)})()

        @staticmethod
        def query_devices():
            return [
                {"name": "Speakers", "max_input_channels": 0, "default_samplerate": 48000},
                {"name": "USB Mic", "max_input_channels": 1, "default_samplerate": 16000},
                {"name": "Webcam Mic", "max_input_channels": 2, "default_samplerate": 48000},
            ]

        @staticmethod
        def check_input_settings(*, device, samplerate, channels, dtype):
            assert device == 1
            assert samplerate == 16000
            assert channels == 1
            assert dtype == "int16"

    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "sounddevice":
            return FakeSoundDevice
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    diagnostics = recorder_module.get_microphone_diagnostics(
        device=None,
        sample_rate=16000,
        channels=1,
    )

    assert diagnostics["input_device_count"] == 2
    assert diagnostics["default_input_device"] is None
    assert diagnostics["selected_input_device"]["name"] == "USB Mic"
    assert diagnostics["selected_input_device_source"] == "first_available"
    assert diagnostics["input_settings_ok"] is True


def test_microphone_diagnostics_reports_portaudio_load_error(monkeypatch):
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "sounddevice":
            raise OSError("cannot load library 'libportaudioarm64.dll': error 0x7e")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    diagnostics = recorder_module.get_microphone_diagnostics(
        device=None,
        sample_rate=16000,
        channels=1,
    )

    assert diagnostics["library_available"] is False
    assert "PortAudio runtime could not be loaded" in str(diagnostics["error"])
    assert "libportaudioarm64.dll" in str(diagnostics["import_error"])


def _build_wav_bytes(*, duration_seconds: float = 0.1, sample_rate: int = 16000) -> bytes:
    frame_count = max(1, int(duration_seconds * sample_rate))
    with BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00\x00" * frame_count)
        return buffer.getvalue()


def test_browser_recorder_backend_accepts_uploaded_chunks(tmp_path):
    service = SessionService(
        Settings(
            samples_root=tmp_path / "samples",
            recorder_backend="browser",
            transcriber_backend="mock",
            mock_transcript_words=["hola", "ritmo", "voz"],
        )
    )

    async def scenario():
        await service.start("browser01")
        result = await service.submit_browser_chunk("browser01", _build_wav_bytes())
        stop_response = await service.stop("browser01")
        for _ in range(50):
            session = service.get("browser01")
            if session is not None and session.state.value == "stopped":
                return result, stop_response, session
            await asyncio.sleep(0.02)
        raise AssertionError("browser session did not finish stopping in time")

    upload_result, stop_response, session = asyncio.run(scenario())

    assert upload_result["chunk_index"] == 1
    assert upload_result["chunk_count"] == 1
    assert stop_response.state.value == "processing"
    assert session.state.value == "stopped"
    assert session.chunk_count == 1
    assert session.word_count >= 1
