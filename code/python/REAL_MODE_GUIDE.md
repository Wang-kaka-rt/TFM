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

## 2b. Noisy environments

When recording with background noise, layer these guards on top of real mode.
All default to off, so enable them only when needed:

```text
# Reject low-confidence / non-speech audio inside faster-whisper
STRUDEL_FASTER_WHISPER_VAD_FILTER=true
STRUDEL_FASTER_WHISPER_NO_SPEECH_THRESHOLD=0.6

# Drop transcribed words whose ASR probability is too low (noise artifacts)
STRUDEL_WORD_MIN_PROBABILITY=0.45

# Tighten Silero VAD so weak/noisy segments are discarded
STRUDEL_SILERO_SPEECH_THRESHOLD=0.65
STRUDEL_MIN_WORD_DURATION_SECONDS=0.08

# Spectral-gating denoise before ASR (needs noisereduce, in requirements.realtime.txt)
STRUDEL_ENABLE_DENOISE=true
STRUDEL_DENOISE_BACKEND=noisereduce
# 0.6 (gentle, keeps more voice) .. 0.9 (aggressive, removes more noise)
STRUDEL_DENOISE_PROP_DECREASE=0.8
# false = non-stationary (default, preserves voice better for varying noise)
# true  = stationary (best only for a constant hum; over-attenuates speech)
STRUDEL_DENOISE_STATIONARY=false

# Skip near-silent chunks entirely (tune min RMS to your room, 0..1)
STRUDEL_ENABLE_ENERGY_GATE=true
STRUDEL_MIN_CHUNK_RMS=0.005
```

The pipeline becomes: denoise → energy gate → faster-whisper (anti-hallucination)
→ confidence filter → Silero VAD → slicing. `/metrics` reports
`denoised_chunk_count`, `energy_gated_chunk_count`, and `low_confidence_word_drops`
so you can quantify each guard's effect (useful for the thesis experiments).

The strongest single improvement is still at capture time: use a close,
directional/headset microphone, or add a push-to-talk control on the panel.

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
