from __future__ import annotations

from dataclasses import dataclass

from app.services.transcriber import WordTiming


@dataclass(slots=True)
class PhraseTiming:
    text: str
    start: float
    end: float
    words: list[str]


@dataclass(slots=True)
class SentenceTiming:
    text: str
    start: float
    end: float
    words: list[str]


class NlpAggregator:
    def __init__(self, phrase_group_size: int = 2) -> None:
        self._phrase_group_size = max(1, phrase_group_size)

    def to_phrases(self, words: list[WordTiming]) -> list[PhraseTiming]:
        phrases: list[PhraseTiming] = []
        buffer: list[WordTiming] = []
        for word in words:
            buffer.append(word)
            if len(buffer) >= self._phrase_group_size:
                phrases.append(self._build_phrase(buffer))
                buffer = []
        if buffer:
            phrases.append(self._build_phrase(buffer))
        return phrases

    def to_sentence(self, words: list[WordTiming]) -> SentenceTiming | None:
        if not words:
            return None
        return SentenceTiming(
            text=" ".join(item.word for item in words),
            start=words[0].start,
            end=words[-1].end,
            words=[item.word for item in words],
        )

    def _build_phrase(self, words: list[WordTiming]) -> PhraseTiming:
        return PhraseTiming(
            text=" ".join(item.word for item in words),
            start=words[0].start,
            end=words[-1].end,
            words=[item.word for item in words],
        )
