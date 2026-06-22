from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.services.transcriber import WordTiming


@dataclass(slots=True)
class CharTiming:
    char: str
    start: float
    end: float


class BaseAligner:
    """Produce real per-character timings through forced alignment.

    ``align_characters`` returns one ``list[CharTiming]`` per input word, aligned
    by index with ``words``. An empty outer list means alignment is unavailable
    (e.g. the backend is mock or whisperx is not installed) and the caller should
    fall back to even time-division.
    """

    def align_characters(self, audio_path: Path, words: list[WordTiming]) -> list[list[CharTiming]]:
        return []


class MockAligner(BaseAligner):
    pass


class WhisperXAligner(BaseAligner):
    # Each word is aligned as its own segment constrained to the word's audio
    # window, so whisperx's wav2vec2 forced alignment yields real character
    # boundaries inside that word instead of a uniform split.
    def __init__(
        self,
        *,
        model_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "es",
    ) -> None:
        self._available = False
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._language = (language or "es").lower()
        self._whisperx = None
        self._align_model = None
        self._align_metadata = None
        try:
            import whisperx  # type: ignore

            self._whisperx = whisperx
            self._available = True
        except ImportError:
            self._available = False

    def align_characters(self, audio_path: Path, words: list[WordTiming]) -> list[list[CharTiming]]:
        if not words or not self._available or self._whisperx is None:
            return []
        try:
            if self._align_model is None:
                self._align_model, self._align_metadata = self._whisperx.load_align_model(
                    language_code=self._language,
                    device=self._device,
                )

            audio = self._whisperx.load_audio(str(audio_path))
            # One segment per word so the returned chars map back to each word by
            # index without having to re-split on whitespace.
            segments = [
                {"text": word.word, "start": float(word.start), "end": float(word.end)}
                for word in words
            ]
            aligned = self._whisperx.align(
                segments,
                self._align_model,
                self._align_metadata,
                audio,
                self._device,
                return_char_alignments=True,
            )
            aligned_segments = aligned.get("segments", []) or []
            results: list[list[CharTiming]] = []
            for index, word in enumerate(words):
                raw_chars = []
                if index < len(aligned_segments):
                    raw_chars = aligned_segments[index].get("chars", []) or []
                results.append(_resolve_char_timings(raw_chars, word.start, word.end))
            return results
        except Exception:
            return []


def _resolve_char_timings(
    raw_chars: list[dict[str, object]],
    word_start: float,
    word_end: float,
) -> list[CharTiming]:
    # Keep only the visible characters and remember which raw timings whisperx
    # actually resolved; spaces and unresolved chars are filled in afterwards.
    chars: list[str] = []
    starts: list[float | None] = []
    ends: list[float | None] = []
    for item in raw_chars:
        char = str(item.get("char", ""))
        if not char.strip():
            continue
        chars.append(char)
        start = item.get("start")
        end = item.get("end")
        starts.append(None if start is None else float(start))
        ends.append(None if end is None else float(end))

    if not chars:
        return []

    span_start = float(word_start)
    span_end = max(span_start + 0.01, float(word_end))

    # Forward-fill missing starts from the previous known end (or the word start),
    # then back-fill missing ends from the next known start (or the word end), so
    # every character gets a monotonic, non-zero window even when whisperx left a
    # few timings unresolved.
    previous_end = span_start
    for i in range(len(chars)):
        if starts[i] is None:
            starts[i] = previous_end
        previous_end = ends[i] if ends[i] is not None else starts[i]

    next_start = span_end
    for i in range(len(chars) - 1, -1, -1):
        if ends[i] is None:
            ends[i] = next_start
        next_start = starts[i]

    timings: list[CharTiming] = []
    cursor = span_start
    for char, start, end in zip(chars, starts, ends):
        safe_start = max(span_start, cursor, float(start))
        safe_end = max(safe_start + 0.01, float(end))
        timings.append(CharTiming(char=char, start=round(safe_start, 3), end=round(safe_end, 3)))
        cursor = safe_end
    return timings


def create_aligner(
    backend: str,
    *,
    whisperx_model: str = "small",
    whisperx_device: str = "cpu",
    whisperx_compute_type: str = "int8",
    language: str = "es",
) -> BaseAligner:
    if backend == "whisperx":
        return WhisperXAligner(
            model_name=whisperx_model,
            device=whisperx_device,
            compute_type=whisperx_compute_type,
            language=language,
        )
    return MockAligner()
