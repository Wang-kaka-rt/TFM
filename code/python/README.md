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
- `STRUDEL_SAMPLES_ROOT=../../samples`
- `STRUDEL_STRUDEL_BASE_URL=http://127.0.0.1:8787`

Relative `STRUDEL_SAMPLES_ROOT` values are resolved from this `code/python` directory, so the service writes to the same place even if it is launched from a different working directory.
