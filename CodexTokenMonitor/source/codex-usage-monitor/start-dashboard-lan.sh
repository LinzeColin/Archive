#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PORT="${CODEX_USAGE_LAN_PORT:-8767}"
HOST="${CODEX_USAGE_LAN_HOST:-0.0.0.0}"
LOG_DIR="${CODEX_USAGE_LOG_DIR:-$(pwd)/runtime/logs}"
PID_FILE="${LOG_DIR}/dashboard-lan.pid"
TOKEN_FILE="$(pwd)/runtime/dashboard-access-token"
mkdir -p "$LOG_DIR"

if lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Dashboard LAN server already listening on port ${PORT}."
else
  PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"
  nohup "$PYTHON_BIN" -m codex_usage_monitor.cli dashboard --host "$HOST" --port "$PORT" >"${LOG_DIR}/dashboard-lan.log" 2>&1 &
  echo $! > "$PID_FILE"
  STARTED=0
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
      STARTED=1
      break
    fi
    sleep 1
  done
  if [[ "$STARTED" != "1" ]]; then
    echo "Dashboard LAN server did not start on port ${PORT}."
    echo "Log: ${LOG_DIR}/dashboard-lan.log"
    exit 1
  fi
fi

MAC_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
if [[ -z "$MAC_IP" ]]; then
  MAC_IP="$(ipconfig getifaddr en1 2>/dev/null || true)"
fi
if [[ -z "$MAC_IP" ]]; then
  MAC_IP="$(ifconfig en0 2>/dev/null | awk '/inet / {print $2; exit}')"
fi
ACCESS_TOKEN="${CODEX_USAGE_ACCESS_TOKEN:-}"
if [[ -z "$ACCESS_TOKEN" && -f "$TOKEN_FILE" ]]; then
  ACCESS_TOKEN="$(tr -d '\n\r' < "$TOKEN_FILE")"
fi
TOKEN_QUERY=""
if [[ -n "$ACCESS_TOKEN" ]]; then
  TOKEN_QUERY="?token=${ACCESS_TOKEN}"
fi

echo "LAN dashboard started."
echo "Mac local: http://127.0.0.1:${PORT}/"
if [[ -n "$MAC_IP" ]]; then
  echo "Phone URL: http://${MAC_IP}:${PORT}/${TOKEN_QUERY}"
else
  echo "Phone URL: http://<your-mac-ip>:${PORT}/${TOKEN_QUERY}"
  echo "Find Mac IP: System Settings > Wi-Fi > Details > IP Address"
fi
echo "PID file: ${PID_FILE}"
