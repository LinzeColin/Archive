#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

./quit-background-monitor.sh || true

osascript >/dev/null 2>&1 <<'APPLESCRIPT' || true
tell application "System Events"
  if exists process "SwiftBar" then
    tell application "SwiftBar" to quit
  end if
  if exists process "xbar" then
    tell application "xbar" to quit
  end if
end tell
APPLESCRIPT

echo "Background monitor stopped. SwiftBar/xbar quit command sent."
