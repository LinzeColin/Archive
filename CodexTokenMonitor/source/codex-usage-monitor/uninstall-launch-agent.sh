#!/usr/bin/env bash
set -euo pipefail

LABEL="local.codex-usage-monitor.dashboard"
PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"

if [ -f "$PLIST" ]; then
  launchctl unload "$PLIST" >/dev/null 2>&1 || true
  rm -f "$PLIST"
  echo "Removed LaunchAgent: $PLIST"
else
  echo "LaunchAgent not installed."
fi
