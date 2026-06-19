#!/usr/bin/env bash
set -euo pipefail

PORT="${CODEX_USAGE_PORT:-8766}"
LAN_PORT="${CODEX_USAGE_LAN_PORT:-8767}"
PID_FILE="${HOME}/Library/Logs/CodexUsageMonitor/dashboard.pid"
LAN_PID_FILE="$(cd "$(dirname "$0")" && pwd)/runtime/logs/dashboard-lan.pid"

stop_port() {
  local port="$1"
  local pid_file="$2"
  local pid
  local stopped=0

  if [ -f "$pid_file" ]; then
    pid="$(cat "$pid_file")"
    if ps -p "$pid" >/dev/null 2>&1; then
      kill "$pid"
      rm -f "$pid_file"
      echo "Stopped dashboard PID $pid on port $port"
      stopped=1
    fi
  fi

  pid="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$pid" ]; then
    kill "$pid"
    echo "Stopped dashboard on port $port"
    stopped=1
  fi

  if [ "$stopped" -eq 0 ]; then
    echo "Dashboard is not running on port $port"
  fi
}

if [ "${1:-}" = "--all" ]; then
  stop_port "$PORT" "$PID_FILE"
  stop_port "$LAN_PORT" "$LAN_PID_FILE"
  exit 0
fi

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE")"
  if ps -p "$PID" >/dev/null 2>&1; then
    kill "$PID"
    rm -f "$PID_FILE"
    echo "Stopped dashboard PID $PID"
    exit 0
  fi
fi

PID="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [ -n "$PID" ]; then
  kill "$PID"
  echo "Stopped dashboard on port $PORT"
else
  echo "Dashboard is not running on port $PORT"
fi
