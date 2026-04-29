from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "Strudel Voice Backend"
    app_version: str = "0.1.0"
    api_prefix: str = ""
    host: str = "127.0.0.1"
    port: int = 8787
    allowed_origins: list[str] = [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "https://strudel.cc",
    ]
    samples_root: Path = PROJECT_ROOT / "samples"
    chunk_duration_seconds: float = 2.5
    sample_rate: int = 16_000
    channels: int = 1
    recorder_backend: str = "mock"
    microphone_device: int | None = None
    mock_chunk_prefix: str = "chunk"
    max_chunks_per_session: int = 4
    enable_phrase_and_sentence_exports: bool = True
    strudel_base_url: str = "http://127.0.0.1:8787"
    session_poll_interval_seconds: float = 0.05
    transcriber_backend: str = "mock"
    faster_whisper_model: str = "base"
    faster_whisper_device: str = "auto"
    faster_whisper_compute_type: str = "int8"
    faster_whisper_beam_size: int = 1
    vad_backend: str = "mock"
    enable_vad: bool = True
    min_word_duration_seconds: float = 0.04
    phrase_group_size: int = 2
    enable_refinement: bool = False
    refinement_backend: str = "mock"
    mock_transcript_words: list[str] = Field(
        default_factory=lambda: [
            "strudel",
            "voice",
            "sample",
            "loop",
            "phrase",
            "pulse",
            "echo",
            "groove",
        ]
    )

    model_config = SettingsConfigDict(
        env_prefix="STRUDEL_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
