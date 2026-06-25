# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_all

datas = [('static', 'static')]
binaries = []
hiddenimports = ['uvicorn', 'uvicorn.config', 'uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.protocols.http.auto', 'uvicorn.lifespan.on', 'app.main', 'app.api.routes', 'faster_whisper', 'ctranslate2', 'tokenizers', 'silero_vad', 'huggingface_hub', 'av', 'sounddevice', '_cffi_backend']

datas += collect_data_files('app')

# Collect package data files plus native shared libraries (.dylib/.so/portaudio)
# that are NOT picked up by hiddenimports alone.
for _pkg in ('faster_whisper', 'ctranslate2', 'tokenizers', 'silero_vad', 'av', 'sounddevice', '_sounddevice_data'):
    _datas, _binaries, _hidden = collect_all(_pkg)
    datas += _datas
    binaries += _binaries
    hiddenimports += _hidden


a = Analysis(
    ['packaging/launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'whisperx', 'tensorflow', 'keras', 'pandas', 'scipy', 'sklearn', 'cv2', 'numba', 'matplotlib', 'IPython', 'jupyter_client', 'pytest'],
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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
