#!/bin/zsh
set -euo pipefail

REPO_DIR="/Users/neoclaw/repos/ifa-data-platform"
PY="$REPO_DIR/.venv/bin/python"
LOG_DIR="$REPO_DIR/artifacts/service"
PID_FILE="$LOG_DIR/unified_daemon.pid"
HEARTBEAT_FILE="$LOG_DIR/unified_daemon.heartbeat.json"
mkdir -p "$LOG_DIR"

echo $$ > "$PID_FILE"

cd "$REPO_DIR"
"$PY" scripts/runtime_preflight.py --repair --out "$LOG_DIR/runtime_preflight_latest.json"
exec env UNIFIED_DAEMON_HEARTBEAT_FILE="$HEARTBEAT_FILE" "$PY" -m ifa_data_platform.runtime.unified_daemon --loop --loop-interval-sec 60
