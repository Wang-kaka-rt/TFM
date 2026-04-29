# Packaging Guide (Sprint 5)

## Goal
- Build a Windows EXE that starts local backend and opens desktop window.

## Prerequisites
- Python 3.10+
- `py` launcher
- Optional: Node bridge already built and tested

## Build
```powershell
cd code/python
pwsh -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

- Default build excludes heavy ASR dependencies (`torch`/`whisperx`/`faster_whisper`) for faster packaging.
- To include heavy ASR runtime:
```powershell
cd code/python
pwsh -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1 -IncludeHeavyAsr
```

## Output
- `code/python/dist/strudel-voice.exe`

## Runtime behavior
- EXE starts backend on `127.0.0.1:8787` and opens `http://127.0.0.1:8787`.
- If an existing healthy backend is already running on this port, launcher reuses it.
- If backend startup fails, launcher retries automatically and writes logs to:
  - `%LOCALAPPDATA%\StrudelVoice\logs\launcher.log`
  - `%LOCALAPPDATA%\StrudelVoice\logs\backend.log`

## Asset packaging
- `build_exe.ps1` auto-includes these directories when present:
  - `assets/ffmpeg`
  - `assets/models`
  - `static`
