from fastapi.testclient import TestClient
import time
import wave
from io import BytesIO

from app.api import routes
from app.core.config import Settings
from app.main import app
from app.services.session_service import SessionService


def test_start_stop_and_artifact_endpoints(tmp_path):
    test_service = SessionService(
        Settings(
            samples_root=tmp_path / "samples",
            chunk_duration_seconds=0.05,
            max_chunks_per_session=1,
            session_poll_interval_seconds=0.01,
            recorder_backend="mock",
            transcriber_backend="mock",
        )
    )
    routes.session_service = test_service
    client = TestClient(app)

    home_response = client.get("/")
    assert home_response.status_code == 200
    assert "Strudel" in home_response.text

    favicon_response = client.get("/favicon.ico")
    assert favicon_response.status_code in (200, 204)

    start_response = client.post("/start", json={"session_id": "api01"})
    assert start_response.status_code == 200

    stop_response = client.post("/stop", json={"session_id": "api01"})
    assert stop_response.status_code == 200
    assert stop_response.json()["message"] == "session stop requested"
    assert stop_response.json()["session"]["state"] == "processing"

    for _ in range(50):
        status_response = client.get("/status", params={"session_id": "api01"})
        assert status_response.status_code == 200
        session = status_response.json()["sessions"][0]
        if session["state"] == "stopped":
            break
        time.sleep(0.02)
    else:
        raise AssertionError("session did not finish background processing in time")

    script_response = client.get("/strudel/api01")
    assert script_response.status_code == 200

    samples_response = client.get("/samples/api01/manifest")
    assert samples_response.status_code == 200
    assert "words" in samples_response.json()

    sample_path = test_service._settings.samples_root / "api01" / "sentences" / "sentence_0001.wav"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample_path.write_bytes(b"RIFF$\x00\x00\x00WAVEfmt ")
    sample_file_response = client.get("/samples/api01/sentences/sentence_0001.wav")
    assert sample_file_response.status_code == 200
    assert sample_file_response.headers["content-type"].startswith("audio/wav")

    metadata_response = client.get("/metadata/api01")
    assert metadata_response.status_code == 200
    assert "chunks" in metadata_response.json()

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    assert metrics_response.json()["session_count"] >= 1


def test_start_rejects_invalid_session_id(tmp_path):
    test_service = SessionService(
        Settings(
            samples_root=tmp_path / "samples",
            recorder_backend="mock",
            transcriber_backend="mock",
        )
    )
    routes.session_service = test_service
    client = TestClient(app)

    response = client.post("/start", json={"session_id": "[object Object]"})
    assert response.status_code == 422


def test_runtime_endpoint_and_start_failure_expose_audio_diagnostics(tmp_path, monkeypatch):
    from app.services import session_service as session_service_module

    original_create_recorder = session_service_module.create_recorder

    def fake_create_recorder(backend, *, microphone_device=None):
        if backend == "microphone":
            raise RuntimeError("sounddevice import failed")
        return original_create_recorder(backend, microphone_device=microphone_device)

    monkeypatch.setattr(session_service_module, "create_recorder", fake_create_recorder)

    test_service = SessionService(
        Settings(
            samples_root=tmp_path / "samples",
            recorder_backend="microphone",
            transcriber_backend="mock",
        )
    )
    routes.session_service = test_service
    client = TestClient(app)

    runtime_response = client.get("/runtime")
    assert runtime_response.status_code == 200
    runtime_payload = runtime_response.json()
    assert runtime_payload["recorder"]["ready"] is False
    assert runtime_payload["recorder"]["startup_blocked"] is True

    start_response = client.post("/start", json={"session_id": "api02"})
    assert start_response.status_code == 503
    assert "Microphone recording is unavailable" in start_response.json()["detail"]


def _build_wav_bytes(*, duration_seconds: float = 0.1, sample_rate: int = 16000) -> bytes:
    frame_count = max(1, int(duration_seconds * sample_rate))
    with BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00\x00" * frame_count)
        return buffer.getvalue()


def test_browser_chunk_endpoint_accepts_uploaded_audio(tmp_path):
    test_service = SessionService(
        Settings(
            samples_root=tmp_path / "samples",
            recorder_backend="browser",
            transcriber_backend="mock",
        )
    )
    routes.session_service = test_service
    client = TestClient(app)

    start_response = client.post("/start", json={"session_id": "browserapi01"})
    assert start_response.status_code == 200

    chunk_response = client.post(
        "/browser/chunk",
        params={"session_id": "browserapi01"},
        content=_build_wav_bytes(),
        headers={"Content-Type": "audio/wav"},
    )
    assert chunk_response.status_code == 200
    assert chunk_response.json()["chunk_count"] == 1

    stop_response = client.post("/stop", json={"session_id": "browserapi01"})
    assert stop_response.status_code == 200
    assert stop_response.json()["session"]["state"] == "processing"
