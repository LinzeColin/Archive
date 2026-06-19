#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

LABEL="local.codex-usage-monitor.dashboard"
PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
PROJECT_DIR="$(pwd)"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"
mkdir -p "${HOME}/Library/LaunchAgents" "${HOME}/Library/Logs/CodexUsageMonitor"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON_BIN}</string>
    <string>-m</string>
    <string>codex_usage_monitor.cli</string>
    <string>dashboard</string>
    <string>--port</string>
    <string>8766</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${PROJECT_DIR}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${HOME}/Library/Logs/CodexUsageMonitor/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>${HOME}/Library/Logs/CodexUsageMonitor/launchd.err.log</string>
</dict>
</plist>
PLIST

launchctl unload "$PLIST" >/dev/null 2>&1 || true
launchctl load "$PLIST"

echo "Installed LaunchAgent:"
echo "$PLIST"
echo "Dashboard will start at login: http://127.0.0.1:8766/"
