# -*- mode: python ; coding: utf-8 -*-
# Windows packaging spec for Strudel Voice.
#   Build on Windows:  pyinstaller strudel-voice-windows.spec
# PyInstaller cannot cross-compile, so this must run on a Windows machine.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

project_root = Path.cwd()

datas = [('static', 'static')]
binaries = []
# Windows uses an embedded pywebview window, so its backend modules must be
# bundled explicitly (they are imported dynamically at runtime).
hiddenimports = [
    'uvicorn', 'uvicorn.config', 'uvicorn.logging',
    'uvicorn.loops.auto', 'uvicorn.protocols.http.auto', 'uvicorn.lifespan.on',
    'app.main', 'app.api.routes', 'app.services.panel',
    'faster_whisper', 'ctranslate2', 'tokenizers', 'silero_vad',
    'huggingface_hub', 'av', 'sounddevice', '_cffi_backend',
    # pywebview Windows (EdgeChromium / WinForms) backend
    'webview', 'webview.platforms.winforms', 'clr',
]

datas += collect_data_files('app')

# Bundle package data files AND native libraries (DLLs / portaudio / ffmpeg libs
# inside av) that hiddenimports alone does not pull in.
for _pkg in (
    'faster_whisper', 'ctranslate2', 'tokenizers', 'silero_vad',
    'av', 'sounddevice', '_sounddevice_data', 'webview',
):
    _datas, _binaries, _hidden = collect_all(_pkg)
    datas += _datas
    binaries += _binaries
    hiddenimports += _hidden

# Optional: include a bundled FFmpeg and/or a Windows-on-ARM PortAudio DLL if
# present in the project tree. Drop them in these relative paths to ship them;
# otherwise the app falls back to FFmpeg on PATH and the stock PortAudio build.
_optional_assets = [
    (project_root / 'assets' / 'ffmpeg', 'assets/ffmpeg'),
    (
        project_root / 'assets' / 'portaudio' / 'libportaudioarm64.dll',
        '_sounddevice_data/portaudio-binaries',
    ),
]
for _src, _dest in _optional_assets:
    if _src.exists():
        datas.append((str(_src), _dest))


a = Analysis(
    ['packaging/launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'whisperx', 'tensorflow', 'keras', 'tf_keras',
        'pandas', 'pyarrow', 'scipy', 'sklearn', 'cv2',
        'numba', 'llvmlite', 'matplotlib', 'IPython', 'jupyter_client',
        'pytest',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='strudel-voice',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
