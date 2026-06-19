#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

DISABLED_FILE="${CODEX_USAGE_DISABLED_FILE:-$(pwd)/runtime/background-monitor.disabled}"

rm -f "$DISABLED_FILE"

./start-dashboard.sh
./start-dashboard-lan.sh

echo "Background monitor resumed."
