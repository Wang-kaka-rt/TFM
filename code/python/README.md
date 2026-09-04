# Strudel Voice Python Backend

## Reproducible Linux source setup (Ubuntu/Debian)

Use this path when you want to clone the repository and run the project from
source. It is different from the portable `dist/linux/strudel-voice` release:
the source workflow builds the Strudel frontend, creates a Python virtual
environment, installs CPU-only ASR dependencies, and downloads the local
`faster-whisper` base model once.

### 1. Clone the repository

```bash
git clone <repository-url> strudel-voice
cd strudel-voice/code
```

For an existing checkout, update it first:

```bash
cd ~/strudel-voice
git pull --ff-only
cd code
```

### 2. Check the machine

```bash
bash scripts/setup_linux_source.sh --check
```

The diagnostic reports the status of FFmpeg, PortAudio, libsndfile, Python,
Node.js, pnpm, the virtual environment, the built Strudel frontend, and the
offline speech model. It does not modify the machine.

### 3. Install missing requirements and build everything

```bash
bash scripts/setup_linux_source.sh
```

The script is idempotent and currently supports Ubuntu/Debian. It:

- installs missing system packages with `sudo apt-get`;
- installs Node.js 20 locally when the system Node version is absent or too old;
- installs pnpm 9.15.5, builds the Strudel frontend, and synchronises it to
  `python/static/strudel`;
- creates `python/.venv` and installs the CPU-only PyTorch wheels plus
  `requirements.linux-portable.txt`;
- downloads `faster-whisper` `base` into `python/assets/models` once, so later
  source launches work offline.

The first run requires an internet connection and can download several GB of
dependencies. Later runs reuse the virtual environment, pnpm store, frontend
build, and model cache.

### 4. Start the source version

```bash
bash scripts/run_linux_source.sh
```

This starts Uvicorn at `http://127.0.0.1:8787/` with the verified Linux
settings: browser microphone capture, `faster-whisper` base, CPU `int8`, and
the local offline model cache. Keep the terminal open. Wait until it prints:

```text
Application startup complete.
```

Then open `http://127.0.0.1:8787/` in Firefox or Chrome and grant microphone
permission. The generated samples appear in Strudel's `voice` tab. To stop the
server, press `Ctrl+C` in the terminal.

### Linux troubleshooting

- **Firefox says it cannot connect:** wait for `Application startup complete`,
  then reload the page. Confirm the service with
  `curl http://127.0.0.1:8787/health`.
- **Port 8787 is occupied:** stop the old terminal session, or inspect it with
  `ss -ltnp | grep :8787`.
- **No microphone/audio chunks:** grant browser microphone permission. Linux
  uses browser capture by design, avoiding ALSA/PortAudio selecting an invalid
  VM or hardware device.
- **The first model download fails:** check that IPv4 can reach Hugging Face
  with `getent ahostsv4 huggingface.co`. On an IPv6-only/broken VM connection,
  download the model on another machine and copy the entire
  `python/assets/models` directory before running the setup script again.
- **Samples disappear after a reload:** wait a few seconds; the application
  restores the samples for the current `BANKNAME`. Select Strudel's `voice`
  tab rather than `mix`.

## Current scope

- FastAPI API for starting, stopping, and checking recording sessions.
- Mock and real recorder backends.
- Mock and faster-whisper transcription backends.
- Optional Silero VAD and WhisperX refinement.
- Artifact generation for words, phrases, sentences, letters, metadata, sample manifest, and Strudel import script.
- Static Strudel asset serving.
- PyInstaller launcher support.

## Windows source setup

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m pip install -r requirements.txt
```

For microphone and ASR mode:

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m pip install -r requirements.realtime.txt
```

## Start the Windows source version

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

Open:

```text
http://127.0.0.1:8787/
```

## Endpoints

- `GET /health`
- `POST /start`
- `POST /stop`
- `GET /status`
- `GET /strudel/{session_id}`
- `GET /samples/{session_id}/manifest`
- `GET /metadata/{session_id}`
- `GET /metrics`

