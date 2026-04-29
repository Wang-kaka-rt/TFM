# Real Mode Switch Guide

## 0) Audio stack: FFmpeg + pydub
- Install dependency:
  - `py -m pip install pydub`
- Install FFmpeg and ensure `ffmpeg` is in PATH, or place binaries under `assets/ffmpeg` for EXE packaging.

## 1) Recorder: microphone
- Install dependency:
  - `py -m pip install sounddevice`
- Update `.env`:
  - `STRUDEL_RECORDER_BACKEND=microphone`
  - Optional (pick input device index):
    - `STRUDEL_MICROPHONE_DEVICE=1`

## 2) ASR: faster-whisper
- Install dependency:
  - `py -m pip install faster-whisper`
- Update `.env`:
  - `STRUDEL_TRANSCRIBER_BACKEND=faster-whisper`
  - `STRUDEL_FASTER_WHISPER_MODEL=small`
  - `STRUDEL_FASTER_WHISPER_DEVICE=auto`
  - `STRUDEL_FASTER_WHISPER_COMPUTE_TYPE=int8`
  - `STRUDEL_FASTER_WHISPER_BEAM_SIZE=1`

## 3) VAD: silero
- Install dependency:
  - `py -m pip install torch`
- Update `.env`:
  - `STRUDEL_ENABLE_VAD=true`
  - `STRUDEL_VAD_BACKEND=silero`

## 4) Refinement: whisperx
- Install dependency:
  - `py -m pip install whisperx`
- Update `.env`:
  - `STRUDEL_ENABLE_REFINEMENT=true`
  - `STRUDEL_REFINEMENT_BACKEND=whisperx`

## 5) Verify flow
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8787/start" -Method POST -ContentType "application/json" -Body '{"session_id":"real01"}'
Start-Sleep -Seconds 3
Invoke-RestMethod -Uri "http://127.0.0.1:8787/reload" -Method POST -ContentType "application/json" -Body '{"session_id":"real01"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8787/stop" -Method POST -ContentType "application/json" -Body '{"session_id":"real01"}'
```
