from __future__ import annotations

import re
from pathlib import Path

from app.services.transcriber import WordTiming


class BaseRefiner:
    def refine(self, audio_path: Path, words: list[WordTiming]) -> list[WordTiming]:
        raise NotImplementedError


class MockRefiner(BaseRefiner):
    def refine(self, audio_path: Path, words: list[WordTiming]) -> list[WordTiming]:
        return words


class WhisperXRefiner(BaseRefiner):
    def __init__(
        self,
        *,
        model_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self._available = False
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._whisperx = None
        self._asr_model = None
        try:
            import whisperx  # type: ignore

            self._whisperx = whisperx
            self._available = True
        except ImportError:
            self._available = False

    def refine(self, audio_path: Path, words: list[WordTiming]) -> list[WordTiming]:
        if not words or not self._available or self._whisperx is None:
            return words
        try:
            if self._asr_model is None:
                self._asr_model = self._whisperx.load_model(
                    self._model_name,
                    self._device,
                    compute_type=self._compute_type,
                )

            audio = self._whisperx.load_audio(str(audio_path))
            result = self._asr_model.transcribe(audio, batch_size=1)
            language = result.get("language") or "en"
            align_model, metadata = self._whisperx.load_align_model(
                language_code=language,
                device=self._device,
            )
            aligned = self._whisperx.align(
                result.get("segments", []),
                align_model,
                metadata,
                audio,
                self._device,
                return_char_alignments=False,
            )
            aligned_words = aligned.get("word_segments", []) or []
            refined = _to_word_timings(aligned_words)
            return refined if refined else words
        except Exception:
            return words


def _to_word_timings(aligned_words: list[dict[str, object]]) -> list[WordTiming]:
    results: list[WordTiming] = []
    for item in aligned_words:
        token = re.sub(r"[^a-zA-Z0-9_-]", "", str(item.get("word", ""))).lower()
        if not token:
            continue
        start = item.get("start")
        end = item.get("end")
        if start is None or end is None:
            continue
        start_value = float(start)
        end_value = max(start_value + 0.01, float(end))
        results.append(
            WordTiming(
                word=token,
                start=round(start_value, 3),
                end=round(end_value, 3),
            )
        )
    return results


def create_refiner(
    backend: str,
    *,
    whisperx_model: str = "small",
    whisperx_device: str = "cpu",
    whisperx_compute_type: str = "int8",
) -> BaseRefiner:
    if backend == "whisperx":
        return WhisperXRefiner(
            model_name=whisperx_model,
            device=whisperx_device,
            compute_type=whisperx_compute_type,
        )
    return MockRefiner()
