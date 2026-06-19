#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PLUGIN="menubar/codex-usage.30s.sh"
TARGET_DIR="${HOME}/Library/Application Support/xbar/plugins"
TARGET="${TARGET_DIR}/codex-usage.30s.sh"

chmod +x codex-usage "$PLUGIN" quit-swiftbar.sh quit-background-monitor.sh quit-monitor-app.sh resume-background-monitor.sh install-app-entry.sh
mkdir -p "$TARGET_DIR"
rm -f "${TARGET_DIR}/codex-usage.5s.sh"
ln -sf "$(pwd)/$PLUGIN" "$TARGET"

echo "Installed xbar/SwiftBar plugin:"
echo "$TARGET"
echo
echo "Next:"
echo "1. Install or open xbar/SwiftBar."
echo "2. Set plugin folder to: $TARGET_DIR"
echo "3. Refresh plugins."
