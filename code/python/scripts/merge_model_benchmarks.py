"""Merge resumable ``benchmark_models`` batches into thesis-ready artifacts.

Example
-------
    python -m scripts.merge_model_benchmarks results/model_benchmark_v2_part*.csv \
        --out results/model_benchmark_v2
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from scripts.benchmark_models import _summary


def run(args: argparse.Namespace) -> int:
    paths = [Path(item) for item in args.inputs]
    rows: list[dict[str, object]] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    if not rows:
        raise SystemExit("no benchmark rows found")

    keys = [(row["model"], row["clip"], row["repeat"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise SystemExit("duplicate (model, clip, repeat) rows found; refusing to merge ambiguous batches")

    models = list(dict.fromkeys(str(row["model"]) for row in rows))
    summary = [_summary(rows, model) for model in models]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    out.with_suffix(".json").write_text(json.dumps({
        "protocol": {
            "source_batches": [str(path) for path in paths],
            "merged_rows": len(rows),
            "duplicate_key": ["model", "clip", "repeat"],
        },
        "summary": summary,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Merged {len(rows)} rows into {out.with_suffix('.json')} and {out.with_suffix('.csv')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge resumable model-benchmark CSV batches.")
    parser.add_argument("inputs", nargs="+", help="input CSV files from benchmark_models")
    parser.add_argument("--out", required=True, help="path prefix for merged JSON and CSV")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
