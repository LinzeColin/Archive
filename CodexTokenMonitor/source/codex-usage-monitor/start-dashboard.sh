#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PORT="${CODEX_USAGE_PORT:-8766}"
LOG_DIR="${HOME}/Library/Logs/CodexUsageMonitor"
PID_FILE="${LOG_DIR}/dashboard.pid"
mkdir -p "$LOG_DIR"

if lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Dashboard already listening on http://127.0.0.1:${PORT}/"
  exit 0
fi

PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"

nohup "$PYTHON_BIN" -m codex_usage_monitor.cli dashboard --port "$PORT" >"${LOG_DIR}/dashboard.log" 2>&1 &
echo $! > "$PID_FILE"
echo "Dashboard started: http://127.0.0.1:${PORT}/"
echo "PID: $(cat "$PID_FILE")"
