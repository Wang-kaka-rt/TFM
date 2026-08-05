"""Create thesis-ready tables from already recorded experiment artifacts.

This script never loads an ASR model and never processes audio.  It only reads
the committed/retained JSON summaries from an earlier experiment execution and
writes derived CSV/Markdown tables with explicit source-file traceability.

Example
-------
    python -m scripts.build_thesis_results \
        --results-dir ../../Resume-or-Thesis/Thesis/提交版本/experimental_materials/results \
        --out-dir ../../Resume-or-Thesis/Thesis/提交版本/experimental_materials/derived_results
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


MODEL_FILES = ("model_tiny_norm.json", "model_base_norm.json", "model_small_norm.json")
NOISE_FILE = "noise_white_base_norm.json"


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"missing required result file: {path}") from exc


def _condition(data: dict[str, object], *, snr: str, denoise: bool) -> dict[str, object]:
    conditions = data.get("conditions")
    if not isinstance(conditions, list):
        raise SystemExit("result JSON has no conditions array")
    for item in conditions:
        if isinstance(item, dict) and str(item.get("snr")) == snr and item.get("denoise") is denoise:
            return item
    raise SystemExit(f"condition snr={snr!r}, denoise={denoise!r} not found")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build(results_dir: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str]]:
    model_rows: list[dict[str, object]] = []
    sources: list[str] = []
    for name in MODEL_FILES:
        path = results_dir / name
        data = _read_json(path)
        condition = _condition(data, snr="clean", denoise=False)
        model_rows.append({
            "model": data.get("model"),
            "clips": condition.get("clips"),
            "ref_words": condition.get("ref_words"),
            "wer": condition.get("wer"),
            "word_loss_rate": condition.get("word_loss_rate"),
            "hallucination_rate": condition.get("hallucination_rate"),
            "hit_rate": condition.get("hit_rate"),
            "avg_transcribe_seconds": condition.get("avg_transcribe_seconds"),
            "p95_transcribe_seconds": condition.get("p95_transcribe_seconds"),
            "source_file": name,
        })
        sources.append(name)

    noise_path = results_dir / NOISE_FILE
    noise_data = _read_json(noise_path)
    noise_rows: list[dict[str, object]] = []
    for condition in noise_data.get("conditions", []):
        if not isinstance(condition, dict):
            continue
        noise_rows.append({
            "model": noise_data.get("model"),
            "noise": noise_data.get("noise"),
            "snr": condition.get("snr"),
            "denoise": condition.get("denoise"),
            "clips": condition.get("clips"),
            "ref_words": condition.get("ref_words"),
            "wer": condition.get("wer"),
            "word_loss_rate": condition.get("word_loss_rate"),
            "hallucination_rate": condition.get("hallucination_rate"),
            "hit_rate": condition.get("hit_rate"),
            "avg_transcribe_seconds": condition.get("avg_transcribe_seconds"),
            "p95_transcribe_seconds": condition.get("p95_transcribe_seconds"),
            "source_file": NOISE_FILE,
        })
    if not noise_rows:
        raise SystemExit(f"no usable conditions found in {noise_path}")
    sources.append(NOISE_FILE)
    return model_rows, noise_rows, sources


def _markdown_table(rows: list[dict[str, object]], fields: list[str]) -> str:
    header = "| " + " | ".join(fields) + " |"
    divider = "|" + "|".join("---" for _ in fields) + "|"
    body = ["| " + " | ".join(str(row.get(field, "")) for field in fields) + " |" for row in rows]
    return "\n".join([header, divider, *body])


def write_outputs(out_dir: Path, model_rows: list[dict[str, object]], noise_rows: list[dict[str, object]], sources: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(out_dir / "table_model_comparison.csv", model_rows)
    _write_csv(out_dir / "table_noise_comparison.csv", noise_rows)
    (out_dir / "thesis_results_provenance.json").write_text(json.dumps({
        "source_execution": "existing result JSON files; no ASR model was run by this script",
        "source_files": sources,
        "model_comparison_rule": "clean audio; denoise=false",
        "noise_comparison_rule": "all conditions retained exactly as stored in noise_white_base_norm.json",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    model_table = _markdown_table(model_rows, [
        "model", "clips", "wer", "word_loss_rate", "hallucination_rate",
        "avg_transcribe_seconds", "p95_transcribe_seconds",
    ])
    noise_table = _markdown_table(noise_rows, [
        "snr", "denoise", "wer", "word_loss_rate", "hallucination_rate",
        "avg_transcribe_seconds", "p95_transcribe_seconds",
    ])
    (out_dir / "texto_resultados_es.md").write_text(
        "# Tablas derivadas de los resultados experimentales existentes\n\n"
        "Este archivo no contiene una nueva ejecución. Las tablas se derivan de los JSON indicados en "
        "`thesis_results_provenance.json`; antes de incorporarlas a la memoria debe comprobarse que la "
        "configuración experimental descrita coincide con la ejecución original.\n\n"
        "## Comparación de modelos en audio limpio\n\n"
        + model_table + "\n\n"
        "Interpretación sugerida: el mejor modelo debe seleccionarse atendiendo conjuntamente al WER y a "
        "la latencia. Los resultados se limitan a los 30 clips y a la configuración registrada en los "
        "artefactos de origen.\n\n"
        "## Robustez frente a ruido blanco (modelo base)\n\n"
        + noise_table + "\n\n"
        "Interpretación sugerida: el ruido blanco es una condición sintética y no representa por sí solo "
        "el entorno acústico de una actuación en directo.\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build thesis tables from existing result JSON files.")
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    model_rows, noise_rows, sources = build(args.results_dir)
    write_outputs(args.out_dir, model_rows, noise_rows, sources)
    print(f"Wrote thesis-ready tables from {len(sources)} original result files to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
