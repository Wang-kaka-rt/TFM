import asyncio
import json

from app.core.config import Settings
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
