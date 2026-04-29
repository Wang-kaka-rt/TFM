from __future__ import annotations

from pathlib import Path

from app.services.transcriber import WordTiming


class BaseRefiner:
    def refine(self, audio_path: Path, words: list[WordTiming]) -> list[WordTiming]:
        raise NotImplementedError


class MockRefiner(BaseRefiner):
    def refine(self, audio_path: Path, words: list[WordTiming]) -> list[WordTiming]:
        return words


class WhisperXRefiner(BaseRefiner):
    def __init__(self) -> None:
        self._available = True
        try:
            import whisperx  # noqa: F401 # pragma: no cover
        except ImportError:
            self._available = False

    def refine(self, audio_path: Path, words: list[WordTiming]) -> list[WordTiming]:
        # Placeholder for async force-alignment.
        # Falls back to original timings when whisperx is not available.
        return words


def create_refiner(backend: str) -> BaseRefiner:
    if backend == "whisperx":
        return WhisperXRefiner()
    return MockRefiner()
