from __future__ import annotations

import math
import re
import wave
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class WordTiming:
    word: str
    start: float
    end: float


class BaseTranscriber:
    def transcribe(self, audio_path: Path, *, chunk_index: int) -> list[WordTiming]:
        raise NotImplementedError


class MockTranscriber(BaseTranscriber):
    def __init__(self, seed_words: list[str]) -> None:
        self._seed_words = seed_words

    def transcribe(self, audio_path: Path, *, chunk_index: int) -> list[WordTiming]:
        duration = get_wav_duration(audio_path)
        words_per_chunk = 3
        token_count = min(words_per_chunk, max(1, len(self._seed_words)))
        step = duration / token_count
        words: list[WordTiming] = []
        for index in range(token_count):
            seed = self._seed_words[(chunk_index + index) % len(self._seed_words)]
            token = re.sub(r"[^a-zA-Z0-9_-]", "", seed).lower() or f"word{index + 1}"
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
    ) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError(
                "faster-whisper is not installed. Install it or use STRUDEL_TRANSCRIBER_BACKEND=mock."
            ) from exc
        self._model = WhisperModel(model_name, device=device, compute_type=compute_type)
        self._beam_size = max(1, beam_size)

    def transcribe(self, audio_path: Path, *, chunk_index: int) -> list[WordTiming]:
        segments, _ = self._model.transcribe(
            str(audio_path),
            word_timestamps=True,
            beam_size=self._beam_size,
        )
        words: list[WordTiming] = []
        for segment in segments:
            for word in getattr(segment, "words", []) or []:
                token = re.sub(r"[^a-zA-Z0-9_-]", "", word.word).lower()
                if not token:
                    continue
                start = 0.0 if word.start is None else float(word.start)
                end = max(start + 0.01, float(word.end) if word.end is not None else start + 0.25)
                words.append(WordTiming(word=token, start=round(start, 3), end=round(end, 3)))

        if words:
            return words
        return MockTranscriber(["fallback", "token", str(chunk_index)]).transcribe(
            audio_path,
            chunk_index=chunk_index,
        )


def create_transcriber(
    backend: str,
    seed_words: list[str],
    *,
    faster_whisper_model: str = "base",
    faster_whisper_device: str = "auto",
    faster_whisper_compute_type: str = "int8",
    faster_whisper_beam_size: int = 1,
) -> BaseTranscriber:
    if backend == "faster-whisper":
        return FasterWhisperTranscriber(
            model_name=faster_whisper_model,
            device=faster_whisper_device,
            compute_type=faster_whisper_compute_type,
            beam_size=faster_whisper_beam_size,
        )
    return MockTranscriber(seed_words)


def get_wav_duration(audio_path: Path) -> float:
    with wave.open(str(audio_path), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        sample_rate = wav_file.getframerate()
    return round(frame_count / sample_rate, 3)


def word_to_dict(word: WordTiming) -> dict[str, float | str]:
    return asdict(word)
