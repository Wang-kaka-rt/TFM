#!/usr/bin/env bash
# First-run setup for the portable Linux release. Run once per computer.
set -euo pipefail

if ! command -v apt-get >/dev/null; then
  echo "This installer currently supports Ubuntu/Debian only." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y ffmpeg libportaudio2 libsndfile1
echo "System dependencies installed. Start the app with ./strudel-voice"
