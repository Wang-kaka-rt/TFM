from __future__ import annotations

import math
import re
import wave
from dataclasses import asdict, dataclass
from pathlib import Path


SPANISH_TOKEN_CORRECTIONS = {
    "ula": "hola",
    "ola": "hola",
}


@dataclass(slots=True)
class WordTiming:
    word: str
    start: float
    end: float
    probability: float = 1.0


class BaseTranscriber:
    def transcribe(self, audio_path: Path, *, chunk_index: int) -> list[WordTiming]:
        raise NotImplementedError


class MockTranscriber(BaseTranscriber):
    def __init__(self, seed_words: list[str]) -> None:
        self._seed_words = seed_words

    def transcribe(self, audio_path: Path, *, chunk_index: int) -> list[WordTiming]:
        if not self._seed_words:
            return []
        duration = get_wav_duration(audio_path)
        words_per_chunk = 3
        token_count = min(words_per_chunk, max(1, len(self._seed_words)))
        step = duration / token_count
        words: list[WordTiming] = []
        for index in range(token_count):
            seed = self._seed_words[(chunk_index + index) % len(self._seed_words)]
            token = clean_token(seed) or f"palabra{index + 1}"
            start = round(index * step, 3)
            end = round(duration if index == token_count - 1 else (index + 1) * step, 3)
            words.append(WordTiming(word=token, start=start, end=end))
        return words


class FasterWhisperTranscriber(BaseTranscriber):
    def __init__(
        self,
        model_name: str = "base",
        *,
        device: str = "auto",
        compute_type: str = "int8",
        beam_size: int = 1,
        language: str | None = "es",
        initial_prompt: str | None = None,
        hotwords: str | None = None,
        fallback_words: list[str] | None = None,
        vad_filter: bool = True,
        no_speech_threshold: float = 0.6,
        log_prob_threshold: float = -1.0,
        compression_ratio_threshold: float = 2.4,
    ) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError(
                "faster-whisper is not installed. Install it or use STRUDEL_TRANSCRIBER_BACKEND=mock."
            ) from exc
        self._model = WhisperModel(model_name, device=device, compute_type=compute_type)
        self._beam_size = max(1, beam_size)
        self._language = language or None
        self._initial_prompt = initial_prompt or None
        self._hotwords = hotwords or None
        self._fallback_words = fallback_words or ["hola", "ritmo", "voz"]
        self._vad_filter = vad_filter
        self._no_speech_threshold = no_speech_threshold
        self._log_prob_threshold = log_prob_threshold
        self._compression_ratio_threshold = compression_ratio_threshold

    def transcribe(self, audio_path: Path, *, chunk_index: int) -> list[WordTiming]:
        segments, _ = self._model.transcribe(
            str(audio_path),
            word_timestamps=True,
            beam_size=self._beam_size,
            language=self._language,
            initial_prompt=self._initial_prompt,
            hotwords=self._hotwords,
            vad_filter=self._vad_filter,
            no_speech_threshold=self._no_speech_threshold,
            log_prob_threshold=self._log_prob_threshold,
            compression_ratio_threshold=self._compression_ratio_threshold,
        )
        words: list[WordTiming] = []
        for segment in segments:
            for word in getattr(segment, "words", []) or []:
                token = clean_token(word.word)
                if not token:
                    continue
                start = 0.0 if word.start is None else float(word.start)
                end = max(start + 0.01, float(word.end) if word.end is not None else start + 0.25)
                probability = 1.0 if getattr(word, "probability", None) is None else float(word.probability)
                words.append(
                    WordTiming(
                        word=token,
                        start=round(start, 3),
                        end=round(end, 3),
                        probability=round(probability, 4),
                    )
                )

        # Silence / non-speech chunks legitimately yield no words. Return them as
        # empty instead of fabricating mock words, otherwise a microphone that is
        # not actually capturing audio would be masked by fake transcripts.
        return words


def create_transcriber(
    backend: str,
    seed_words: list[str],
    *,
    faster_whisper_model: str = "base",
    faster_whisper_device: str = "auto",
    faster_whisper_compute_type: str = "int8",
    faster_whisper_beam_size: int = 1,
    transcriber_language: str | None = "es",
    transcriber_initial_prompt: str | None = None,
    transcriber_hotwords: str | None = None,
    faster_whisper_vad_filter: bool = True,
    faster_whisper_no_speech_threshold: float = 0.6,
    faster_whisper_log_prob_threshold: float = -1.0,
    faster_whisper_compression_ratio_threshold: float = 2.4,
) -> BaseTranscriber:
    if backend == "faster-whisper":
        return FasterWhisperTranscriber(
            model_name=faster_whisper_model,
            device=faster_whisper_device,
            compute_type=faster_whisper_compute_type,
            beam_size=faster_whisper_beam_size,
            language=transcriber_language,
            initial_prompt=transcriber_initial_prompt,
            hotwords=transcriber_hotwords,
            fallback_words=seed_words,
            vad_filter=faster_whisper_vad_filter,
            no_speech_threshold=faster_whisper_no_speech_threshold,
            log_prob_threshold=faster_whisper_log_prob_threshold,
            compression_ratio_threshold=faster_whisper_compression_ratio_threshold,
        )
    return MockTranscriber(seed_words)


def clean_token(value: str) -> str:
    token = re.sub(r"_+", "_", re.sub(r"[^\w-]+", "_", value, flags=re.UNICODE)).strip("_").lower()
    return SPANISH_TOKEN_CORRECTIONS.get(token, token)


def get_wav_duration(audio_path: Path) -> float:
    with wave.open(str(audio_path), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        sample_rate = wav_file.getframerate()
    return round(frame_count / sample_rate, 3)


def word_to_dict(word: WordTiming) -> dict[str, float | str]:
    return asdict(word)
