#!/bin/zsh
set -euo pipefail

REPO_DIR="/Users/neoclaw/repos/ifa-data-platform"
PY="$REPO_DIR/.venv/bin/python"
LOG_DIR="$REPO_DIR/artifacts/service"
mkdir -p "$LOG_DIR"

cd "$REPO_DIR"
"$PY" scripts/runtime_preflight.py --repair --out "$LOG_DIR/runtime_preflight_latest.json"
exec "$PY" -m ifa_data_platform.runtime.unified_daemon --loop --loop-interval-sec 60
