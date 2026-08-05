"""Noise-robustness & word-loss evaluation harness.

Measures how well the recognition pipeline survives background noise, producing
the numbers a thesis needs: Word Error Rate (WER), word-loss rate (deletions),
hallucination rate (insertions), and the effect of the spectral-gating denoiser.

What it does
------------
For every clip in a labelled dataset and every requested SNR level it:

1. mixes noise into the clean clip at the target SNR (synthetic white noise by
   default, or a real noise recording with ``--noise-file``);
2. transcribes it with the *real* faster-whisper backend, using the same
   anti-hallucination thresholds the live service uses;
3. optionally repeats step 2 with the noisereduce denoiser turned on;
4. scores the hypothesis against the ground-truth transcript.

Dataset
-------
Provide one of:

* ``--manifest data.json`` — a JSON list of ``{"audio": "clip.wav", "text": "hola que tal"}``
  (audio paths may be relative to the manifest file), or
* ``--audio-dir DIR`` — a folder where each ``clip.wav`` has a sibling ``clip.txt``
  holding its transcript.

Audio is read as 16 kHz mono internally (other rates/channels are converted).

Examples
--------
    # Real evaluation across several SNRs, denoise off vs on, base model:
    python -m scripts.evaluate_noise --audio-dir data/clips \\
        --snr clean 20 10 5 0 --denoise both --model base \\
        --out results/noise_eval

    # Smoke test with no audio/model (synthesises clips, uses the mock backend):
    python -m scripts.evaluate_noise --selftest
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import statistics
import sys
import tempfile
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.services.denoiser import NoiseReduceDenoiser
from app.services.transcriber import clean_token, create_transcriber

SAMPLE_RATE = 16_000


# --------------------------------------------------------------------------- #
# Audio I/O helpers
# --------------------------------------------------------------------------- #
def read_wav_mono(path: Path, target_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Read a WAV file as float32 mono in [-1, 1], resampled to ``target_rate``."""
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    if width != 2:
        raise ValueError(f"{path}: only 16-bit PCM WAV is supported (got {width * 8}-bit)")
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if rate != target_rate and audio.size:
        # Linear resample — good enough for an ASR robustness benchmark.
        duration = audio.size / rate
        new_len = max(1, int(round(duration * target_rate)))
        audio = np.interp(
            np.linspace(0.0, audio.size - 1, new_len),
            np.arange(audio.size),
            audio,
        ).astype(np.float32)
    return audio


def write_wav_mono(path: Path, signal: np.ndarray, rate: int = SAMPLE_RATE) -> None:
    pcm = (np.clip(signal, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm)


def rms(signal: np.ndarray) -> float:
    return float(np.sqrt(np.mean(signal**2))) if signal.size else 0.0


# --------------------------------------------------------------------------- #
# Noise mixing
# --------------------------------------------------------------------------- #
def make_noise(kind: str, length: int, rng: np.random.Generator) -> np.ndarray:
    """Synthesise ``length`` samples of white or pink noise (unit-ish RMS)."""
    white = rng.standard_normal(length).astype(np.float32)
    if kind == "white":
        return white
    # Pink: shape white noise with a 1/sqrt(f) spectral slope.
    spectrum = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(length)
    freqs[0] = freqs[1] if len(freqs) > 1 else 1.0
    pink = np.fft.irfft(spectrum / np.sqrt(freqs), n=length).astype(np.float32)
    std = pink.std() or 1.0
    return pink / std


def mix_at_snr(clean: np.ndarray, noise: np.ndarray, snr_db: float, rng: np.random.Generator) -> np.ndarray:
    """Add ``noise`` to ``clean`` scaled to the target speech-band SNR (dB)."""
    if noise.size < clean.size:  # tile a short noise recording to cover the clip
        reps = int(np.ceil(clean.size / noise.size))
        noise = np.tile(noise, reps)
    noise = noise[: clean.size]

    # Reference the SNR against the active-speech RMS, not whole-clip RMS, so
    # leading/trailing silence does not deflate the apparent signal level.
    speech = clean[np.abs(clean) > (0.1 * (np.abs(clean).max() or 1.0))]
    signal_rms = rms(speech if speech.size else clean)
    noise_rms = rms(noise) or 1e-9
    target_noise_rms = signal_rms / (10 ** (snr_db / 20.0))
    scaled = noise * (target_noise_rms / noise_rms)
    return (clean + scaled).astype(np.float32)


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def tokenize(text: str) -> list[str]:
    return [t for t in (clean_token(w) for w in text.split()) if t]


def align_counts(ref: list[str], hyp: list[str]) -> tuple[int, int, int, int]:
    """Levenshtein alignment over word tokens.

    Returns ``(substitutions, deletions, insertions, hits)``.
    """
    n, m = len(ref), len(hyp)
    # dp[i][j] = edit distance between ref[:i] and hyp[:j], plus a backtrace.
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)

    i, j = n, m
    subs = dels = ins = hits = 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1):
            if ref[i - 1] == hyp[j - 1]:
                hits += 1
            else:
                subs += 1
            i, j = i - 1, j - 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            dels += 1
            i -= 1
        else:
            ins += 1
            j -= 1
    return subs, dels, ins, hits