## Test

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q
```

## Acceptance

```powershell
cd ..\scripts
powershell -ExecutionPolicy Bypass -File .\final_acceptance.ps1 -SessionId final01
```

## Important environment variables

- `STRUDEL_RECORDER_BACKEND=mock|microphone`
- `STRUDEL_TRANSCRIBER_BACKEND=mock|faster-whisper`
- `STRUDEL_VAD_BACKEND=mock|silero`
- `STRUDEL_ENABLE_VAD=true|false`
- `STRUDEL_ENABLE_REFINEMENT=true|false`
- `STRUDEL_REFINEMENT_BACKEND=mock|whisperx`
- `STRUDEL_SLICE_PADDING_SECONDS=0.04` (margin added to each word/phrase/sentence slice so boundaries are not clipped)
- `STRUDEL_ENABLE_ENERGY_GATE=true|false` + `STRUDEL_MIN_CHUNK_RMS=0.005` (drop near-silent chunks)
- `STRUDEL_WORD_MIN_PROBABILITY=0.45` (drop low-confidence words in noise)
- `STRUDEL_SAMPLES_ROOT=../../samples`
- `STRUDEL_STRUDEL_BASE_URL=http://127.0.0.1:8787`

A ready-to-use noisy-environment preset lives in `.env.realtime.example`
(`cp .env.realtime.example .env`). It enables denoise, the energy gate,
confidence filtering, and Silero VAD together.

## Noise / word-loss evaluation

```powershell
# Dry run (no audio or model required):
python -m scripts.evaluate_noise --selftest

# Paired run: each clip/SNR input is generated once, then reused unchanged for
# denoise off and on.  Keep the saved WAVs and CSV input_sha256 column as an
# audit trail.  Use a distinct input directory and result prefix per seed.
python -m scripts.evaluate_noise --audio-dir data\clips --snr clean 20 10 5 0 --noise white --denoise both --model base --seed 42 --save-noisy-dir results\paired_inputs\seed_42 --out results\noise_eval_seed_42
```

Outputs WER, word-loss rate, hallucination rate per condition and writes
`.json` + `.csv` for the report. The run now stops if `--denoise on` or
`--denoise both` is requested but `noisereduce` is unavailable or fails to
process a WAV; it never silently treats a denoise condition as a no-op.

For a thesis result, repeat the paired command with at least five fixed seeds
(for example 42--46), preserving one result prefix and one `paired_inputs`
directory per seed. Compare the resulting WER values as paired observations;
do not compare conditions generated from different noise draws.

The raw and denoised conditions use the same deterministic noisy waveform for
each clip/SNR pair, so their difference is a paired denoising comparison rather
than an artefact of different random noise draws. The JSON report records the
normalisation rule, SNR reference, seed, ASR configuration, and runtime.

## Clean-audio model and latency benchmark

Use this command for the model-selection table in the thesis. It reports WER,
per-clip latency, real-time factor (RTF), median/p95 latency, and the individual
transcripts used to calculate every aggregate value.

```powershell
python -m scripts.benchmark_models --audio-dir data\clips `
  --models tiny base small --repeats 3 --out results\model_benchmark
```

The benchmark measures only the `faster-whisper` transcription call, excluding
model load and WAV preparation. This scope is recorded in the output JSON and
must be stated when reporting latency in the thesis.

## Build thesis tables from existing results (no model execution)

When a computer cannot run the models, generate the thesis tables directly from
the retained JSON artifacts. This command does not load a model, modify audio,
or download a dependency:

```powershell
python -m scripts.build_thesis_results `
  --results-dir ..\..\Resume-or-Thesis\Thesis\提交版本\experimental_materials\results `
  --out-dir ..\..\Resume-or-Thesis\Thesis\提交版本\experimental_materials\derived_results
```

It writes model and noise CSV tables, a Spanish results fragment, and a
provenance JSON that records the original source files.

On slower hardware, execute the corpus in non-overlapping batches and merge the
raw evidence afterwards. This avoids losing a long run to a time limit while
preserving one row per `(model, clip, repeat)`:

```powershell
python -m scripts.benchmark_models --audio-dir data\clips --models base small `
  --repeats 3 --start-index 0 --max-clips 5 --out results\model_part_00
python -m scripts.benchmark_models --audio-dir data\clips --models base small `
  --repeats 3 --start-index 5 --max-clips 5 --out results\model_part_05
python -m scripts.merge_model_benchmarks results\model_part_*.csv `
  --out results\model_benchmark
```

Relative `STRUDEL_SAMPLES_ROOT` values are resolved from this `code/python` directory, so the service writes to the same place even if it is launched from a different working directory.
