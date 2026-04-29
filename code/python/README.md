# Strudel Voice Python Backend

## Current scope
- Sprint 0-4 implemented: API flow, chunk export, artifacts, static service, metrics, tests
- Sprint 5 packaging ready: PyInstaller + PyWebView launcher with startup retry and log files

## Run
```bash
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

## Realtime mode (microphone + faster-whisper)
- Install realtime dependencies:
```bash
py -m pip install -r requirements.realtime.txt
```
- Copy `.env.realtime.example` to `.env` and adjust `STRUDEL_MICROPHONE_DEVICE` if needed.
- Note: if optional dependencies are missing, backend now auto-falls back to `mock` and keeps running.

## Final acceptance
```powershell
cd ..\scripts
pwsh -ExecutionPolicy Bypass -File .\final_acceptance.ps1
```

## Config template
- Copy `.env.example` to `.env` and edit values as needed.

## Available endpoints
- `GET /health`
- `POST /start`
- `POST /reload`
- `POST /stop`
- `GET /status`
- `GET /strudel/{session_id}`
- `GET /samples/{session_id}/manifest`
- `GET /metadata/{session_id}`
- `GET /metrics`

## Useful env vars
- `STRUDEL_RECORDER_BACKEND=mock|microphone`
- `STRUDEL_TRANSCRIBER_BACKEND=mock|faster-whisper`
- `STRUDEL_FASTER_WHISPER_MODEL=base|small|medium|...`
- `STRUDEL_FASTER_WHISPER_DEVICE=auto|cpu|cuda`
- `STRUDEL_FASTER_WHISPER_COMPUTE_TYPE=int8|float16|float32`
- `STRUDEL_FASTER_WHISPER_BEAM_SIZE=1|2|...`
- `STRUDEL_VAD_BACKEND=mock|silero`
- `STRUDEL_ENABLE_REFINEMENT=true|false`
- `STRUDEL_REFINEMENT_BACKEND=mock|whisperx`
- `STRUDEL_MICROPHONE_DEVICE=<input-device-index>`
- `STRUDEL_SAMPLES_ROOT=...`
- `STRUDEL_MAX_CHUNKS_PER_SESSION=...`
- `STRUDEL_CHUNK_DURATION_SECONDS=...`

## Example request
```bash
curl -X POST http://127.0.0.1:8787/start ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"test01\"}"
```

## Strudel commands in editor
- The launcher injects `strudelVoiceStart`, `strudelVoiceReload`, `strudelVoiceStop` automatically.
- Run these in the Strudel editor:
```javascript
await strudelVoiceStart()
await strudelVoiceReload()
await strudelVoiceStop()
```
