# Security Exclusions

The following local files or credential stores were intentionally not backed up to GitHub:

- `source/codex-usage-monitor/runtime/dashboard-access-token`
- `source/codex-usage-monitor/runtime/logs/`
- `automation/codex-usage-token-alert/logs/`
- macOS Keychain entries, including Gmail SMTP app password entries.
- Any `OPENAI_API_KEY`, GitHub token, browser cookie store, or Mail account state.

Secret-pattern scan before commit checked for common OpenAI, GitHub, Google, Slack, and private-key patterns and found no matches.

CodexBar Application Support and preference files were also scanned for common token/password/secret patterns before being added to the archive.
