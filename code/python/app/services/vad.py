from __future__ import annotations

from pathlib import Path

from app.services.transcriber import WordTiming


class BaseVoiceActivityDetector:
    def filter_words(self, words: list[WordTiming], audio_path: Path | None = None) -> list[WordTiming]:
        raise NotImplementedError


class MockVoiceActivityDetector(BaseVoiceActivityDetector):
    def __init__(self, min_word_duration_seconds: float) -> None:
        self._min_word_duration = min_word_duration_seconds

    def filter_words(self, words: list[WordTiming], audio_path: Path | None = None) -> list[WordTiming]:
        filtered = [
            word
            for word in words
            if (word.end - word.start) >= self._min_word_duration and word.word.strip()
        ]
        return filtered if filtered else words


class SileroVoiceActivityDetector(BaseVoiceActivityDetector):
    def __init__(
        self,
        min_word_duration_seconds: float,
        *,
        sample_rate: int = 16_000,
        speech_threshold: float = 0.5,
    ) -> None:
        self._fallback = MockVoiceActivityDetector(min_word_duration_seconds)
        self._sample_rate = sample_rate
        self._speech_threshold = speech_threshold
        self._model = None
        self._read_audio = None
        self._get_speech_timestamps = None
        try:
            from silero_vad import get_speech_timestamps, load_silero_vad, read_audio  # type: ignore

            self._model = load_silero_vad()
            self._read_audio = read_audio
            self._get_speech_timestamps = get_speech_timestamps
        except ImportError:
            self._model = None

    def filter_words(self, words: list[WordTiming], audio_path: Path | None = None) -> list[WordTiming]:
        if not words:
            return []
        if self._model is None or self._read_audio is None or self._get_speech_timestamps is None:
            return self._fallback.filter_words(words, audio_path)
        if audio_path is None:
            return self._fallback.filter_words(words, audio_path)

        try:
            audio = self._read_audio(str(audio_path), sampling_rate=self._sample_rate)
            speech_timestamps = self._get_speech_timestamps(
                audio,
                self._model,
                sampling_rate=self._sample_rate,
                threshold=self._speech_threshold,
            )
        except Exception:
            return self._fallback.filter_words(words, audio_path)

        if not speech_timestamps:
            return []

        speech_windows = [
            (
                float(timestamp["start"]) / self._sample_rate,
                float(timestamp["end"]) / self._sample_rate,
            )
            for timestamp in speech_timestamps
        ]
        retained = [word for word in words if _overlap_speech(word, speech_windows)]
        return self._fallback.filter_words(retained, audio_path) if retained else []


def _overlap_speech(word: WordTiming, speech_windows: list[tuple[float, float]]) -> bool:
    start = word.start
    end = max(word.start + 0.01, word.end)
    for speech_start, speech_end in speech_windows:
        if end <= speech_start:
            continue
        if start >= speech_end:
            continue
        return True
    return False


def create_vad(
    backend: str,
    min_word_duration_seconds: float,
    *,
    silero_sample_rate: int = 16_000,
    silero_speech_threshold: float = 0.5,
) -> BaseVoiceActivityDetector:
    if backend == "silero":
        return SileroVoiceActivityDetector(
            min_word_duration_seconds,
            sample_rate=silero_sample_rate,
            speech_threshold=silero_speech_threshold,
        )
    return MockVoiceActivityDetector(min_word_duration_seconds)
