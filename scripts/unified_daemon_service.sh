#!/bin/zsh
set -euo pipefail

REPO_DIR="${REPO_DIR:-/Users/neoclaw/repos/ifa-data-platform}"
PY="${PY:-$REPO_DIR/.venv/bin/python}"
LOG_DIR="${LOG_DIR:-$REPO_DIR/artifacts/service}"
PID_FILE="${PID_FILE:-$LOG_DIR/unified_daemon.pid}"
PREFLIGHT_JSON="${PREFLIGHT_JSON:-$LOG_DIR/runtime_preflight_latest.json}"
OUT_LOG="${OUT_LOG:-$LOG_DIR/unified_daemon.out.log}"
ERR_LOG="${ERR_LOG:-$LOG_DIR/unified_daemon.err.log}"
DAEMON_MATCH_PATTERN="${DAEMON_MATCH_PATTERN:-ifa_data_platform.runtime.unified_daemon --loop}"
mkdir -p "$LOG_DIR"

cd "$REPO_DIR"

read_pid() {
  local pid
  pid=$(tr -d '[:space:]' < "$PID_FILE" 2>/dev/null || true)
  if [[ ! "$pid" =~ '^[0-9]+$' ]]; then
    echo ""
    return 1
  fi
  echo "$pid"
}

pid_command() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'
}

pid_is_expected_daemon() {
  local pid="$1"
  if ! kill -0 "$pid" 2>/dev/null; then
    return 1
  fi
  local command
  command=$(pid_command "$pid")
  [[ -n "$command" ]] || return 1
  [[ "$command" == *"$DAEMON_MATCH_PATTERN"* ]]
}

report_stale_pid() {
  local pid="$1"
  local reason="$2"
  local command="${3:-}"
  if [[ -n "$command" ]]; then
    echo "stale_pid_file pid=$pid reason=$reason command=$command"
  else
    echo "stale_pid_file pid=$pid reason=$reason"
  fi
}

cmd_status() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(read_pid) || {
      echo "stale_pid_file reason=invalid_pid_contents"
      exit 1
    }
    if pid_is_expected_daemon "$pid"; then
      echo "alive pid=$pid"
      ps -p "$pid" -o pid=,ppid=,pgid=,etime=,state=,command=
      exit 0
    fi
    local command
    command=$(pid_command "$pid")
    if [[ -n "$command" ]]; then
      report_stale_pid "$pid" "command_mismatch" "$command"
    else
      report_stale_pid "$pid" "not_running"
    fi
    exit 1
  fi
  echo "not_running"
  exit 1
}

cmd_stop() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(read_pid) || {
      rm -f "$PID_FILE"
      echo "cleared_stale_pid_file reason=invalid_pid_contents"
      return
    }
    if pid_is_expected_daemon "$pid"; then
      kill "$pid"
      sleep 1
      echo "stopped pid=$pid"
    else
      local command
      command=$(pid_command "$pid")
      if [[ -n "$command" ]]; then
        echo "cleared_stale_pid_file pid=$pid reason=command_mismatch command=$command"
      else
        echo "cleared_stale_pid_file pid=$pid reason=not_running"
      fi
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
    pid=$(read_pid) || {
      rm -f "$PID_FILE"
      pid=""
    }
    if [[ -n "$pid" ]]; then
      if pid_is_expected_daemon "$pid"; then
        echo "already_running pid=$pid"
        exit 0
      fi
      rm -f "$PID_FILE"
    fi
  fi

  "$PY" scripts/runtime_preflight.py --repair --out "$PREFLIGHT_JSON"
  nohup "$PY" -m ifa_data_platform.runtime.unified_daemon --loop --loop-interval-sec 60 >>"$OUT_LOG" 2>>"$ERR_LOG" < /dev/null &
  local pid=$!
  echo "$pid" > "$PID_FILE"
  disown "$pid" 2>/dev/null || true
  sleep 2
  if pid_is_expected_daemon "$pid"; then
    echo "started pid=$pid"
    exit 0
  fi
  local command
  command=$(pid_command "$pid")
  if [[ -n "$command" ]]; then
    echo "failed_to_start pid=$pid reason=command_mismatch command=$command"
  else
    echo "failed_to_start pid=$pid reason=not_running"
  fi
  rm -f "$PID_FILE"
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
