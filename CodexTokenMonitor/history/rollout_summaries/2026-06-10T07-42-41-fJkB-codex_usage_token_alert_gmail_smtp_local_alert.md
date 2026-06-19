thread_id: 019eb07b-c54e-7e62-b9b1-ab14611acc19
updated_at: 2026-06-10T07:44:24+00:00
rollout_path: /Users/linzezhang/.codex/archived_sessions/rollout-2026-06-10T17-42-41-019eb07b-c54e-7e62-b9b1-ab14611acc19.jsonl
cwd: /Users/linzezhang/.codex/automations/codex-usage-token-alert

# 本地脚本化的 Codex 周窗口额度告警自动化，已改为默认走 Gmail SMTP 发送并补充 automation 说明

Rollout context: 用户要在 `/Users/linzezhang/.codex/automations/codex-usage-token-alert` 里按命令本地执行，定时读取 Codex 周窗口额度；当剩余额度触发告警条件时发送 Gmail 通知，并明确要求“仅执行脚本，不调用模型，不产生额外LLM token”。

## Task 1: 读取现有自动化并确认实现方向

Outcome: success

Preference signals:
- 用户明确要求“按命令本地执行”“仅执行脚本，不调用模型，不产生额外LLM token” -> 未来类似自动化应默认走本地脚本/本地状态/本地发送路径，避免引入模型调用。
- 用户要求“定时读取 Codex 周窗口额度；当周窗口剩余额度触发告警条件时发送 Gmail 通知” -> 未来类似任务应优先把“读取额度、阈值判断、通知”拆成纯脚本链路，并把 Gmail 作为目标通道。

Key steps:
- 读取了 `automation.toml` 和 `check_token_usage_alert.py`，确认脚本已经具备：本地执行、周窗口读取、阈值判断、冷却、状态/日志记录。
- 发现原脚本默认发送后端是 macOS Mail (`osascript`) 而不是 Gmail SMTP。

Failures and how to do differently:
- 先前存在一个 `memory.md` 路径不存在的问题；后来改用绝对路径写入成功。未来如果要写 `$CODEX_HOME/...` 下文件，先确认环境变量在当前 shell 里是否生效，或直接使用绝对路径。

Reusable knowledge:
- 该 automation 的主目录是 `/Users/linzezhang/.codex/automations/codex-usage-token-alert`。
- `automation.toml` 中的 `command` 已固定为 `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 /Users/linzezhang/.codex/automations/codex-usage-token-alert/check_token_usage_alert.py --once`。
- 原脚本已经支持从 `openai-dashboard.json`、SQLite `token_events`、以及 `usage-history.jsonl` 三类来源读取周窗口剩余额度。

References:
- `automation.toml` 中原有字段：`execution_environment = "local"`、`rrule = "RRULE:FREQ=HOURLY;INTERVAL=4;BYMINUTE=0"`。
- 原脚本函数名：`get_weekly_usage`, `_should_send_alert`, `_send_via_macos_mail`。

## Task 2: 将告警发送切换为 Gmail SMTP 并补充自动化说明

Outcome: success

Preference signals:
- 用户说“发送 Gmail 通知” -> 未来类似需求默认应把 Gmail SMTP 作为主通道，而不是只保留系统 Mail.app 兜底。
- 用户强调“仅执行脚本，不调用模型” -> 未来类似自动化不应把通知逻辑设计成依赖 LLM 的工作流。

Key steps:
- 给 `check_token_usage_alert.py` 增加了 Gmail SMTP 发送实现：
  - 新增 `USAGE_ALERT_SEND_BACKEND=gmail` 默认值。
  - 新增 `USAGE_ALERT_SMTP_HOST`、`USAGE_ALERT_SMTP_PORT`、`USAGE_ALERT_SMTP_USER`、`USAGE_ALERT_SMTP_PASSWORD`、`USAGE_ALERT_SMTP_FROM`。
  - 使用 `smtplib.SMTP_SSL` + `EmailMessage` 发送邮件。
- 保留了 `macos-mail` 作为可选后端回退。
- 更新了 `automation.toml` 的 `notes`，补充 SMTP / 后端环境变量说明和示例。
- 创建并写入了 `memory.md`，记录本次 automation 改造摘要。

Failures and how to do differently:
- 首次补 `automation.toml` 时，`apply_patch` 目标位置不匹配，说明文件末尾模板内容与预期不完全一致；之后改成针对实际存在的行做 patch，成功。
- 首次写 `memory.md` 失败是因为使用了未展开的 `$CODEX_HOME`，后改为绝对路径写入成功。

Reusable knowledge:
- Gmail SMTP 发送实现已嵌入脚本，且不会额外调用模型。
- `--dry-run` 仍可用于联调邮件正文，不实际发信。
- 发送分支现在会根据 `USAGE_ALERT_SEND_BACKEND` 选择 `gmail` 或 `macos-mail`。

References:
- 文件变更：
  - `/Users/linzezhang/.codex/automations/codex-usage-token-alert/check_token_usage_alert.py`
  - `/Users/linzezhang/.codex/automations/codex-usage-token-alert/automation.toml`
  - `/Users/linzezhang/.codex/automations/codex-usage-token-alert/memory.md`
- 新增函数：`_send_via_gmail_smtp(...)`
- 现有执行入口：`/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 /Users/linzezhang/.codex/automations/codex-usage-token-alert/check_token_usage_alert.py --once`
- 用户可直接设置的关键环境变量示例：`USAGE_ALERT_SMTP_USER`、`USAGE_ALERT_SMTP_PASSWORD`、`USAGE_ALERT_TO`、`USAGE_ALERT_SEND_BACKEND=gmail`
