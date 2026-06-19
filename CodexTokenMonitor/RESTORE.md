# Restore And Development Handoff

## 1. Verify Archive Integrity

From `Archive/CodexTokenMonitor`:

```bash
shasum -a 256 -c CHECKSUMS.sha256
```

Expected: every listed file reports `OK`.

## 2. Restore The Source Tree

Recommended development location on a new machine:

```bash
mkdir -p "$HOME/Documents/Codex/restored"
rsync -a source/codex-usage-monitor/ "$HOME/Documents/Codex/restored/codex-usage-monitor/"
cd "$HOME/Documents/Codex/restored/codex-usage-monitor"
chmod +x codex-usage *.sh menubar/codex-usage.30s.sh
```

Run the minimum validation suite:

```bash
python3 -m py_compile codex_usage_monitor/*.py
python3 -m unittest discover -s tests -v
./codex-usage now
```

The CLI reads local Codex token-count logs. On a new machine without local Codex logs, the compile and unit tests are still the primary development validation path.

## 3. Restore The SQLite Cache Snapshot

The archived cache is optional for development, but useful for historical dashboard testing.

```bash
mkdir -p "$HOME/.codex_usage_monitor"
gunzip -c data/usage.sqlite.gz > "$HOME/.codex_usage_monitor/usage.sqlite"
cp data/project_aliases.json "$HOME/.codex_usage_monitor/project_aliases.json"
sqlite3 "$HOME/.codex_usage_monitor/usage.sqlite" "pragma integrity_check;"
```

Archived table counts at backup time:

```text
token_events|70867
monitor_samples|62331
file_state|462
```

## 4. Restore macOS App Entry Points

From the restored source directory:

```bash
./install-app-entry.sh
./install-menubar.sh
./install-launch-agent.sh
```

Start or stop services manually:

```bash
./start-dashboard.sh
./start-dashboard-lan.sh
./stop-dashboard.sh
```

The LAN dashboard token is intentionally not archived. A restored environment should generate its own `runtime/dashboard-access-token` or set `CODEX_USAGE_ACCESS_TOKEN`.

## 5. Restore Alert Automation

Copy the automation and skill into a Codex home only if this automation is still desired:

```bash
mkdir -p "$HOME/.codex/automations" "$HOME/.codex/memories/skills"
rsync -a automation/codex-usage-token-alert/ "$HOME/.codex/automations/codex-usage-token-alert/"
rsync -a skills/codex-usage-token-alert-local-check/ "$HOME/.codex/memories/skills/codex-usage-token-alert-local-check/"
```

Run a dry validation:

```bash
cd "$HOME/.codex/automations/codex-usage-token-alert"
USAGE_ALERT_INTERVAL_HOURS=0 USAGE_ALERT_DRY_RUN=1 python3 check_token_usage_alert.py --once
```

Gmail SMTP passwords are not archived. Use macOS Keychain or environment variables only on the target machine.

## 6. Continue Development

Primary source directory:

```text
source/codex-usage-monitor
```

Important files:

- `codex_usage_monitor/cli.py`
- `codex_usage_monitor/storage.py`
- `codex_usage_monitor/parser.py`
- `static/app.js`
- `static/styles.css`
- `tests/test_parser_metrics.py`
- `HANDOFF.md`

Minimum useful checks before a change:

```bash
python3 -m py_compile codex_usage_monitor/*.py
python3 -m unittest discover -s tests -v
node --check static/app.js
node --check static/widget.js
```
