# Build Commands

## Python backend dependencies

```powershell
cd code\python
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m pip install -r requirements.txt
```

For real microphone and ASR mode:

```powershell
cd code\python
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m pip install -r requirements.realtime.txt
```

## Python tests

```powershell
cd code\python
C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q
```

## Node bridge

```powershell
cd code\node
npm install
npm run build
```

## Desktop EXE

```powershell
cd code\python
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1 -SkipSyncStrudel
```

Add `-IncludeHeavyAsr` only when you want to package the heavier real ASR dependencies.
