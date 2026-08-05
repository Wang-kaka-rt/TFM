from __future__ import annotations

from scripts.evaluate_noise import align_counts, tokenize
from scripts.benchmark_models import _summary


def test_tokenize_applies_documented_normalization_rule():
    assert tokenize("¡Hola, mundo! ritmo-voz") == ["hola", "mundo", "ritmo-voz"]


def test_alignment_counts_expose_all_wer_components():
    substitutions, deletions, insertions, hits = align_counts(
        ["hola", "ritmo", "voz"], ["hola", "muestra", "voz", "extra"]
    )
    assert (substitutions, deletions, insertions, hits) == (1, 0, 1, 2)


def test_model_summary_aggregates_latency_and_wer():
    rows = [{
        "model": "base", "clip": "clip_001", "repeat": 1,
        "ref_words": 4, "substitutions": 1, "deletions": 0, "insertions": 0,
        "processing_seconds": 0.5, "audio_duration_seconds": 1.0,
    }, {
        "model": "base", "clip": "clip_002", "repeat": 1,
        "ref_words": 6, "substitutions": 0, "deletions": 1, "insertions": 1,
        "processing_seconds": 1.0, "audio_duration_seconds": 2.0,
    }]
    summary = _summary(rows, "base")
    assert summary["wer"] == 0.3
    assert summary["latency_median_seconds"] == 0.75
    assert summary["rtf_mean"] == 0.5
