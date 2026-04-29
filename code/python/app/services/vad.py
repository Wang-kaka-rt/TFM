from __future__ import annotations

from app.services.transcriber import WordTiming


class BaseVoiceActivityDetector:
    def filter_words(self, words: list[WordTiming]) -> list[WordTiming]:
        raise NotImplementedError


class MockVoiceActivityDetector(BaseVoiceActivityDetector):
    def __init__(self, min_word_duration_seconds: float) -> None:
        self._min_word_duration = min_word_duration_seconds

    def filter_words(self, words: list[WordTiming]) -> list[WordTiming]:
        filtered = [
            word
            for word in words
            if (word.end - word.start) >= self._min_word_duration and word.word.strip()
        ]
        return filtered if filtered else words


class SileroVoiceActivityDetector(BaseVoiceActivityDetector):
    def __init__(self, min_word_duration_seconds: float) -> None:
        self._fallback = MockVoiceActivityDetector(min_word_duration_seconds)
        self._model_loaded = False
        try:
            import torch  # noqa: F401 # pragma: no cover
            self._model_loaded = True
        except ImportError:
            self._model_loaded = False

    def filter_words(self, words: list[WordTiming]) -> list[WordTiming]:
        # Full frame-level silero gating can be plugged in here later.
        # For now we provide a deterministic fallback so the pipeline remains usable.
        return self._fallback.filter_words(words)


def create_vad(backend: str, min_word_duration_seconds: float) -> BaseVoiceActivityDetector:
    if backend == "silero":
        return SileroVoiceActivityDetector(min_word_duration_seconds)
    return MockVoiceActivityDetector(min_word_duration_seconds)