@dataclass
class Tally:
    clips: int = 0
    ref_words: int = 0
    subs: int = 0
    dels: int = 0
    ins: int = 0
    hits: int = 0

    def add(self, ref: list[str], hyp: list[str]) -> None:
        s, d, i, h = align_counts(ref, hyp)
        self.clips += 1
        self.ref_words += len(ref)
        self.subs += s
        self.dels += d
        self.ins += i
        self.hits += h

    @property
    def wer(self) -> float:
        return (self.subs + self.dels + self.ins) / self.ref_words if self.ref_words else 0.0

    @property
    def word_loss_rate(self) -> float:  # deletions / reference words = "words lost"
        return self.dels / self.ref_words if self.ref_words else 0.0

    @property
    def hallucination_rate(self) -> float:  # insertions / reference words
        return self.ins / self.ref_words if self.ref_words else 0.0

    @property
    def hit_rate(self) -> float:
        return self.hits / self.ref_words if self.ref_words else 0.0

    def as_row(self) -> dict[str, float | int]:
        return {
            "clips": self.clips,
            "ref_words": self.ref_words,
            "wer": round(self.wer, 4),
            "word_loss_rate": round(self.word_loss_rate, 4),
            "hallucination_rate": round(self.hallucination_rate, 4),
            "hit_rate": round(self.hit_rate, 4),
            "subs": self.subs,
            "dels": self.dels,
            "ins": self.ins,
            "hits": self.hits,
        }


@dataclass
class Sample:
    audio: np.ndarray
    text: str
    name: str


# --------------------------------------------------------------------------- #
# Dataset loading
# --------------------------------------------------------------------------- #
def load_manifest(path: Path) -> list[Sample]:
    entries = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    samples: list[Sample] = []
    for entry in entries:
        audio_path = (base / entry["audio"]).resolve()
        samples.append(Sample(read_wav_mono(audio_path), str(entry["text"]), audio_path.stem))
    return samples


def load_audio_dir(directory: Path) -> list[Sample]:
    samples: list[Sample] = []
    for wav_path in sorted(directory.glob("*.wav")):
        txt_path = wav_path.with_suffix(".txt")
        if not txt_path.exists():
            print(f"  skip {wav_path.name}: no sibling .txt transcript", file=sys.stderr)
            continue
        samples.append(
            Sample(read_wav_mono(wav_path), txt_path.read_text(encoding="utf-8").strip(), wav_path.stem)
        )
    return samples


def make_selftest_samples(rng: np.random.Generator) -> list[Sample]:
    """Synthetic tone bursts standing in for words, for a no-data dry run."""
    phrases = ["hola bien", "consejo familia", "ritmo voz muestra"]
    samples: list[Sample] = []
    for idx, phrase in enumerate(phrases):
        tokens = phrase.split()
        burst = int(SAMPLE_RATE * 0.4)
        gap = int(SAMPLE_RATE * 0.15)
        chunks = []
        for k, _tok in enumerate(tokens):
            t = np.arange(burst) / SAMPLE_RATE
            freq = 180 + 40 * k
            chunks.append(0.4 * np.sin(2 * np.pi * freq * t).astype(np.float32))
            chunks.append(np.zeros(gap, dtype=np.float32))
        samples.append(Sample(np.concatenate(chunks), phrase, f"selftest_{idx:02d}"))
    return samples


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
@dataclass
class Condition:
    snr: str          # "clean" or a dB string
    denoise: bool
    tally: Tally = field(default_factory=Tally)

    @property
    def label(self) -> str:
        return f"{self.snr:>5} {'denoise' if self.denoise else 'raw    '}"


