#!/bin/zsh
set -euo pipefail

LABEL="ai.ifa.unified-runtime"
PLIST_NAME="$LABEL.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$PLIST_NAME"
REPO_DIR="/Users/neoclaw/repos/ifa-data-platform"
BOOT_SCRIPT="$REPO_DIR/scripts/unified_daemon_launchd_boot.sh"
STDOUT_LOG="$REPO_DIR/artifacts/service/unified_daemon.launchd.out.log"
STDERR_LOG="$REPO_DIR/artifacts/service/unified_daemon.launchd.err.log"

mkdir -p "$LAUNCH_AGENTS_DIR" "$REPO_DIR/artifacts/service"

write_plist() {
cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>$BOOT_SCRIPT</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$REPO_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$STDOUT_LOG</string>
  <key>StandardErrorPath</key>
  <string>$STDERR_LOG</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>HOME</key>
    <string>$HOME</string>
  </dict>
</dict>
</plist>
EOF
}

cmd_install() {
  write_plist
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
  launchctl enable "gui/$(id -u)/$LABEL" || true
  echo "installed plist=$PLIST_PATH"
}

cmd_start() {
  [[ -f "$PLIST_PATH" ]] || write_plist
  launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
  launchctl enable "gui/$(id -u)/$LABEL" || true
  launchctl kickstart -k "gui/$(id -u)/$LABEL"
  echo "started label=$LABEL"
}

cmd_stop() {
  launchctl bootout "gui/$(id -u)/$LABEL" || true
  echo "stopped label=$LABEL"
}

cmd_restart() {
  cmd_stop
  sleep 1
  cmd_start
}

cmd_status() {
  launchctl print "gui/$(id -u)/$LABEL" | sed -n '1,220p'
}

case "${1:-}" in
  install) cmd_install ;;
  start) cmd_start ;;
  stop) cmd_stop ;;
  restart) cmd_restart ;;
  status) cmd_status ;;
  plist) write_plist; echo "$PLIST_PATH" ;;
  *) echo "usage: $0 {install|start|stop|restart|status|plist}"; exit 2 ;;
esac
