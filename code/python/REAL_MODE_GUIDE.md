# Real Mode Guide

Real mode uses the microphone, faster-whisper, and optional Silero VAD. Start with mock mode for acceptance tests, then switch one real backend on at a time.

## 1. Install dependencies

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m pip install -r requirements.realtime.txt
```

FFmpeg is recommended for reliable audio slicing. Put `ffmpeg.exe` in `PATH` or package it under `assets\ffmpeg`.

## 2. Configure `.env`

```text
STRUDEL_RECORDER_BACKEND=microphone
STRUDEL_TRANSCRIBER_BACKEND=faster-whisper
STRUDEL_VAD_BACKEND=silero
STRUDEL_ENABLE_VAD=true
STRUDEL_ENABLE_REFINEMENT=false
```

If the wrong input device is selected, set:

```text
STRUDEL_MICROPHONE_DEVICE=0
```

Change `0` to the device index you want.

## 3. Run backend

```powershell
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

## 4. Manual verification

```powershell
$body = @{ session_id = "real01" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8787/start" -Method POST -ContentType "application/json" -Body $body
Start-Sleep -Seconds 5
Invoke-RestMethod -Uri "http://127.0.0.1:8787/stop" -Method POST -ContentType "application/json" -Body $body
Invoke-RestMethod -Uri "http://127.0.0.1:8787/status?session_id=real01" -Method GET
```

If `/start` fails, the API now returns the failing operation in the response body. Also check `last_error` from `/status`.
