# Strudel Voice Python Backend

## Current scope

- FastAPI API for starting, stopping, and checking recording sessions.
- Mock and real recorder backends.
- Mock and faster-whisper transcription backends.
- Optional Silero VAD and WhisperX refinement.
- Artifact generation for words, phrases, sentences, letters, metadata, sample manifest, and Strudel import script.
- Static Strudel asset serving.
- PyInstaller launcher support.

## Install

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m pip install -r requirements.txt
```

For microphone and ASR mode:

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m pip install -r requirements.realtime.txt
```

## Run

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

Relative `STRUDEL_SAMPLES_ROOT` values are resolved from this `code/python` directory, so the service writes to the same place even if it is launched from a different working directory.
