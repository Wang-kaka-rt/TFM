#!/usr/bin/env bash
# Build a self-contained Linux binary for Strudel Voice.
#
# Usage:
#   ./scripts/build_linux.sh [--include-heavy-asr] [--strudel-dist PATH] [--skip-sync-strudel]
#
# Requirements (Ubuntu/Debian):
#   sudo apt install python3.10+ ffmpeg libsndfile1 portaudio19-dev
#   pip install -r requirements.txt
#
# The produced binary is dist/strudel-voice (no extension).
# It opens a system browser at http://127.0.0.1:8787 on launch.

set -euo pipefail

INCLUDE_HEAVY_ASR=false
STRUDEL_DIST="../strudel-src-real/website/dist"
SKIP_SYNC_STRUDEL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --include-heavy-asr) INCLUDE_HEAVY_ASR=true ;;
        --strudel-dist)      STRUDEL_DIST="$2"; shift ;;
        --skip-sync-strudel) SKIP_SYNC_STRUDEL=true ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
    shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ── 0. Pre-flight checks ────────────────────────────────────────────────────
if [[ ! -f "requirements.txt" ]]; then
    echo "ERROR: requirements.txt not found in $PROJECT_ROOT" >&2; exit 1
fi
if [[ ! -f "packaging/launcher.py" ]]; then
    echo "ERROR: packaging/launcher.py not found" >&2; exit 1
fi

# ── 1. Sync Strudel static assets ───────────────────────────────────────────
if [[ "$SKIP_SYNC_STRUDEL" == false ]]; then
    STRUDEL_DIST_ABS="$(realpath "$PROJECT_ROOT/$STRUDEL_DIST" 2>/dev/null || echo "$STRUDEL_DIST")"
    if [[ ! -f "$STRUDEL_DIST_ABS/index.html" ]]; then
        echo "ERROR: Strudel dist not found at $STRUDEL_DIST_ABS (missing index.html)." >&2
        echo "       Build the Strudel website first:" >&2
        echo "         cd code/strudel-src-real && pnpm i && pnpm build" >&2
        exit 1
    fi
    STRUDEL_TARGET="$PROJECT_ROOT/static/strudel"
    rm -rf "$STRUDEL_TARGET"
    mkdir -p "$STRUDEL_TARGET"
    cp -r "$STRUDEL_DIST_ABS/." "$STRUDEL_TARGET/"
    echo "✓ Synced Strudel assets: $STRUDEL_DIST_ABS → $STRUDEL_TARGET"
fi

# ── 2. Install runtime dependencies ─────────────────────────────────────────
echo "[1/3] Installing runtime dependencies..."
if [[ "$INCLUDE_HEAVY_ASR" == true ]]; then
    python3 -m pip install -r requirements.realtime.txt
else
    python3 -m pip install -r requirements.txt
fi

# ── 3. Install PyInstaller (no pywebview needed on Linux) ───────────────────
echo "[2/3] Installing PyInstaller..."
python3 -m pip install "pyinstaller>=6.11,<7.0"

# ── 4. Build binary ──────────────────────────────────────────────────────────
echo "[3/3] Building binary with PyInstaller..."

PYINSTALLER_ARGS=(
    --noconfirm
    --clean
    --name strudel-voice
    --onefile
    --collect-data app
    --hidden-import uvicorn
    --hidden-import uvicorn.config
    --hidden-import uvicorn.logging
    --hidden-import uvicorn.loops.auto
    --hidden-import "uvicorn.protocols.http.auto"
    --hidden-import "uvicorn.lifespan.on"
    --hidden-import app.main
    --hidden-import app.api.routes
    --hidden-import app.services.panel
    --hidden-import faster_whisper
    --hidden-import ctranslate2
    --hidden-import tokenizers
    --hidden-import huggingface_hub
    --hidden-import av
    --collect-all faster_whisper
    --collect-all ctranslate2
    --collect-all tokenizers
    --exclude-module webview
)

if [[ "$INCLUDE_HEAVY_ASR" == false ]]; then
    PYINSTALLER_ARGS+=(
        --exclude-module torch
        --exclude-module whisperx
        --exclude-module tensorflow
        --exclude-module keras
        --exclude-module tf_keras
        --exclude-module pandas
        --exclude-module pyarrow
        --exclude-module scipy
        --exclude-module sklearn
        --exclude-module cv2
        --exclude-module numba
        --exclude-module llvmlite
        --exclude-module matplotlib
        --exclude-module IPython
        --exclude-module jupyter_client
        --exclude-module pytest
    )
fi

# Optional bundled assets
for ASSET in "assets/ffmpeg" "assets/models" "static"; do
    if [[ -d "$ASSET" ]]; then
        PYINSTALLER_ARGS+=(--add-data "$ASSET:$ASSET")
        echo "  Including asset: $ASSET"
    fi
done

python3 -m PyInstaller "${PYINSTALLER_ARGS[@]}" packaging/launcher.py

echo ""
echo "✓ Build complete: dist/strudel-voice"
echo ""
echo "Run with:"
echo "  ./dist/strudel-voice"
echo ""
echo "System dependencies required at runtime (Ubuntu/Debian):"
echo "  sudo apt install ffmpeg portaudio19-dev libsndfile1"
