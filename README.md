# Strudel Voice

Strudel Voice is a local prototype for recording voice, slicing recognized words or phrases into samples, and importing the generated sample manifest into Strudel.

## Project layout

- `code/python`: FastAPI backend. It records audio, transcribes chunks, exports samples, writes metadata, and serves the bundled Strudel static site.
- `code/node`: NestJS bridge. It forwards Strudel control requests to the Python backend.
- `code/strudel-src-real`: upstream Strudel source used to build static assets.
- `samples`: generated session artifacts.

## Prerequisites

- Python 3.12
- Node.js 18 or newer
- `npm`
- `pnpm` for building the upstream Strudel frontend

## Quick check

Install Python dependencies:

```bash
cd code/python
python3 -m pip install -r requirements.txt
```

Run Python tests:

```bash
cd code/python
python3 -m pytest -q
```

Build the Node bridge:

```bash
cd code/node
npm install
npm run build
```

## Run in development

Python backend:

```bash
cd code/python
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

Node bridge:

```bash
cd code/node
npm install
npm run start:dev
```

## Optional realtime dependencies

For the heavier realtime stack, including `torch` and `whisperx`:

```bash
cd code/python
python3 -m pip install -r requirements.realtime.txt
```

## Strudel frontend assets

The Python backend serves Strudel from `code/python/static/strudel` when that directory exists.
For normal backend and bridge development, you do not need to build these assets first.

Build them before desktop packaging:

```bash
cd code/strudel-src-real
pnpm i
pnpm build
```

## Acceptance test

With both services running:

```powershell
cd code\scripts
powershell -ExecutionPolicy Bypass -File .\final_acceptance.ps1 -SessionId final01
```

For reliable local validation, use `mock` backends first. Real microphone and ASR mode depends on local audio devices and model dependencies.

## Build Notes

- `BUILD_COMMANDS.md` contains the repository-aligned build commands
- Windows EXE packaging is handled by `code/python/scripts/build_exe.ps1`
- Do not use `-SkipSyncStrudel` for packaging unless `code/python/static/strudel` has already been prepared
