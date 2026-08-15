"""Audit and aggregate the five paired denoise reruns for thesis use."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


def mean_sd(values: list[float]) -> tuple[float, float]:
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    args = parser.parse_args()
    root = Path(args.results_dir)
    files = sorted(root.glob("noise_white_base_paired_seed_*.csv"))
    if len(files) != 5:
        raise RuntimeError(f"Expected five seed CSVs; found {len(files)}")
    per_seed: list[dict[str, object]] = []
    audit: dict[str, object] = {"files": [], "valid": True}
    for file in files:
        with file.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        if len(rows) != 240:
            raise RuntimeError(f"{file.name}: expected 240 rows, found {len(rows)}")
        groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
        for row in rows: groups[(row["clip"], row["snr"])].append(row)
        for key, group in groups.items():
            if len(group) != 2: raise RuntimeError(f"{file.name}/{key}: missing paired condition")
            if len({x["input_sha256"] for x in group}) != 1: raise RuntimeError(f"{file.name}/{key}: inputs not paired")
            on = [x for x in group if x["denoise"] == "True"]
            if len(on) != 1 or on[0]["denoise_applied"] != "True": raise RuntimeError(f"{file.name}/{key}: denoise not applied")
        seed = int(file.stem.rsplit("_", 1)[1])
        by_condition: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
        for row in rows: by_condition[(row["snr"], row["denoise"])].append(row)
        for (snr, denoise), condition_rows in by_condition.items():
            # All clips have the same reference-word total within a condition.
            total_ref = 0; total_s = total_d = total_i = 0
            for row in condition_rows:
                # Recover integer edit counts from the exact WER components only
                # is impossible after rounding; the matching JSON is authoritative.
                pass
        summary = json.loads(file.with_suffix(".json").read_text(encoding="utf-8"))
        for condition in summary["conditions"]:
            per_seed.append({"seed": seed, "snr": str(condition["snr"]), "denoise": bool(condition["denoise"]), "wer": float(condition["wer"]), "word_loss_rate": float(condition["word_loss_rate"]), "hallucination_rate": float(condition["hallucination_rate"]), "ref_words": int(condition["ref_words"])})
        audit["files"].append({"file": file.name, "rows": len(rows), "groups": len(groups), "status": "PASS"})
    conditions: dict[tuple[str, bool], list[dict[str, object]]] = defaultdict(list)
    for row in per_seed: conditions[(str(row["snr"]), bool(row["denoise"]))].append(row)
    rows_out: list[dict[str, object]] = []
    for snr in ("20", "10", "5", "0"):
        raw, den = conditions[(snr, False)], conditions[(snr, True)]
        raw_wer = [float(r["wer"]) for r in raw]; den_wer = [float(r["wer"]) for r in den]
        raw_loss = [float(r["word_loss_rate"]) for r in raw]; den_loss = [float(r["word_loss_rate"]) for r in den]
        raw_ins = [float(r["hallucination_rate"]) for r in raw]; den_ins = [float(r["hallucination_rate"]) for r in den]
        m_raw, sd_raw = mean_sd(raw_wer); m_den, sd_den = mean_sd(den_wer)
        m_delta, sd_delta = mean_sd([(d-r)*100 for r, d in zip(raw_wer, den_wer)])
        m_raw_ins, _ = mean_sd(raw_ins); m_den_ins, _ = mean_sd(den_ins)
        signs = {(d-r) > 0 for r, d in zip(raw_wer, den_wer)}
        conclusion = "inestable; signos mixtos entre semillas" if len(signs) > 1 else ("mejora consistente" if m_delta < 0 else "empeora consistentemente")
        rows_out.append({"snr_db": snr, "wer_without_mean_pct": round(m_raw*100, 2), "wer_without_sd_pct": round(sd_raw*100, 2), "wer_with_mean_pct": round(m_den*100, 2), "wer_with_sd_pct": round(sd_den*100, 2), "mean_delta_wer_pp": round(m_delta, 2), "sd_delta_wer_pp": round(sd_delta, 2), "word_loss_without_mean_pct": round(mean_sd(raw_loss)[0]*100, 2), "word_loss_with_mean_pct": round(mean_sd(den_loss)[0]*100, 2), "insertion_without_mean_pct": round(m_raw_ins*100, 2), "insertion_with_mean_pct": round(m_den_ins*100, 2), "conclusion_es": conclusion})
    with (root / "per_seed_paired_noise.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(per_seed[0])); writer.writeheader(); writer.writerows(per_seed)
    with (root / "paired_noise_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows_out[0])); writer.writeheader(); writer.writerows(rows_out)
    (root / "paired_noise_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rows_out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
