import sys
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]
PYTHON_SERVICE_ROOT = Path(__file__).resolve().parents[2]

def resolve_env_files() -> tuple[str, ...]:
    # Only load project-local env files so desktop/user overrides cannot
    # silently change recording behavior outside the repository.
    candidates: list[Path] = [
        PYTHON_SERVICE_ROOT / ".env",
        Path.cwd() / ".env",
    ]

    unique_files: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = str(candidate.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_files.append(resolved)
    return tuple(unique_files)


ENV_FILES = resolve_env_files()


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
    max_chunks_per_session: int = 0
    enable_phrase_and_sentence_exports: bool = True
    strudel_base_url: str = "http://127.0.0.1:8787"
    session_poll_interval_seconds: float = 0.05
    transcriber_backend: str = "mock"
    faster_whisper_model: str = "base"
    faster_whisper_device: str = "auto"
    faster_whisper_compute_type: str = "int8"
    faster_whisper_beam_size: int = 5
    transcriber_language: str | None = "es"
    transcriber_initial_prompt: str = (
        "Vocabulario en español para nombres de sonidos: hola, bien, bueno, consejo, familia, "
        "hijos, problema, también, tengo, todos, ritmo, voz, muestra, frase, pulso, eco."
    )
    transcriber_hotwords: str = "hola bien bueno consejo familia hijos problema también tengo todos"
    vad_backend: str = "mock"
    enable_vad: bool = True
    min_word_duration_seconds: float = 0.04
    silero_sample_rate: int = 16_000
    silero_speech_threshold: float = 0.5
    phrase_group_size: int = 2
    enable_refinement: bool = False
    refinement_backend: str = "mock"
    whisperx_model: str = "small"
    whisperx_device: str = "cpu"
    whisperx_compute_type: str = "int8"
    mock_transcript_words: list[str] = Field(
        default_factory=lambda: [
            "hola",
            "ritmo",
            "voz",
            "muestra",
            "frase",
            "pulso",
            "eco",
            "grave",
        ]
    )

    @model_validator(mode="after")
    def resolve_paths(self) -> "Settings":
        if not self.samples_root.is_absolute():
            self.samples_root = (PYTHON_SERVICE_ROOT / self.samples_root).resolve()
        return self

    model_config = SettingsConfigDict(
        env_prefix="STRUDEL_",
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
    )


settings = Settings()
