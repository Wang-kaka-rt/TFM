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
    # Streaming silence-based segmentation (microphone backend only). When enabled,
    # audio is sliced at natural pauses via an RMS energy gate instead of fixed
    # `chunk_duration_seconds` windows, so words/sentences are not cut mid-utterance.
    # Falls back to fixed-window slicing for the mock/browser backends.
    streaming_segmentation: bool = True
    segment_block_seconds: float = 0.03          # analysis frame size
    segment_silence_rms: float = 0.008           # RMS below this counts as silence
    segment_start_rms: float = 0.018             # onset threshold (hysteresis vs silence)
    segment_hangover_seconds: float = 0.6        # trailing silence needed to close a segment
    segment_max_duration_seconds: float = 8.0    # hard cap that bounds latency
    segment_min_speech_seconds: float = 0.2      # ignore blips shorter than this
    segment_preroll_seconds: float = 0.25        # audio kept before detected speech onset
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
    # Anti-hallucination guards for noisy input. faster-whisper fabricates words
    # on pure-noise chunks unless these thresholds reject low-confidence audio.
    faster_whisper_vad_filter: bool = True
    faster_whisper_no_speech_threshold: float = 0.6
    faster_whisper_log_prob_threshold: float = -1.0
    faster_whisper_compression_ratio_threshold: float = 2.4
    # Drop transcribed words whose ASR probability is below this value. 0.0 keeps
    # every word (default, mock-safe); raise to ~0.45 in noisy environments.
    word_min_probability: float = 0.0
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
    # Pre-ASR noise reduction. Disabled by default so existing behavior is
    # unchanged; enable with backend 'noisereduce' for noisy environments.
    enable_denoise: bool = False
    denoise_backend: str = "null"
    denoise_prop_decrease: float = 0.8
    denoise_stationary: bool = False
    # Energy gate: skip whole chunks whose RMS amplitude (0..1) is below this
    # value. 0.0 disables the gate (default); ~0.005 drops near-silent chunks.
    enable_energy_gate: bool = False
    min_chunk_rms: float = 0.0
    phrase_group_size: int = 2
    enable_refinement: bool = False
    refinement_backend: str = "mock"
    whisperx_model: str = "small"
    whisperx_device: str = "cpu"
    whisperx_compute_type: str = "int8"
    mock_transcript_words: list[str] = Field(default_factory=list)

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
