"""Reproducible paired white-noise evaluation for the thesis.

For every clip/SNR/seed, raw and denoised transcription are scored from the
same saved noisy WAV.  The CSV is intentionally auditable: it records the
SHA-256 of that common input and whether the denoiser actually ran.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
import tempfile
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16_000


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wav:
        channels, width, rate = wav.getnchannels(), wav.getsampwidth(), wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    if width != 2:
        raise ValueError(f"{path}: expected 16-bit PCM WAV")
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if rate != SAMPLE_RATE and audio.size:
        new_length = max(1, round(audio.size * SAMPLE_RATE / rate))
        audio = np.interp(np.linspace(0, audio.size - 1, new_length), np.arange(audio.size), audio).astype(np.float32)
    return audio


def write_wav(path: Path, signal: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(signal, -1, 1) * 32767).astype(np.int16).tobytes()
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(SAMPLE_RATE); wav.writeframes(pcm)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mix_white(clean: np.ndarray, snr: float, rng: np.random.Generator) -> np.ndarray:
    noise = rng.standard_normal(clean.size).astype(np.float32)
    active = clean[np.abs(clean) > 0.1 * (np.abs(clean).max() or 1.0)]
    signal_rms = float(np.sqrt(np.mean((active if active.size else clean) ** 2)))
    noise_rms = float(np.sqrt(np.mean(noise ** 2))) or 1e-9
    return (clean + noise * (signal_rms / (10 ** (snr / 20))) / noise_rms).astype(np.float32)


def tokens(text: str) -> list[str]:
    return ["".join(c for c in word.lower() if c.isalnum() or c in "_-") for word in text.split() if word]


def counts(ref: list[str], hyp: list[str]) -> tuple[int, int, int, int]:
    n, m = len(ref), len(hyp)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1): dp[i][0] = i
    for j in range(m + 1): dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]))
    i, j, sub, delete, insert, hit = n, m, 0, 0, 0, 0
    while i or j:
        if i and j and dp[i][j] == dp[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]):
            if ref[i - 1] == hyp[j - 1]: hit += 1
            else: sub += 1
            i -= 1; j -= 1
        elif i and dp[i][j] == dp[i - 1][j] + 1:
            delete += 1; i -= 1
        else:
            insert += 1; j -= 1
    return sub, delete, insert, hit


@dataclass
class Tally:
    ref_words: int = 0
    sub: int = 0
    delete: int = 0
    insert: int = 0
    hit: int = 0
    clips: int = 0
    def add(self, values: tuple[int, int, int, int], words: int) -> None:
        s, d, i, h = values; self.sub += s; self.delete += d; self.insert += i; self.hit += h; self.ref_words += words; self.clips += 1
    def summary(self) -> dict[str, float | int]:
        n = self.ref_words or 1
        return {"clips": self.clips, "ref_words": self.ref_words, "wer": round((self.sub+self.delete+self.insert)/n, 4), "word_loss_rate": round(self.delete/n, 4), "hallucination_rate": round(self.insert/n, 4), "subs": self.sub, "dels": self.delete, "ins": self.insert, "hits": self.hit}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--audio-dir", required=False)
    p.add_argument("--snr", nargs="+", default=["20", "10", "5", "0"])
    p.add_argument("--denoise", choices=["both"], default="both")
    p.add_argument("--model", default="base"); p.add_argument("--device", default="auto"); p.add_argument("--compute-type", default="int8")
    p.add_argument("--seed", type=int, default=42); p.add_argument("--save-noisy-dir"); p.add_argument("--out"); p.add_argument("--code-root", required=True); p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    sys.path.insert(0, args.code_root)
    from app.services.denoiser import NoiseReduceDenoiser
    from app.services.transcriber import create_transcriber, clean_token
    denoiser = NoiseReduceDenoiser(prop_decrease=0.8, stationary=False)
    if not denoiser._available:
        raise RuntimeError("noisereduce is required for a valid denoise comparison")
    if args.selftest:
        test = np.sin(2 * np.pi * 220 * np.arange(SAMPLE_RATE) / SAMPLE_RATE).astype(np.float32)
        samples = [("selftest", test, "hola mundo")]
        backend = "mock"
    else:
        directory = Path(args.audio_dir)
        samples = [(x.stem, read_wav(x), x.with_suffix(".txt").read_text(encoding="utf-8").strip()) for x in sorted(directory.glob("*.wav")) if x.with_suffix(".txt").exists()]
        if not samples: raise RuntimeError("no WAV/TXT sample pairs found")
        backend = "faster-whisper"
    transcriber = create_transcriber(backend, ["hola", "mundo"], faster_whisper_model=args.model, faster_whisper_device=args.device, faster_whisper_compute_type=args.compute_type, faster_whisper_beam_size=1, transcriber_language="es", transcriber_initial_prompt="Vocabulario en español.")
    rng, rows, tallies = np.random.default_rng(args.seed), [], {(s, d): Tally() for s in args.snr for d in (False, True)}
    noisy_dir = Path(args.save_noisy_dir) if args.save_noisy_dir else None
    with tempfile.TemporaryDirectory() as temp_name:
        temp = Path(temp_name)
        for clip, clean, reference_text in samples:
            reference = [clean_token(x) for x in tokens(reference_text) if clean_token(x)]
            for snr in args.snr:
                source = clean if snr == "clean" else mix_white(clean, float(snr), rng)
                saved = (noisy_dir / f"{clip}_{snr}dB.wav") if noisy_dir else (temp / f"{clip}_{snr}_source.wav")
                write_wav(saved, source); input_hash = sha256(saved)
                for enabled in (False, True):
                    work = temp / f"{clip}_{snr}_{enabled}.wav"; write_wav(work, source)
                    started = time.perf_counter(); applied = denoiser.denoise(work) if enabled else False
                    if enabled and not applied: raise RuntimeError(f"denoising failed for {clip}/{snr}")
                    hypothesis = " ".join(word.word for word in transcriber.transcribe(work, chunk_index=0)); elapsed = time.perf_counter() - started
                    hyp = [clean_token(x) for x in tokens(hypothesis) if clean_token(x)]; s, d, i, h = counts(reference, hyp); n = len(reference) or 1
                    tallies[(snr, enabled)].add((s, d, i, h), len(reference))
                    rows.append({"clip": clip, "snr": snr, "denoise": enabled, "denoise_applied": applied, "input_sha256": input_hash, "ref": reference_text, "hyp": hypothesis, "processing_seconds": round(elapsed, 4), "wer": round((s+d+i)/n, 4), "word_loss_rate": round(d/n, 4), "hallucination_rate": round(i/n, 4)})
            print(f"scored {clip}", file=sys.stderr)
    summary = {"paired_raw_denoise_inputs": True, "seed": args.seed, "noise": "white", "model": args.model, "device": args.device, "compute_type": args.compute_type, "runtime": {"python": platform.python_version(), "platform": platform.platform()}, "conditions": [{"snr": snr, "denoise": dn, **tallies[(snr,dn)].summary()} for snr in args.snr for dn in (False, True)]}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.out:
        out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.with_suffix(".json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f: writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
