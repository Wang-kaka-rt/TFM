# Build & Usage Guide

This file covers how to build and run Strudel Voice on both Windows and Linux.

Repository layout:

- `code/python` — FastAPI backend (recording, transcription, slicing, sample export)
- `code/strudel-src-real` — upstream Strudel source, built into the frontend assets
- `code/node` — NestJS bridge service (optional)

---

## Windows

### Requirements

- Python 3.10 or newer
- Node.js 18 or newer + `pnpm`
- FFmpeg (bundled automatically if placed in `code/python/assets/ffmpeg/ffmpeg.exe`,
  otherwise installed system-wide via `winget install ffmpeg`)

### Build the EXE

The build script installs all Python dependencies, copies the Strudel frontend, and
produces a single `strudel-voice.exe` that runs without Python installed.

**Step 1 — Build the Strudel frontend:**

```powershell
cd code\strudel-src-real
pnpm i
pnpm build
```

**Step 2 — Build the EXE:**

```powershell
cd code\python
pwsh -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

Output: `code\python\dist\strudel-voice.exe`

Optional build flags:

| Flag | Description |
|------|-------------|
| `-IncludeHeavyAsr` | Bundle the heavier WhisperX / torch ASR stack |
| `-PythonExe <path>` | Point to a specific Python interpreter |
| `-SkipSyncStrudel` | Skip copying Strudel assets (if `static\strudel` already exists) |

### Run on Windows

Double-click `strudel-voice.exe`, or run from the terminal:

```powershell
.\dist\strudel-voice.exe
```

An embedded desktop window opens automatically (powered by pywebview).
The voice control panel appears as a floating **"Voice"** button in the bottom-right corner.

### Use the voice control panel (Windows)

1. Click the **"Voice"** button (bottom-right corner of the window).
2. Enter a **session ID** (e.g. `demo01`).
3. Click **Iniciar** — recording starts, audio is chunked and transcribed in real time.
4. Click **Detener** — recording stops and all samples are finalized.
5. Select a granularity level: **Oraciones** / **Frases** / **Palabras** / **Letras**.
6. Click **Importar** — samples are registered directly into Strudel.
7. In the Strudel code editor, use `s('word')` to play a sample immediately.

### Run in development (Windows, no EXE)

Install dependencies once:

```powershell
cd code\python
pip install -r requirements.txt
```

Start the backend:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

Open a browser at `http://127.0.0.1:8787`.

---

## Linux

### Requirements

- Python 3.10 or newer
- Node.js 18 or newer + `pnpm`
- System audio libraries (installed once, listed below)

**Install system dependencies (Ubuntu / Debian):**

```bash
sudo apt install ffmpeg portaudio19-dev libsndfile1
```

**Install system dependencies (Fedora / RHEL):**

```bash
sudo dnf install ffmpeg portaudio-devel libsndfile
```

### Build the binary

The build script produces a single self-contained executable.
Python and all pip packages are bundled inside — no Python installation needed to run it.

**Step 1 — Build the Strudel frontend:**

```bash
cd code/strudel-src-real
pnpm i
pnpm build
```

**Step 2 — Build the binary:**

```bash
cd code/python
chmod +x scripts/build_linux.sh
./scripts/build_linux.sh
```

Output: `code/python/dist/strudel-voice`

Optional build flags:

| Flag | Description |
|------|-------------|
| `--include-heavy-asr` | Bundle the heavier WhisperX / torch ASR stack |
| `--strudel-dist PATH` | Custom path to the Strudel website build output |
| `--skip-sync-strudel` | Skip copying Strudel assets (if `static/strudel` already exists) |

### Run on Linux

```bash
./dist/strudel-voice
```

The backend starts on `127.0.0.1:8787` and opens your default browser automatically.
Press **Ctrl+C** to stop.

> Note: the binary must be run on a Linux system with glibc version equal to or newer
> than the system it was built on. Build on Ubuntu 20.04 for the widest compatibility.

### Use the voice control panel (Linux)

The workflow is identical to Windows. The control panel is served as part of the
Strudel page — no desktop window required.

1. The browser opens `http://127.0.0.1:8787` automatically.
2. Click the **"Voice"** button (bottom-right corner of the page).
3. Enter a **session ID** (e.g. `demo01`).
4. Click **Iniciar** — recording starts.
5. Click **Detener** — recording stops and samples are finalized.
6. Select a granularity level: **Oraciones** / **Frases** / **Palabras** / **Letras**.
7. Click **Importar** — samples are registered directly into Strudel.
8. In the Strudel code editor, use `s('word')` to play a sample immediately.

### Run in development (Linux, no binary)

Install dependencies once:

```bash
cd code/python
pip install -r requirements.txt
```

Start the backend:

```bash
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

Open a browser at `http://127.0.0.1:8787`.

---

## Common: Python tests

```bash
cd code/python
python3 -m pytest -q
```

## Common: Strudel frontend (standalone build)

Only needed if you want to rebuild the frontend independently of the packaging steps above.

```bash
cd code/strudel-src-real
pnpm i
pnpm build
# Output: code/strudel-src-real/website/dist
```

## Common: Node bridge (optional)

```bash
cd code/node
npm install
npm run build       # production build
npm run start:dev   # development mode
```
