import asyncio
import json

from app.core.config import Settings
from app.services.session_service import SessionService


def test_session_service_generates_artifacts(tmp_path):
    settings = Settings(
        samples_root=tmp_path / "samples",
        chunk_duration_seconds=0.05,
        max_chunks_per_session=2,
        session_poll_interval_seconds=0.01,
        recorder_backend="mock",
        transcriber_backend="mock",
    )
    service = SessionService(settings)

    async def scenario():
        await service.start("test01")
        await asyncio.sleep(0.15)
        return await service.stop("test01")

    session = asyncio.run(scenario())

    assert session.state.value == "stopped"
    assert session.chunk_count == 2
    assert session.word_count >= 2
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
    assert len(samples["words"]) == session.word_count
    assert samples["session_id"] == "test01"
