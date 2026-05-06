# Build Commands

This file is aligned with the current repository layout:

- `code/python`: FastAPI backend for recording, transcription, slicing, and sample export
- `code/node`: NestJS bridge service
- `code/strudel-src-real`: upstream Strudel source used to build the frontend assets

## Python backend dependencies

Use your active Python 3.12 environment from `code/python`.

```bash
cd code/python
python3 -m pip install -r requirements.txt
```

For the heavier realtime stack, including `torch` and `whisperx`:

```bash
cd code/python
python3 -m pip install -r requirements.realtime.txt
```

Notes:

- `requirements.txt` is the default runtime dependency set
- `requirements.realtime.txt` extends the default set with heavier ASR and refinement dependencies

## Python tests

```bash
cd code/python
python3 -m pytest -q
```

## Python backend run

```bash
cd code/python
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

## Node bridge

Build:

```bash
cd code/node
npm install
npm run build
```

Run in development:

```bash
cd code/node
npm install
npm run start:dev
```

## Strudel frontend assets

The Python app serves Strudel from `code/python/static/strudel` when that directory exists.
The packaging script populates it from `code/strudel-src-real/website/dist`, so build the
Strudel website before packaging.

Install workspace dependencies and build the upstream Strudel website:

```bash
cd code/strudel-src-real
pnpm i
pnpm build
```

Requirements:

- Node.js 18 or newer
- `pnpm`

## Desktop EXE (Windows only)

This step is only for Windows packaging. It does not apply to normal macOS development.

1. Build the Strudel frontend assets first:

```powershell
cd code\strudel-src-real
pnpm i
pnpm build
```

2. Then build the EXE:

```powershell
cd code\python
pwsh -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

Optional:

- Add `-IncludeHeavyAsr` only when you want to bundle the heavier ASR stack
- Use `-PythonExe <path-to-python.exe>` if the script cannot find a usable Python interpreter

Do not use `-SkipSyncStrudel` unless `code/python/static/strudel` has already been prepared,
because the current repository does not ship that directory by default.