def build_transcriber(backend: str, model: str, device: str, compute_type: str):
    # Seed words double as the faster-whisper hotword/prompt vocabulary and the
    # mock backend's word source, so --selftest stays meaningful.
    seed = ["hola", "bien", "consejo", "familia", "ritmo", "voz", "muestra"]
    return create_transcriber(
        backend,
        seed,
        faster_whisper_model=model,
        faster_whisper_device=device,
        faster_whisper_compute_type=compute_type,
        faster_whisper_beam_size=1,
        transcriber_language="es",
        transcriber_initial_prompt="Vocabulario en español: " + ", ".join(seed) + ".",
        transcriber_hotwords=" ".join(seed),
    )


def transcribe_text(
    transcriber,
    signal: np.ndarray,
    denoise: NoiseReduceDenoiser | None,
    tmp: Path,
    *,
    file_stem: str,
) -> tuple[str, float]:
    """Return the hypothesis and processing time for one fixed audio input.

    ``file_stem`` makes every condition use its own temporary WAV.  This is
    important for a fair raw-versus-denoised comparison: the denoiser works in
    place and must never alter the audio reused by the raw condition.
    """
    path = tmp / f"{file_stem}.wav"
    write_wav_mono(path, signal)
    started = time.perf_counter()
    if denoise is not None:
        denoise.denoise(path)
    words = transcriber.transcribe(path, chunk_index=0)
    return " ".join(w.word for w in words), max(0.0, time.perf_counter() - started)


