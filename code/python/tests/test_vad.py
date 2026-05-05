from app.services.transcriber import WordTiming
from app.services.vad import _overlap_speech


def test_overlap_speech_detects_intersection():
    word = WordTiming(word="hello", start=0.2, end=0.5)
    windows = [(0.0, 0.1), (0.4, 0.8)]
    assert _overlap_speech(word, windows) is True


def test_overlap_speech_detects_no_intersection():
    word = WordTiming(word="hello", start=1.2, end=1.5)
    windows = [(0.0, 0.5), (0.6, 1.0)]
    assert _overlap_speech(word, windows) is False
