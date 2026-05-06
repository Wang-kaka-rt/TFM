# Strudel Voice

Strudel Voice is a local prototype for recording voice, slicing recognized words or phrases into samples, and importing the generated sample manifest into Strudel.

## Project layout

- `code/python`: FastAPI backend. It records audio, transcribes chunks, exports samples, writes metadata, and serves the bundled Strudel static site.
- `code/node`: NestJS bridge. It forwards Strudel control requests to the Python backend.
- `code/strudel-src-real`: upstream Strudel source used to build static assets.
- `samples`: generated session artifacts.

## Quick check

Use the Python 3.12 interpreter that has the project dependencies installed:

```powershell
cd code\python
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q
```

Build the Node bridge:

```powershell
cd code\node
npm run build
```

## Run in development

Python backend:

```powershell
cd code\python
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

Node bridge:

```powershell
cd code\node
npm run start
```

## Acceptance test

With both services running:

```powershell
cd code\scripts
powershell -ExecutionPolicy Bypass -File .\final_acceptance.ps1 -SessionId final01
```

For reliable local validation, use `mock` backends first. Real microphone and ASR mode depends on local audio devices and model dependencies.