def run(args: argparse.Namespace) -> int:
    rng = np.random.default_rng(args.seed)

    # ---- dataset --------------------------------------------------------- #
    if args.selftest:
        samples = make_selftest_samples(rng)
        backend = "mock"
    elif args.manifest:
        samples = load_manifest(Path(args.manifest))
        backend = args.backend
    elif args.audio_dir:
        samples = load_audio_dir(Path(args.audio_dir))
        backend = args.backend
    else:
        print("error: provide --manifest, --audio-dir, or --selftest", file=sys.stderr)
        return 2
    if not samples:
        print("error: no samples loaded", file=sys.stderr)
        return 2

    # ---- noise source ---------------------------------------------------- #
    noise_clip = read_wav_mono(Path(args.noise_file)) if args.noise_file else None

    # ---- pipeline pieces ------------------------------------------------- #
    transcriber = build_transcriber(backend, args.model, args.device, args.compute_type)
    denoiser = NoiseReduceDenoiser(prop_decrease=0.8, stationary=False)
    if args.denoise in ("on", "both") and not denoiser._available:  # noqa: SLF001 - intentional capability probe
        print("warning: noisereduce not installed; denoise conditions become no-ops", file=sys.stderr)

    denoise_modes = {"off": [False], "on": [True], "both": [False, True]}[args.denoise]
    conditions = [Condition(snr, dn) for snr in args.snr for dn in denoise_modes]

    # ---- evaluate -------------------------------------------------------- #
    per_clip_rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        for sample in samples:
            ref = tokenize(sample.text)
            # Create one deterministic noisy signal per (clip, SNR) and share
            # it between raw and denoised conditions.  Without this pairing,
            # any apparent denoising effect could partly come from a different
            # random-noise draw instead of the denoiser itself.
            signals: dict[str, np.ndarray] = {}
            for snr in args.snr:
                if snr == "clean":
                    signals[snr] = sample.audio
                else:
                    noise = noise_clip if noise_clip is not None else make_noise(args.noise, sample.audio.size, rng)
                    signals[snr] = mix_at_snr(sample.audio, noise, float(snr), rng)

            for cond_index, cond in enumerate(conditions):
                signal = signals[cond.snr]
                dn = denoiser if cond.denoise else None
                hyp_text, processing_seconds = transcribe_text(
                    transcriber,
                    signal,
                    dn,
                    tmp,
                    file_stem=f"{sample.name}_{cond.snr}_{cond_index}",
                )
                hyp = tokenize(hyp_text)
                cond.tally.add(ref, hyp)
                per_clip_rows.append(
                    {
                        "clip": sample.name,
                        "snr": cond.snr,
                        "denoise": cond.denoise,
                        "ref": sample.text,
                        "hyp": hyp_text,
                        "audio_duration_seconds": round(sample.audio.size / SAMPLE_RATE, 4),
                        "processing_seconds": round(processing_seconds, 4),
                        **{k: v for k, v in _clip_metrics(ref, hyp).items()},
                    }
                )
            print(f"  scored {sample.name} ({len(ref)} ref words)", file=sys.stderr)

    # ---- report ---------------------------------------------------------- #
    print()
    print(f"Dataset: {len(samples)} clips | backend={backend} model={args.model} | noise={args.noise}"
          + (f" file={Path(args.noise_file).name}" if args.noise_file else ""))
    print("=" * 78)
    header = f"{'condition':>14} {'WER':>7} {'word_loss':>10} {'halluc':>8} {'hit':>7} {'clips':>6}"
    print(header)
    print("-" * 78)
    for cond in conditions:
        t = cond.tally
        print(f"{cond.label:>14} {t.wer:>7.3f} {t.word_loss_rate:>10.3f} "
              f"{t.hallucination_rate:>8.3f} {t.hit_rate:>7.3f} {t.clips:>6}")
    print("=" * 78)
    print("WER↓  word_loss=deletions/ref  halluc=insertions/ref  hit=correct/ref")

    # ---- write artifacts ------------------------------------------------- #
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "backend": backend,
            "model": args.model,
            "device": args.device,
            "compute_type": args.compute_type,
            "language": "es",
            "beam_size": 1,
            "seed": args.seed,
            "sample_rate_hz": SAMPLE_RATE,
            "normalization": "lowercase; non-word punctuation replaced with separators; underscores trimmed",
            "snr_reference": "active-speech RMS (samples above 10% of peak amplitude)",
            "paired_raw_denoise_inputs": True,
            "runtime": {
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
            "noise": args.noise,
            "noise_file": args.noise_file,
            "clips": len(samples),
            "conditions": [
                {"snr": c.snr, "denoise": c.denoise, **c.tally.as_row()} for c in conditions
            ],
        }
        out.with_suffix(".json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(per_clip_rows[0].keys()))
            writer.writeheader()
            writer.writerows(per_clip_rows)
        print(f"\nWrote {out.with_suffix('.json')} and {out.with_suffix('.csv')}")

    return 0


def _clip_metrics(ref: list[str], hyp: list[str]) -> dict[str, float]:
    s, d, i, h = align_counts(ref, hyp)
    n = len(ref) or 1
    return {
        "wer": round((s + d + i) / n, 4),
        "word_loss_rate": round(d / n, 4),
        "hallucination_rate": round(i / n, 4),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Noise-robustness & word-loss evaluation for the voice pipeline.")
    src = p.add_argument_group("dataset (choose one)")
    src.add_argument("--manifest", help="JSON list of {audio, text} entries")
    src.add_argument("--audio-dir", help="folder of clip.wav + clip.txt pairs")
    src.add_argument("--selftest", action="store_true", help="synthesise clips and use the mock backend (no data/model needed)")

    p.add_argument("--snr", nargs="+", default=["clean", "20", "10", "5", "0"],
                   help="SNR levels in dB, plus the literal 'clean' (default: clean 20 10 5 0)")
    p.add_argument("--noise", choices=["white", "pink"], default="white", help="synthetic noise colour")
    p.add_argument("--noise-file", help="use this WAV as the noise source instead of synthetic noise")
    p.add_argument("--denoise", choices=["off", "on", "both"], default="both", help="denoiser conditions to run")

    p.add_argument("--backend", choices=["faster-whisper", "mock"], default="faster-whisper")
    p.add_argument("--model", default="base", help="faster-whisper model name")
    p.add_argument("--device", default="auto")
    p.add_argument("--compute-type", default="int8")

    p.add_argument("--out", help="path prefix for the .json + .csv result files")
    p.add_argument("--seed", type=int, default=42)
    return p


def main(argv: list[str] | None = None) -> int:
    return run(build_arg_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
