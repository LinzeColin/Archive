#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP_SOURCE="$(pwd)/macos/Codex Token Monitor.app"
APP_NAME="Codex Token Monitor.app"

chmod +x "${APP_SOURCE}/Contents/MacOS/Codex Token Monitor"

install_link() {
  local dir="$1"
  mkdir -p "$dir"
  rm -rf "${dir}/Codex Usage Monitor.app"
  rm -rf "${dir}/${APP_NAME}"
  ln -s "$APP_SOURCE" "${dir}/${APP_NAME}"
  echo "Installed: ${dir}/${APP_NAME}"
}

install_link "${HOME}/Downloads"
install_link "${HOME}/Desktop"
install_link "${HOME}/Applications"

if [[ -w "/Applications" ]]; then
  install_link "/Applications"
else
  echo "Skipped /Applications: not writable without admin permission"
fi
