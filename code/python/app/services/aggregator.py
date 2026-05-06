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
        if not words:
            return []
        # Prefer pause-based grouping so phrases follow natural speech breaks.
        pause_split_phrases = self._to_phrases_by_pause(words)
        if pause_split_phrases:
            return pause_split_phrases

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

    def _to_phrases_by_pause(self, words: list[WordTiming]) -> list[PhraseTiming]:
        if not words:
            return []
        max_gap_seconds = 0.35
        max_words_per_phrase = max(2, self._phrase_group_size + 1)
        phrases: list[PhraseTiming] = []
        buffer: list[WordTiming] = [words[0]]
        for word in words[1:]:
            previous = buffer[-1]
            gap = max(0.0, word.start - previous.end)
            if gap >= max_gap_seconds or len(buffer) >= max_words_per_phrase:
                phrases.append(self._build_phrase(buffer))
                buffer = [word]
                continue
            buffer.append(word)
        if buffer:
            phrases.append(self._build_phrase(buffer))
        return phrases

    def _build_phrase(self, words: list[WordTiming]) -> PhraseTiming:
        return PhraseTiming(
            text=" ".join(item.word for item in words),
            start=words[0].start,
            end=words[-1].end,
            words=[item.word for item in words],
        )
