# Strudel Voice

Strudel Voice is a local prototype for recording voice, slicing recognized words, phrases, or sentences into audio samples, and importing them directly into [Strudel](https://strudel.cc) for live coding performance — no code paste required.

---

## How it works

1. Click **Iniciar** in the floating panel → the backend records your voice in chunks, transcribes each chunk with faster-whisper, and slices the audio into word / phrase / sentence / letter samples in real time.
2. Click **Detener** → recording stops and all samples are finalized.
3. Select a granularity level and click **Importar** → samples are registered directly into Strudel's sound engine.
4. Type `s('hola')` in the Strudel editor → your voice plays.

---

## Project layout

```
code/
  python/           FastAPI backend — recording, transcription, slicing, sample export
  node/             NestJS bridge service (optional)
  strudel-src-real/ upstream Strudel source, built into the frontend assets
samples/            generated session artifacts (created at runtime)
```

---

## Windows

### Requirements

- Python 3.10 or newer
- Node.js 18 or newer + `pnpm`
- FFmpeg (place `ffmpeg.exe` in `code/python/assets/ffmpeg/` or install system-wide)

### Build the EXE

```powershell
# 1. Build Strudel frontend
cd code\strudel-src-real
pnpm i
pnpm build

# 2. Build the EXE
cd code\python
pwsh -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

Output: `code\python\dist\strudel-voice.exe`

No Python installation needed to run the EXE.

### Run

Double-click `strudel-voice.exe`, or:

```powershell
.\dist\strudel-voice.exe
```

An embedded desktop window opens. The **"Voice"** button appears in the bottom-right corner.

### Use the control panel

| Step | Action |
|------|--------|
| 1 | Click the **"Voice"** button (bottom-right) |
| 2 | Enter a session ID, e.g. `demo01` |
| 3 | Click **Iniciar** to start recording |
| 4 | Click **Detener** to stop and finalize samples |
| 5 | Choose a level: **Oraciones / Frases / Palabras / Letras** |
| 6 | Click **Importar** — samples load into Strudel instantly |
| 7 | Use `s('word')` in the editor to play your voice |

### Run in development (no EXE)

```powershell
cd code\python
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

Open `http://127.0.0.1:8787` in a browser.

---

## Linux

### Requirements

- Python 3.10 or newer
- Node.js 18 or newer + `pnpm`
- System audio libraries

**Ubuntu / Debian:**

```bash
sudo apt install ffmpeg portaudio19-dev libsndfile1
```

**Fedora / RHEL:**

```bash
sudo dnf install ffmpeg portaudio-devel libsndfile
```

### Build the binary

```bash
# 1. Build Strudel frontend
cd code/strudel-src-real
pnpm i
pnpm build

# 2. Build the binary
cd code/python
chmod +x scripts/build_linux.sh
./scripts/build_linux.sh
```

Output: `code/python/dist/strudel-voice`

Python and all pip packages are bundled inside — no Python installation needed to run it.

### Run

```bash
./dist/strudel-voice
```

The backend starts on `127.0.0.1:8787` and opens your default browser automatically.
Press **Ctrl+C** to stop.

### Use the control panel

Same as Windows. The **"Voice"** button appears in the bottom-right corner of the browser page.

| Step | Action |
|------|--------|
| 1 | Click the **"Voice"** button (bottom-right) |
| 2 | Enter a session ID, e.g. `demo01` |
| 3 | Click **Iniciar** to start recording |
| 4 | Click **Detener** to stop and finalize samples |
| 5 | Choose a level: **Oraciones / Frases / Palabras / Letras** |
| 6 | Click **Importar** — samples load into Strudel instantly |
| 7 | Use `s('word')` in the editor to play your voice |

### Run in development (no binary)

```bash
cd code/python
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

Open `http://127.0.0.1:8787` in a browser.

---

## Optional: heavier ASR stack

To enable WhisperX forced alignment for higher-precision slicing:

```bash
cd code/python
pip install -r requirements.realtime.txt
```

Set `STRUDEL_REFINEMENT_BACKEND=whisperx` before running.

---

## Tests

```bash
cd code/python
python3 -m pytest -q
```

---

## Full build reference

See [`BUILD_COMMANDS.md`](BUILD_COMMANDS.md) for all build options and flags.
