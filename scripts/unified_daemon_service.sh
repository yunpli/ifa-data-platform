#!/bin/zsh
set -euo pipefail

REPO_DIR="/Users/neoclaw/repos/ifa-data-platform"
PY="$REPO_DIR/.venv/bin/python"
LOG_DIR="$REPO_DIR/artifacts/service"
PID_FILE="$LOG_DIR/unified_daemon.pid"
PREFLIGHT_JSON="$LOG_DIR/runtime_preflight_latest.json"
OUT_LOG="$LOG_DIR/unified_daemon.out.log"
ERR_LOG="$LOG_DIR/unified_daemon.err.log"
mkdir -p "$LOG_DIR"

cd "$REPO_DIR"

cmd_status() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      echo "alive pid=$pid"
      ps -p "$pid" -o pid=,ppid=,pgid=,etime=,state=,command=
      exit 0
    fi
    echo "stale_pid_file pid=$pid"
    exit 1
  fi
  echo "not_running"
  exit 1
}

cmd_stop() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
      sleep 1
      echo "stopped pid=$pid"
    fi
    rm -f "$PID_FILE"
  else
    echo "not_running"
  fi
}

cmd_preflight() {
  "$PY" scripts/runtime_preflight.py --repair --out "$PREFLIGHT_JSON"
  cat "$PREFLIGHT_JSON"
}

cmd_start() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      echo "already_running pid=$pid"
      exit 0
    else
      rm -f "$PID_FILE"
    fi
  fi

  "$PY" scripts/runtime_preflight.py --repair --out "$PREFLIGHT_JSON"
  nohup "$PY" -m ifa_data_platform.runtime.unified_daemon --loop --loop-interval-sec 60 >>"$OUT_LOG" 2>>"$ERR_LOG" < /dev/null &
  local pid=$!
  echo "$pid" > "$PID_FILE"
  disown "$pid" 2>/dev/null || true
  sleep 2
  if kill -0 "$pid" 2>/dev/null; then
    echo "started pid=$pid"
    exit 0
  fi
  echo "failed_to_start pid=$pid"
  exit 1
}

case "${1:-}" in
  start) cmd_start ;;
  stop) cmd_stop ;;
  status) cmd_status ;;
  preflight) cmd_preflight ;;
  *)
    echo "usage: $0 {start|stop|status|preflight}"
    exit 2
    ;;
esac
