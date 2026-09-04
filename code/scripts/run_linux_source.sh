#!/usr/bin/env bash
# Start the Strudel Voice source checkout on Linux after setup_linux_source.sh.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_DIR="$ROOT_DIR/python"
VENV_DIR="$PYTHON_DIR/.venv"
MODEL_DIR="$PYTHON_DIR/assets/models"
MODEL_GLOB="$MODEL_DIR/models--Systran--faster-whisper-base/snapshots/*/model.bin"

if [[ ! -x "$VENV_DIR/bin/python" || ! -f "$PYTHON_DIR/static/strudel/index.html" ]]; then
  echo "Source environment is incomplete. Run: bash scripts/setup_linux_source.sh" >&2
  exit 1
fi
if ! compgen -G "$MODEL_GLOB" > /dev/null; then
  echo "The offline base model is missing. Run: bash scripts/setup_linux_source.sh" >&2
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
