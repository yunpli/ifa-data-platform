#!/bin/zsh
set -euo pipefail

REPO_DIR="${REPO_DIR:-/Users/neoclaw/repos/ifa-data-platform}"
PY="${PY:-$REPO_DIR/.venv/bin/python}"
LOG_DIR="${LOG_DIR:-$REPO_DIR/artifacts/service}"
PID_FILE="${PID_FILE:-$LOG_DIR/unified_daemon.pid}"
PREFLIGHT_JSON="${PREFLIGHT_JSON:-$LOG_DIR/runtime_preflight_latest.json}"
OUT_LOG="${OUT_LOG:-$LOG_DIR/unified_daemon.out.log}"
ERR_LOG="${ERR_LOG:-$LOG_DIR/unified_daemon.err.log}"
HEARTBEAT_FILE="${HEARTBEAT_FILE:-$LOG_DIR/unified_daemon.heartbeat.json}"
LOOP_INTERVAL_SEC="${LOOP_INTERVAL_SEC:-60}"
HEARTBEAT_STALE_SEC="${HEARTBEAT_STALE_SEC:-$((LOOP_INTERVAL_SEC * 4))}"
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

find_matching_daemon_pids() {
  ps -axo pid=,command= | awk -v pat="$DAEMON_MATCH_PATTERN" 'index($0, pat) > 0 {print $1}'
}

first_matching_daemon_pid() {
  local matched_process
  while IFS= read -r matched_process; do
    [[ "$matched_process" =~ ^[0-9]+$ ]] || continue
    echo "$matched_process"
    return 0
  done < <(find_matching_daemon_pids)
  return 1
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

heartbeat_status() {
  local pid="$1"
  HEARTBEAT_FILE="$HEARTBEAT_FILE" HEARTBEAT_STALE_SEC="$HEARTBEAT_STALE_SEC" EXPECTED_PID="$pid" "$PY" - <<'PY'
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(os.environ['HEARTBEAT_FILE'])
expected_pid = int(os.environ['EXPECTED_PID'])
stale_sec = int(os.environ['HEARTBEAT_STALE_SEC'])
if not path.exists():
    print(f"heartbeat_status=missing path={path}")
    raise SystemExit(1)
try:
    payload = json.loads(path.read_text())
except Exception as exc:
    print(f"heartbeat_status=invalid path={path} error={exc}")
    raise SystemExit(1)
if int(payload.get('pid') or -1) != expected_pid:
    print(f"heartbeat_status=pid_mismatch path={path} heartbeat_pid={payload.get('pid')} expected_pid={expected_pid}")
    raise SystemExit(1)
ts = payload.get('generated_at')
if not ts:
    print(f"heartbeat_status=missing_timestamp path={path}")
    raise SystemExit(1)
now = datetime.now(timezone.utc)
seen = datetime.fromisoformat(ts)
if seen.tzinfo is None:
    seen = seen.replace(tzinfo=timezone.utc)
age = int((now - seen.astimezone(timezone.utc)).total_seconds())
phase = payload.get('phase') or 'unknown'
print(f"heartbeat_status={'ok' if age <= stale_sec else 'stale'} age_sec={age} phase={phase} path={path}")
raise SystemExit(0 if age <= stale_sec else 1)
PY
}

cmd_status() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(read_pid) || {
      local discovered_pid
      discovered_pid=$(first_matching_daemon_pid || true)
      if [[ -n "$discovered_pid" ]]; then
        echo "$discovered_pid" > "$PID_FILE"
        echo "alive pid=$discovered_pid source=process_scan refreshed_pid_file=1"
        ps -p "$discovered_pid" -o pid=,ppid=,pgid=,etime=,state=,command=
        heartbeat_status "$discovered_pid"
        exit $?
      fi
      echo "stale_pid_file reason=invalid_pid_contents"
      exit 1
    }
    if pid_is_expected_daemon "$pid"; then
      echo "alive pid=$pid source=pid_file"
      ps -p "$pid" -o pid=,ppid=,pgid=,etime=,state=,command=
      heartbeat_status "$pid"
      exit $?
    fi
    local command
    command=$(pid_command "$pid")
    local discovered_pid
    discovered_pid=$(first_matching_daemon_pid || true)
    if [[ -n "$discovered_pid" ]]; then
      echo "$discovered_pid" > "$PID_FILE"
      if [[ -n "$command" ]]; then
        report_stale_pid "$pid" "command_mismatch" "$command"
      else
        report_stale_pid "$pid" "not_running"
      fi
      echo "alive pid=$discovered_pid source=process_scan refreshed_pid_file=1"
      ps -p "$discovered_pid" -o pid=,ppid=,pgid=,etime=,state=,command=
      heartbeat_status "$discovered_pid"
      exit $?
    fi
    if [[ -n "$command" ]]; then
      report_stale_pid "$pid" "command_mismatch" "$command"
    else
      report_stale_pid "$pid" "not_running"
    fi
    exit 1
  fi
  local discovered_pid
  discovered_pid=$(first_matching_daemon_pid || true)
  if [[ -n "$discovered_pid" ]]; then
    echo "$discovered_pid" > "$PID_FILE"
    echo "alive pid=$discovered_pid source=process_scan refreshed_pid_file=1"
    ps -p "$discovered_pid" -o pid=,ppid=,pgid=,etime=,state=,command=
    heartbeat_status "$discovered_pid"
    exit $?
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
        echo "already_running pid=$pid source=pid_file"
        exit 0
      fi
      rm -f "$PID_FILE"
    fi
  fi

  local discovered_pid
  discovered_pid=$(first_matching_daemon_pid || true)
  if [[ -n "$discovered_pid" ]]; then
    echo "$discovered_pid" > "$PID_FILE"
    echo "already_running pid=$discovered_pid source=process_scan refreshed_pid_file=1"
    exit 0
  fi

  "$PY" scripts/runtime_preflight.py --repair --out "$PREFLIGHT_JSON"
  nohup env UNIFIED_DAEMON_HEARTBEAT_FILE="$HEARTBEAT_FILE" "$PY" -m ifa_data_platform.runtime.unified_daemon --loop --loop-interval-sec "$LOOP_INTERVAL_SEC" >>"$OUT_LOG" 2>>"$ERR_LOG" < /dev/null &
  local pid=$!
  echo "$pid" > "$PID_FILE"
  disown "$pid" 2>/dev/null || true
  sleep 3
  if pid_is_expected_daemon "$pid" && heartbeat_status "$pid"; then
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
