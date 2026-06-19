#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PORT="${CODEX_USAGE_PORT:-8766}"
LAN_PORT="${CODEX_USAGE_LAN_PORT:-8767}"
DISABLED_FILE="${CODEX_USAGE_DISABLED_FILE:-$(pwd)/runtime/background-monitor.disabled}"
LOG_DIR="${CODEX_USAGE_LOG_DIR:-$(pwd)/runtime/logs}"

mkdir -p "$(dirname "$DISABLED_FILE")" "$LOG_DIR"
{
  echo "disabled_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "reason=manual_menu_quit"
} > "$DISABLED_FILE"

./stop-dashboard.sh --all || true

close_port_hard() {
  local port="$1"
  local pids=""
  for _ in 1 2 3; do
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -z "$pids" ]]; then
      return 0
    fi
    kill $pids 2>/dev/null || true
    sleep 0.3
  done
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    kill -9 $pids 2>/dev/null || true
  fi
}

close_port_hard "$PORT"
close_port_hard "$LAN_PORT"

rm -f "${HOME}/Library/Logs/CodexUsageMonitor/dashboard.pid" "${LOG_DIR}/dashboard-lan.pid"

echo "Background monitor disabled."
echo "Mac dashboard stopped on port ${PORT}."
echo "Phone access stopped on port ${LAN_PORT}."
echo "Use 'Resume background monitor' from the menu to start it again."
