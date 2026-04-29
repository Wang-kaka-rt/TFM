from fastapi.testclient import TestClient

from app.api import routes
from app.core.config import Settings
from app.main import app
from app.services.session_service import SessionService


def test_start_reload_stop_and_artifact_endpoints(tmp_path):
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

    reload_response = client.post("/reload", json={"session_id": "api01"})
    assert reload_response.status_code == 200

    script_response = client.get("/strudel/api01")
    assert script_response.status_code == 200

    samples_response = client.get("/samples/api01/manifest")
    assert samples_response.status_code == 200
    assert "words" in samples_response.json()

    metadata_response = client.get("/metadata/api01")
    assert metadata_response.status_code == 200
    assert "chunks" in metadata_response.json()

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    assert metrics_response.json()["session_count"] >= 1
