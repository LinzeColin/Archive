#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP="macos/CodexUsageMenuBar.app"
BIN="$APP/Contents/MacOS/CodexUsageMenuBar"
PLIST="$APP/Contents/Info.plist"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

swiftc macos/CodexUsageMenuBar.swift -o "$BIN" -framework Cocoa

cat > "$PLIST" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>Codex Token Menu Bar</string>
  <key>CFBundleDisplayName</key>
  <string>Codex Token Monitor</string>
  <key>CFBundleIdentifier</key>
  <string>local.codex.token.menubar</string>
  <key>CFBundleVersion</key>
  <string>0.1.0</string>
  <key>CFBundleShortVersionString</key>
  <string>0.1.0</string>
  <key>CFBundleExecutable</key>
  <string>CodexUsageMenuBar</string>
  <key>LSUIElement</key>
  <true/>
</dict>
</plist>
PLIST

chmod +x "$BIN"
echo "Built: $(pwd)/$APP"
