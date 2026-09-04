#!/usr/bin/env bash
# Bootstrap a reproducible Linux source checkout of Strudel Voice.
# Usage:
#   bash scripts/setup_linux_source.sh          # install/build missing parts
#   bash scripts/setup_linux_source.sh --check  # diagnostics only
set -euo pipefail

CHECK_ONLY=false
if [[ "${1:-}" == "--check" ]]; then
  CHECK_ONLY=true
elif [[ $# -gt 0 ]]; then
  echo "Usage: bash scripts/setup_linux_source.sh [--check]" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/strudel-src-real"
PYTHON_DIR="$ROOT_DIR/python"
STATIC_DIR="$PYTHON_DIR/static/strudel"
VENV_DIR="$PYTHON_DIR/.venv"
MODEL_DIR="$PYTHON_DIR/assets/models"
NODE_VERSION="20.20.2"
NODE_ARCH=""
case "$(uname -m)" in
  x86_64) NODE_ARCH="x64" ;;
  aarch64|arm64) NODE_ARCH="arm64" ;;
  *) echo "Unsupported CPU architecture: $(uname -m)" >&2; exit 1 ;;
esac
NODE_HOME="$HOME/.local/node/node-v${NODE_VERSION}-linux-${NODE_ARCH}"
NODE_BIN="$NODE_HOME/bin"
export PATH="$NODE_BIN:$HOME/.local/bin:$PATH"

say() { printf '\n==> %s\n' "$*"; }
has_base_model() {
  compgen -G "$MODEL_DIR/models--Systran--faster-whisper-base/snapshots/*/model.bin" > /dev/null
}
python_ok() {
  command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'
}
node_ok() {
  command -v node >/dev/null 2>&1 && node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)'
}

if [[ ! -d "$FRONTEND_DIR" || ! -f "$FRONTEND_DIR/package.json" ]]; then
  echo "Frontend checkout not found: $FRONTEND_DIR" >&2
  echo "Run this script from the repository's code directory." >&2
  exit 1
fi
if [[ ! -f "$PYTHON_DIR/requirements.linux-portable.txt" ]]; then
  echo "Python service not found: $PYTHON_DIR" >&2
  exit 1
fi

if [[ "$CHECK_ONLY" == true ]]; then
  say "Strudel Voice Linux source environment check"
  printf 'Platform: %s %s\n' "$(. /etc/os-release 2>/dev/null && echo "${PRETTY_NAME:-Linux}")" "$(uname -m)"
  command -v ffmpeg >/dev/null && echo "ffmpeg: OK" || echo "ffmpeg: MISSING"
  ldconfig -p 2>/dev/null | grep -F 'libportaudio.so' >/dev/null && echo "PortAudio: OK" || echo "PortAudio: MISSING"
  ldconfig -p 2>/dev/null | grep -F 'libsndfile.so' >/dev/null && echo "libsndfile: OK" || echo "libsndfile: MISSING"
  python_ok && echo "Python: $(python3 --version)" || echo "Python >= 3.10: MISSING"
  node_ok && echo "Node: $(node --version)" || echo "Node >= 20: MISSING"
  command -v pnpm >/dev/null && echo "pnpm: $(pnpm --version)" || echo "pnpm: MISSING"
  [[ -x "$VENV_DIR/bin/python" ]] && echo "Python venv: OK" || echo "Python venv: MISSING"
  [[ -f "$STATIC_DIR/index.html" ]] && echo "Strudel static assets: OK" || echo "Strudel static assets: MISSING"
  has_base_model && echo "faster-whisper base model: OK (offline)" || echo "faster-whisper base model: MISSING"
  exit 0
fi

if [[ ! -f /etc/debian_version ]]; then
  echo "This bootstrap script currently supports Ubuntu/Debian only." >&2
  exit 1
fi

say "Installing system dependencies"
missing_packages=()
command -v ffmpeg >/dev/null 2>&1 || missing_packages+=(ffmpeg)
command -v python3 >/dev/null 2>&1 || missing_packages+=(python3)
command -v rsync >/dev/null 2>&1 || missing_packages+=(rsync)
if ! command -v python3 >/dev/null 2>&1 || ! python3 -m venv --help >/dev/null 2>&1; then
  missing_packages+=(python3-venv)
fi
if ! ldconfig -p 2>/dev/null | grep -F 'libportaudio.so' >/dev/null; then
  missing_packages+=(libportaudio2)
fi
if ! ldconfig -p 2>/dev/null | grep -F 'libsndfile.so' >/dev/null; then
  missing_packages+=(libsndfile1)
fi
# curl and xz are only needed when this machine does not already have a usable
# Node.js runtime. Git is needed for `git clone` before this script is run, not
# for an already-cloned checkout.
if ! node_ok; then
  command -v curl >/dev/null 2>&1 || missing_packages+=(curl ca-certificates)
  command -v xz >/dev/null 2>&1 || missing_packages+=(xz-utils)
fi

if [[ ${#missing_packages[@]} -gt 0 ]]; then
  echo "Installing missing packages: ${missing_packages[*]}"
  sudo apt-get update
  sudo apt-get install -y ca-certificates "${missing_packages[@]}"
else
  echo "System dependencies are already installed."
fi

if ! python_ok; then
  echo "Python 3.10 or later is required; current python3 is too old." >&2
  exit 1
fi

if ! node_ok; then
  say "Installing Node.js ${NODE_VERSION} locally"
  mkdir -p "$HOME/.local/node"
  archive="/tmp/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz"
  curl --fail --location --retry 3 --output "$archive" \
    "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz"
  tar -xJf "$archive" -C "$HOME/.local/node"
fi
if ! node_ok; then
  echo "Node.js 20 installation failed." >&2
  exit 1
fi

say "Preparing pnpm and building the Strudel frontend"
corepack enable
corepack prepare pnpm@9.15.5 --activate
pnpm --dir "$FRONTEND_DIR" install --frozen-lockfile
pnpm --dir "$FRONTEND_DIR" build

say "Synchronising frontend static assets"
mkdir -p "$STATIC_DIR"
rsync -a --delete "$FRONTEND_DIR/website/dist/" "$STATIC_DIR/"

say "Creating the Python virtual environment"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
# Install the CPU wheels before the remaining dependencies, preventing PyPI from
# pulling an unnecessary CUDA runtime on ordinary Linux desktops.
python -m pip install --index-url https://download.pytorch.org/whl/cpu \
  "torch==2.5.1+cpu" "torchaudio==2.5.1+cpu"
python -m pip install -r "$PYTHON_DIR/requirements.linux-portable.txt"

if ! has_base_model; then
  say "Downloading the faster-whisper base model for offline use"
  mkdir -p "$MODEL_DIR"
  (
    cd "$PYTHON_DIR"
    python - <<'PY'
from faster_whisper import WhisperModel

WhisperModel("base", device="cpu", compute_type="int8", download_root="assets/models")
print("Downloaded faster-whisper base model.")
PY
  )
fi

say "Setup complete"
echo "Start the source version with:"
echo "  bash scripts/run_linux_source.sh"
