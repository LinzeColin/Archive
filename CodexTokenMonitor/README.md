# Codex Token Monitor Archive

This directory is the portable archive for the local macOS Codex Token Monitor system.

Archived on: 2026-06-19 Australia/Sydney
Target repository path: `LinzeColin/Archive/CodexTokenMonitor`

## What Is Included

- `source/codex-usage-monitor/`: runnable source, dashboard frontend, CLI, tests, app bundle source, icons, scripts, reports, and handoff.
- `automation/codex-usage-token-alert/`: local alert automation code, config, state, and memory, excluding runtime logs and bytecode.
- `skills/codex-usage-token-alert-local-check/`: local skill instructions for validating the alert automation.
- `config/`: LaunchAgent and menu-plugin inventory needed to reinstall local services.
- `data/usage.sqlite.gz`: consistent SQLite cache snapshot exported with `sqlite3 .backup`, plus schema, integrity check, and table counts.
- `vendor/CodexBar-macos-universal-0.32.4.zip`: archived CodexBar install package used by the alert workflow.
- `vendor/codexbar-support/`: CodexBar Application Support and preference files present at backup time.
- `history/rollout_summaries/`: selected Codex usage-token-alert rollout summaries.
- `CHECKSUMS.sha256` and `meta/file_inventory.relative.txt`: integrity and inventory files.

## What Is Intentionally Excluded

- Runtime LAN dashboard token: `runtime/dashboard-access-token`.
- Runtime logs and Python bytecode: `runtime/logs/`, `logs/`, `__pycache__/`, `*.pyc`.
- Keychain secrets, Gmail app passwords, API keys, OpenAI keys, GitHub credentials, and browser/session credentials.
- Raw Codex Desktop/CLI session JSONL logs under `~/.codex/sessions` and `~/.codex/archived_sessions`.
- Extracted CodexBar `.app`; the zip is included instead.

## Quick Restore

```bash
git clone https://github.com/LinzeColin/Archive.git
cd Archive/CodexTokenMonitor/source/codex-usage-monitor
chmod +x codex-usage *.sh menubar/codex-usage.30s.sh
python3 -m py_compile codex_usage_monitor/*.py
python3 -m unittest discover -s tests -v
./codex-usage now
```

For full restore details, read `RESTORE.md`.
