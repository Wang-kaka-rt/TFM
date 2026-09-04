# Strudel Voice

Strudel Voice is a local prototype for recording voice, slicing recognized words, phrases, or sentences into audio samples, and importing them directly into [Strudel](https://strudel.cc) for live coding performance — no code paste required.

---

## How it works

1. Click the **Voice** record button → the browser captures your microphone, the backend transcribes it with faster-whisper, and audio is cut into sentence / phrase / word / syllable / letter samples.
2. Click the button again to stop → the final audio is processed and all samples are finalised.
3. Samples are imported automatically into Strudel. Open the **voice** tab to browse them; after a page reload, samples for the current `BANKNAME` are restored automatically.
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

### Recommended source setup (Ubuntu/Debian)

For a reproducible setup from a fresh clone, use the automated scripts rather
than manually installing Python, Node.js, pnpm, frontend assets, and speech
dependencies.

```bash
git clone <repository-url> strudel-voice
cd strudel-voice/code

# Read-only diagnostic: shows what is installed or missing.
bash scripts/setup_linux_source.sh --check

# Installs missing dependencies, builds Strudel, and downloads the local model.
# The first run needs internet access and sudo permission.
bash scripts/setup_linux_source.sh

# Starts the source version.
bash scripts/run_linux_source.sh
```

The setup script supports Ubuntu/Debian and automatically checks or prepares:

- FFmpeg, PortAudio, libsndfile, Python 3.10+, Node.js 20, and pnpm;
- the Python virtual environment and CPU-only ASR dependencies;
- the Strudel frontend build and static-asset synchronisation;
- the local `faster-whisper` `base` model for later offline launches.

When the terminal prints `Application startup complete.`, open
`http://127.0.0.1:8787/` in Firefox or Chrome and grant microphone permission.
Linux uses browser microphone capture by default, avoiding ALSA/PortAudio
device-selection problems on VMs and different sound cards. Press **Ctrl+C**
to stop the server.

For detailed Linux troubleshooting and configuration, see
[`code/python/README.md`](code/python/README.md).

### Run the portable Linux release

If you received the prebuilt `strudel-voice` release directory instead of the
source code, keep the entire directory together and run:

```bash
cd strudel-voice
chmod +x install.sh strudel-voice
./install.sh       # required once per computer
./strudel-voice
```

No Python, Node.js, pnpm, or model download is required for the portable
release. It supports Ubuntu/Debian x86_64 and still requires a desktop browser
with microphone permission.

---

## macOS

At runtime macOS behaves like Linux: the app starts the backend on
`127.0.0.1:8787` and opens your default browser (no embedded desktop window).

### Requirements

- Python 3.10 or newer
- Node.js 18 or newer + `pnpm`
- System audio libraries via [Homebrew](https://brew.sh):

```bash
brew install ffmpeg portaudio libsndfile
```

### Run in development (no build)

```bash
cd code/python
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

Open `http://127.0.0.1:8787` in a browser. The first time, macOS asks the
terminal app for microphone permission — allow it, or the recorder stays silent.

### Build the app

There is no dedicated macOS build script, so the steps the Linux script performs
are run by hand against the cross-platform spec `strudel-voice.spec` (it bundles
PortAudio / sounddevice and opens a browser instead of a pywebview window).

```bash
# 1. Build the Strudel frontend
cd code/strudel-src-real
pnpm i
pnpm build

# 2. Sync the frontend into the backend's static assets
cd ../python
rm -rf static/strudel && mkdir -p static/strudel
cp -R ../strudel-src-real/website/dist/. static/strudel/

# 3. Build the binary
pip install -r requirements.txt "pyinstaller>=6.11,<7.0"
pyinstaller --noconfirm --clean strudel-voice.spec
```

Output: `code/python/dist/strudel-voice`

### Run

```bash
./dist/strudel-voice
```

The backend starts and your browser opens automatically. Press **Ctrl+C** to stop.

> **First launch (Gatekeeper):** the binary is unsigned, so macOS may block it.
> Clear the quarantine flag once, then run it:
>
> ```bash
> xattr -dr com.apple.quarantine ./dist/strudel-voice
> ```
>
> Build and run on the same CPU architecture (Apple Silicon `arm64` vs Intel
> `x86_64`) — PyInstaller does not cross-compile.

### Use the control panel

Same as Windows/Linux. The **"Voice"** button appears in the bottom-right corner
of the browser page.

| Step | Action |
|------|--------|
| 1 | Click the **"Voice"** button (bottom-right) |
| 2 | Enter a session ID, e.g. `demo01` |
| 3 | Click **Iniciar** to start recording |
| 4 | Click **Detener** to stop and finalize samples |
| 5 | Choose a level: **Oraciones / Frases / Palabras / Letras** |
| 6 | Click **Importar** — samples load into Strudel instantly |
| 7 | Use `s('word')` in the editor to play your voice |

---

## Sample names: `voice` vs `mix`

Every recording is registered into Strudel's sounds panel under **two tabs**, both
pointing at the same audio — pick whichever addressing you prefer:

| Tab | How you call a sample | Example |
|-----|-----------------------|---------|
| **voice** | by its bare text | `s("hola")` (repeats: `s("hola:1")`) |
| **mix** | by level + index | `s("palabra:0")`, `s("oracion:0")`, `s("frase:0")`, `s("silaba:0")`, `s("letra:0")` |

The `mix` level names are **reserved keywords**:

```
oracion · frase · palabra · silaba · letra
```

Avoid recording one of these five words as actual content. Sample names are
global in Strudel, so a recorded word that equals a reserved name (e.g. you say
*"palabra"*) collides with the `mix` group of the same name — the bare `voice`
name then overrides the `mix` indexing for that word. Any other word is fine.

---

## Optional: heavier ASR stack

To enable WhisperX forced alignment for higher-precision slicing:

```bash
cd code/python
pip install -r requirements.realtime.txt
```

Set `STRUDEL_REFINEMENT_BACKEND=whisperx` before running.

---

## Calibration & noise robustness

Word slices no longer clip their first/last consonant: every word / phrase /
sentence cut is widened by `STRUDEL_SLICE_PADDING_SECONDS` (default `0.04`) on
each side, clamped to the recording. Tune it if cuts still sound tight.

For noisy rooms, copy the ready-made preset, which turns on spectral-gating
denoise, the near-silence energy gate, low-confidence word dropping, and Silero
VAD:

```bash
cd code/python
cp .env.realtime.example .env
pip install -r requirements.realtime.txt   # noisereduce, silero-vad, etc.
```

### Measuring it (thesis data)

`scripts/evaluate_noise.py` mixes noise into labelled clips at several SNR levels
and reports Word Error Rate, **word-loss rate** (deletions), hallucination rate,
and the denoise on/off effect — writing a `.json` + `.csv` for the report.

```bash
cd code/python
# Dry run, no audio/model needed (checks the harness works):
python3 -m scripts.evaluate_noise --selftest

# Real evaluation over your own clips (clip.wav + clip.txt transcript pairs):
python3 -m scripts.evaluate_noise --audio-dir data/clips \
    --snr clean 20 10 5 0 --denoise both --model base --out results/noise_eval
```

## Tests

```bash
cd code/python
python3 -m pytest -q
```

---

## Full build reference

See [`BUILD_COMMANDS.md`](BUILD_COMMANDS.md) for all build options and flags.
