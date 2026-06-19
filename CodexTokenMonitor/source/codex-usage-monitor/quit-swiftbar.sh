#!/usr/bin/env bash
set -euo pipefail

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

echo "SwiftBar/xbar quit command sent."
