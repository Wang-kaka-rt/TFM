"""Reproducible WER and latency benchmark for faster-whisper models.

This benchmark is intentionally separate from ``evaluate_noise``: it answers
the clean-audio model-selection question used by the thesis (RQ1/RQ3), while
the other script measures noise robustness (RQ2).  It consumes the same
``clip.wav`` + ``clip.txt`` corpus format and records both per-clip and
aggregate evidence in CSV/JSON.

Example
-------
    python -m scripts.benchmark_models --audio-dir data/clips \
        --models tiny base small --repeats 3 --out results/model_benchmark
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

from scripts.evaluate_noise import (
    SAMPLE_RATE,
    align_counts,
    build_transcriber,
    load_audio_dir,
    load_manifest,
    tokenize,
    write_wav_mono,
)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percentile))
    return ordered[index]


def _summary(rows: list[dict[str, object]], model: str) -> dict[str, object]:
    selected = [row for row in rows if row["model"] == model]
    ref_words = sum(int(row["ref_words"]) for row in selected)
    subs = sum(int(row["substitutions"]) for row in selected)
    dels = sum(int(row["deletions"]) for row in selected)
    ins = sum(int(row["insertions"]) for row in selected)
    latencies = [float(row["processing_seconds"]) for row in selected]
    durations = [float(row["audio_duration_seconds"]) for row in selected]
    rtf = [latency / duration for latency, duration in zip(latencies, durations) if duration > 0]
    return {
        "model": model,
        "clips": len({str(row["clip"]) for row in selected}),
        "runs": len(selected),
        "ref_words": ref_words,
        "wer": round((subs + dels + ins) / ref_words, 4) if ref_words else 0.0,
        "substitutions": subs,
        "deletions": dels,
        "insertions": ins,
        "latency_mean_seconds": round(statistics.mean(latencies), 4) if latencies else 0.0,
        "latency_median_seconds": round(statistics.median(latencies), 4) if latencies else 0.0,
        "latency_std_seconds": round(statistics.stdev(latencies), 4) if len(latencies) > 1 else 0.0,
        "latency_p95_seconds": round(_percentile(latencies, 0.95), 4),
        "rtf_mean": round(statistics.mean(rtf), 4) if rtf else 0.0,
    }


def run(args: argparse.Namespace) -> int:
    if args.manifest:
        samples = load_manifest(Path(args.manifest))
    elif args.audio_dir:
        samples = load_audio_dir(Path(args.audio_dir))
    else:
        print("error: provide --manifest or --audio-dir", file=sys.stderr)
        return 2
    if not samples:
        print("error: no samples loaded", file=sys.stderr)
        return 2
    total_dataset_clips = len(samples)
    samples = samples[args.start_index: args.start_index + args.max_clips if args.max_clips else None]
    if not samples:
        print("error: the requested clip slice is empty", file=sys.stderr)
        return 2

    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        for model in args.models:
            transcriber = build_transcriber(args.backend, model, args.device, args.compute_type)
            for sample in samples:
                audio_path = tmp / f"{model}_{sample.name}.wav"
                write_wav_mono(audio_path, sample.audio)
                ref = tokenize(sample.text)
                # The first run is explicitly retained.  It reflects the
                # practical cold-session experience and is distinguishable in
                # the raw CSV; aggregate results include every run.
                for repeat in range(1, args.repeats + 1):
                    started = time.perf_counter()
                    words = transcriber.transcribe(audio_path, chunk_index=0)
                    processing_seconds = max(0.0, time.perf_counter() - started)
                    hypothesis = " ".join(word.word for word in words)
                    hyp = tokenize(hypothesis)
                    substitutions, deletions, insertions, hits = align_counts(ref, hyp)
                    denominator = len(ref) or 1
                    rows.append({
                        "model": model,
                        "clip": sample.name,
                        "repeat": repeat,
                        "reference": sample.text,
                        "hypothesis": hypothesis,
                        "audio_duration_seconds": round(sample.audio.size / SAMPLE_RATE, 4),
                        "processing_seconds": round(processing_seconds, 4),
                        "real_time_factor": round(processing_seconds / (sample.audio.size / SAMPLE_RATE), 4)
                        if sample.audio.size else 0.0,
                        "ref_words": len(ref),
                        "substitutions": substitutions,
                        "deletions": deletions,
                        "insertions": insertions,
                        "hits": hits,
                        "wer": round((substitutions + deletions + insertions) / denominator, 4),
                    })
                print(f"  scored model={model} clip={sample.name}", file=sys.stderr)

    summary = [_summary(rows, model) for model in args.models]
    print("\nModel benchmark (WER lower is better; RTF below 1 is faster than audio duration)")
    print(f"{'model':<12} {'WER':>7} {'median s':>10} {'p95 s':>8} {'mean RTF':>10}")
    for item in summary:
        print(f"{item['model']:<12} {item['wer']:>7.3f} {item['latency_median_seconds']:>10.3f} "
              f"{item['latency_p95_seconds']:>8.3f} {item['rtf_mean']:>10.3f}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".csv").write_text("", encoding="utf-8")
        with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        out.with_suffix(".json").write_text(json.dumps({
            "protocol": {
                "dataset_clips": len(samples),
                "dataset_total_clips": total_dataset_clips,
                "start_index": args.start_index,
                "max_clips": args.max_clips,
                "models": args.models,
                "repeats": args.repeats,
                "backend": args.backend,
                "device": args.device,
                "compute_type": args.compute_type,
                "language": "es",
                "beam_size": 1,
                "sample_rate_hz": SAMPLE_RATE,
                "normalization": "lowercase; non-word punctuation replaced with separators; underscores trimmed",
                "latency_scope": "faster-whisper transcribe call; excludes WAV preparation and model-load time",
                "runtime": {"python": platform.python_version(), "platform": platform.platform()},
            },
            "summary": summary,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nWrote {out.with_suffix('.json')} and {out.with_suffix('.csv')}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WER and latency benchmark for faster-whisper models.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--manifest", help="JSON list of {audio, text} entries")
    source.add_argument("--audio-dir", help="folder of clip.wav + clip.txt pairs")
    parser.add_argument("--models", nargs="+", default=["tiny", "base", "small"])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--start-index", type=int, default=0,
                        help="zero-based first clip index; use with --max-clips for resumable batches")
    parser.add_argument("--max-clips", type=int,
                        help="number of clips to process; omitted means the remaining corpus")
    parser.add_argument("--backend", choices=["faster-whisper", "mock"], default="faster-whisper")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--out", help="path prefix for JSON and CSV artifacts")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.repeats < 1:
        raise SystemExit("--repeats must be at least 1")
    if args.start_index < 0:
        raise SystemExit("--start-index must be non-negative")
    if args.max_clips is not None and args.max_clips < 1:
        raise SystemExit("--max-clips must be at least 1")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
