#!/usr/bin/env bash
# Start the Strudel Voice source checkout on Linux after setup_linux_source.sh.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_DIR="$ROOT_DIR/python"
VENV_DIR="$PYTHON_DIR/.venv"
MODEL_DIR="$PYTHON_DIR/assets/models"
MODEL_GLOB="$MODEL_DIR/models--Systran--faster-whisper-base/snapshots/*/model.bin"

python_runtime_ok() {
  [[ -x "$VENV_DIR/bin/python" ]] && "$VENV_DIR/bin/python" -c '
import fastapi
import multipart
import uvicorn
import faster_whisper
' >/dev/null 2>&1
}

if [[ ! -x "$VENV_DIR/bin/python" || ! -f "$PYTHON_DIR/static/strudel/index.html" ]] \
  || ! python_runtime_ok \
  || ! compgen -G "$MODEL_GLOB" > /dev/null; then
  echo "Source environment is incomplete or has outdated dependencies; running setup..."
  bash "$ROOT_DIR/scripts/setup_linux_source.sh"
fi

# Setup may have been interrupted or a package installation may have failed.
# Fail with a precise diagnostic rather than starting Uvicorn with a broken API.
if ! python_runtime_ok; then
  echo "Python runtime dependencies are still missing (including python-multipart)." >&2
  exit 1
fi
if ! compgen -G "$MODEL_GLOB" > /dev/null; then
  echo "The offline base model is still missing after setup." >&2
  exit 1
fi

source "$VENV_DIR/bin/activate"
export STRUDEL_RECORDER_BACKEND=browser
export STRUDEL_TRANSCRIBER_BACKEND=faster-whisper
export STRUDEL_FASTER_WHISPER_MODEL=base
export STRUDEL_FASTER_WHISPER_DEVICE=cpu
export STRUDEL_FASTER_WHISPER_COMPUTE_TYPE=int8
export STRUDEL_FASTER_WHISPER_DOWNLOAD_ROOT="$MODEL_DIR"
export HF_HUB_OFFLINE=1
export STRUDEL_SAMPLES_ROOT="$ROOT_DIR/samples"

cd "$PYTHON_DIR"
exec python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
