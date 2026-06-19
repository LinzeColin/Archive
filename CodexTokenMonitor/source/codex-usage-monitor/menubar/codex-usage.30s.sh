#!/usr/bin/env bash
# xbar/SwiftBar compatible plugin. Copy or symlink this file into your xbar plugin folder.

PROJECT_DIR="/Users/linzezhang/Documents/Codex/2026-06-02/new-chat/outputs/codex-usage-monitor"
LOCAL_PORT="${CODEX_USAGE_PORT:-8766}"
LAN_PORT="${CODEX_USAGE_LAN_PORT:-8767}"
DASHBOARD_URL="${CODEX_USAGE_DASHBOARD_URL:-http://127.0.0.1:${LOCAL_PORT}/}"
TOKEN_FILE="${PROJECT_DIR}/runtime/dashboard-access-token"
DISABLED_FILE="${CODEX_USAGE_DISABLED_FILE:-${PROJECT_DIR}/runtime/background-monitor.disabled}"
AUTO_START_DASHBOARD="${CODEX_USAGE_AUTO_START_DASHBOARD:-1}"
AUTO_START_PHONE_ACCESS="${CODEX_USAGE_AUTO_START_PHONE_ACCESS:-1}"

is_listening() {
  lsof -tiTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

mac_ip() {
  local ip
  ip="$(ipconfig getifaddr en0 2>/dev/null || true)"
  if [[ -z "$ip" ]]; then
    ip="$(ipconfig getifaddr en1 2>/dev/null || true)"
  fi
  if [[ -z "$ip" ]]; then
    ip="$(ifconfig en0 2>/dev/null | awk '/inet / {print $2; exit}')"
  fi
  printf "%s" "$ip"
}

phone_token_query() {
  local token="${CODEX_USAGE_ACCESS_TOKEN:-}"
  if [[ -z "$token" && -f "$TOKEN_FILE" ]]; then
    token="$(tr -d '\n\r' < "$TOKEN_FILE")"
  fi
  if [[ -n "$token" ]]; then
    printf "?token=%s" "$token"
  fi
}

if [[ -f "$DISABLED_FILE" ]]; then
  if is_listening "$LOCAL_PORT" || is_listening "$LAN_PORT"; then
    "$PROJECT_DIR/stop-dashboard.sh" --all >/dev/null 2>&1 || true
  fi
  echo "Codex off | color=#98A2B3"
  echo "---"
  echo "Background monitor: off"
  echo "Mac dashboard: stopped"
  echo "Phone access: stopped"
  echo "---"
  echo "Quit Completely | bash=${PROJECT_DIR}/quit-monitor-app.sh terminal=false refresh=false color=#FF3B30"
  echo "Quit SwiftBar | bash=${PROJECT_DIR}/quit-swiftbar.sh terminal=false refresh=false color=#FF3B30"
  echo "---"
  echo "Resume background monitor | bash=${PROJECT_DIR}/resume-background-monitor.sh terminal=false refresh=true color=#00A3FF"
  echo "Open dashboard after resume | disabled=true"
  exit 0
fi

if [[ "$AUTO_START_DASHBOARD" != "0" ]] && ! is_listening "$LOCAL_PORT"; then
  "$PROJECT_DIR/start-dashboard.sh" >/dev/null 2>&1 || true
fi

if [[ "$AUTO_START_PHONE_ACCESS" != "0" ]] && is_listening "$LOCAL_PORT" && ! is_listening "$LAN_PORT"; then
  "$PROJECT_DIR/start-dashboard-lan.sh" >/dev/null 2>&1 || true
fi

"$PROJECT_DIR/codex-usage" menu --dashboard-url "$DASHBOARD_URL" --menu-limit 200 --no-history-log 2>/dev/null || {
  echo "Codex --"
  echo "---"
  echo "No cached data"
}

IP_ADDRESS="$(mac_ip)"
LOCAL_RUNNING=0
LAN_RUNNING=0
if is_listening "$LOCAL_PORT"; then
  LOCAL_RUNNING=1
fi
if is_listening "$LAN_PORT"; then
  LAN_RUNNING=1
fi

echo "---"
echo "Quit Completely | bash=${PROJECT_DIR}/quit-monitor-app.sh terminal=false refresh=false color=#FF3B30"
echo "Quit SwiftBar | bash=${PROJECT_DIR}/quit-swiftbar.sh terminal=false refresh=false color=#FF3B30"
echo "---"
if [[ "$LOCAL_RUNNING" != "1" ]]; then
  echo "Start Mac dashboard | bash=${PROJECT_DIR}/start-dashboard.sh terminal=false refresh=true color=#FF3B30"
fi

if [[ "$LAN_RUNNING" == "1" ]]; then
  if [[ -n "$IP_ADDRESS" ]]; then
    TOKEN_QUERY="$(phone_token_query)"
    echo "Phone: http://${IP_ADDRESS}:${LAN_PORT}/${TOKEN_QUERY} | href=http://${IP_ADDRESS}:${LAN_PORT}/${TOKEN_QUERY} color=#00A3FF"
  else
    echo "Phone: check Mac Wi-Fi IP, then open http://<ip>:${LAN_PORT}/ | color=#7C5CFF"
  fi
else
  echo "Start phone access | bash=${PROJECT_DIR}/start-dashboard-lan.sh terminal=false refresh=true color=#7C5CFF"
fi

if [[ "$LOCAL_RUNNING" == "1" || "$LAN_RUNNING" == "1" ]]; then
  echo "Stop services | bash=${PROJECT_DIR}/stop-dashboard.sh param1=--all terminal=false refresh=true"
fi
