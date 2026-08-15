"""Launch all thesis paired-noise seeds without PowerShell path encoding issues."""
from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", required=True)
    parser.add_argument("--clip-dir", required=True)
    parser.add_argument("--result-dir", required=True)
    args = parser.parse_args()
    code_root, clips, results = map(Path, (args.code_root, args.clip_dir, args.result_dir))
    if not code_root.is_dir(): raise RuntimeError(f"Missing source code: {code_root}")
    if not clips.is_dir(): raise RuntimeError(f"Missing clips: {clips}")
    results.mkdir(parents=True, exist_ok=True)
    env = results / "environment.txt"
    env.write_text("\n".join((f"python={sys.version}", f"platform={platform.platform()}", f"run_date={datetime.now(timezone.utc).isoformat()}", "device=auto; compute_type=int8; model=base; seeds=42,43,44,45,46")) + "\n", encoding="utf-8")
    with env.open("a", encoding="utf-8") as fh:
        subprocess.run([sys.executable, "-m", "pip", "freeze"], stdout=fh, check=True)
    for seed in (42, 43, 44, 45, 46):
        command = [sys.executable, "-m", "scripts.evaluate_noise_paired", "--audio-dir", str(clips), "--snr", "20", "10", "5", "0", "--denoise", "both", "--model", "base", "--device", "auto", "--compute-type", "int8", "--seed", str(seed), "--save-noisy-dir", str(results / "paired_inputs" / f"seed_{seed}"), "--out", str(results / f"noise_white_base_paired_seed_{seed}"), "--code-root", str(code_root)]
        subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
