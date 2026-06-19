# Backup Scope

## Original Local Assets

| Asset | Backup Location | Treatment |
| --- | --- | --- |
| `/Users/linzezhang/Documents/Codex/2026-06-02/new-chat/outputs/codex-usage-monitor` | `source/codex-usage-monitor` | Included, excluding runtime token/logs/bytecode |
| `/Users/linzezhang/.codex_usage_monitor/usage.sqlite` | `data/usage.sqlite.gz` | Included as consistent compressed SQLite backup |
| `/Users/linzezhang/.codex_usage_monitor/project_aliases.json` | `data/project_aliases.json` | Included |
| `/Users/linzezhang/.codex/automations/codex-usage-token-alert` | `automation/codex-usage-token-alert` | Included, excluding logs/bytecode |
| `/Users/linzezhang/.codex/memories/skills/codex-usage-token-alert-local-check` | `skills/codex-usage-token-alert-local-check` | Included |
| `/Users/linzezhang/Library/LaunchAgents/local.codex-usage-monitor.dashboard.plist` | `config/launch_agents/` | Included |
| xbar/SwiftBar plugin state | `config/menu_plugins/` | Inventory and symlink target included |
| app symlinks in `/Applications`, `~/Applications`, `~/Desktop`, `~/Downloads` | `meta/app_symlinks.txt` | Inventory included; app bundle source included under `source` |
| CodexBar installer zip | `vendor/CodexBar-macos-universal-0.32.4.zip` | Included |
| CodexBar Application Support and preferences | `vendor/codexbar-support/` | Included after secret scan |
| selected usage-token-alert rollout summaries | `history/rollout_summaries/` | Included |

## Deliberate Exclusions

The target repository is public. The backup therefore excludes secrets and high-risk local state:

- LAN dashboard token file.
- Keychain items and Gmail SMTP app passwords.
- GitHub/OpenAI/API credentials.
- Browser state, Mail state, Messages, Keychain, global app state.
- Raw Codex session logs. The monitor can rebuild from a new machine's local logs, and the archived SQLite snapshot is enough for development/testing.
- Python bytecode and runtime logs.

## Completeness Standard

This archive is complete for:

- Recreating the Codex Token Monitor source tree.
- Running tests and continuing development.
- Restoring dashboard/app/menu/LaunchAgent setup.
- Restoring a historical SQLite cache snapshot for dashboard development.
- Recreating the alert automation workflow without secrets.

It is not intended to clone private credentials or unrelated Codex workspace history into a public repository.
