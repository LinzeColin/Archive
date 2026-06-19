thread_id: 019ebb46-70f6-7543-ba48-3b6196b37b75
updated_at: 2026-06-12T11:02:36+00:00
rollout_path: /Users/linzezhang/.codex/archived_sessions/rollout-2026-06-12T20-00-16-019ebb46-70f6-7543-ba48-3b6196b37b75.jsonl
cwd: /Users/linzezhang/.codex/automations/codex-usage-token-alert

# Codex usage alert automation was production-hardened, then synchronized and verified against the final conversation state.

Rollout context: The automation lives in `/Users/linzezhang/.codex/automations/codex-usage-token-alert` and monitors Codex weekly token usage. The user repeatedly pushed from “test script” toward a real, stable notification workflow that reads accurately, wakes CodexBar when needed, and sends real email notifications. The final state was explicitly requested to be fully consistent with the conversation and to keep running normally.

## Task 1: Make the usage-alert automation production-stable and real-email capable
Outcome: success

Preference signals:
- The user said the automation “不是测试，是一个能真实使用的脚本任务…能达到检测和及时通知跌目的” -> future runs should treat this as a production workflow, not a demo.
- The user explicitly corrected the assistant several times about data accuracy (“你的读数依旧不准”) -> future runs should prioritize read correctness and freshness over simply making the email path succeed.
- The user requested “如果检测到codexbar时间戳不是现在时间就确认codexbar的运行状态，没运行就唤醒他，读书后再关闭他。设置gmail smtp” -> future runs should proactively wake CodexBar on stale reads, then close it if the automation started it, and should support Gmail SMTP as a first-class option.
- The user later changed direction to “使用macos mail” -> future runs should respect that macOS Mail is the preferred default delivery backend unless the user says otherwise.
- The user later asked to “更新AUTOmation，同步并确保正常运行” and then “确认automation和本次对话完全一致” -> future runs should finish with explicit consistency checks between conversation intent, local automation config, and runtime behavior.

Key steps:
- Read and used the local automation memory and `automation.toml` as the truth source for the current automation state.
- Inspected `check_token_usage_alert.py` and iteratively hardened it:
  - default usage source moved to `auto`
  - preferred source order prioritized `CodexBar/usage-history.jsonl`
  - rejected stale/expired reset times
  - added `USAGE_ALERT_FRESH_SAMPLE_MINUTES=10`
  - added CodexBar wake/refresh/close logic using `/Applications/CodexBar.app` and bundle id `com.steipete.codexbar`
  - added wait/timeout logic for fresh samples
  - added keychain-backed Gmail SMTP support with `security` lookup
  - fixed TLS validation by using `certifi` for SMTP SSL context
  - normalized SMTP password by stripping whitespace before login
  - finally set the default send backend to `macos-mail` after the user requested it
- Verified the automation by running the exact normal entrypoint (`python3 ... check_token_usage_alert.py --once`) and also forced-trigger runs for live send validation.
- Confirmed that the automation’s normal 4-hour schedule path still runs cleanly and that default threshold runs do not send mail unless trigger conditions are met.
- Updated `automation.toml` metadata and prompt so its wording matches the actual behavior: local execution, CodexBar refresh on stale samples, and notification through macOS Mail to a Gmail inbox.

Failures and how to do differently:
- Gmail SMTP live sending initially failed because the Keychain password was missing; later it failed due to TLS CA trust, then due to Gmail `535 BadCredentials`. Those failures were diagnostic and led to better hardening, but the final user-facing default was switched to macOS Mail to keep real notifications working.
- The rollout showed that a single cached weekly value can be misleading; future runs should treat sample freshness as a hard requirement and should fail closed when freshness cannot be established.
- The assistant initially had a mismatch between the config prompt (“Gmail”) and the actual backend choice (“macOS Mail”); future runs should do a final prompt/config consistency pass before declaring the automation synchronized.

Reusable knowledge:
- The exact runtime command remains:
  `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 /Users/linzezhang/.codex/automations/codex-usage-token-alert/check_token_usage_alert.py --once`
- The automation’s stable working directory is `/Users/linzezhang/.codex/automations/codex-usage-token-alert`.
- The current production defaults in the script are:
  - `USAGE_ALERT_PREFERRED_SOURCE=auto`
  - `USAGE_ALERT_FRESH_SAMPLE_MINUTES=10`
  - `USAGE_ALERT_CODEXBAR_APP_PATH=/Applications/CodexBar.app`
  - `USAGE_ALERT_CODEXBAR_REFRESH_TIMEOUT_SECONDS=120`
  - `USAGE_ALERT_SEND_BACKEND=macos-mail`
- The script uses CodexBar refresh behavior when a sample is not fresh: if CodexBar is not running, it is launched, the script waits for a fresh history/dashboard sample, and then CodexBar is closed if the script started it.
- Gmail SMTP is still implemented and can be re-enabled, but the automation default was intentionally changed away from it because live SMTP authentication was not reliable in this rollout.
- Keychain service for Gmail app password was standardized as `codex-usage-token-alert-gmail-smtp` with account `linzezhang35@gmail.com`.
- The automation records state/logs in `state/state.json` and `logs/runner.log`; these were used to verify `event=check`, `event=alert_sent`, and `trigger` values.

References:
- [1] `automation.toml` now shows:
  - `status = "ACTIVE"`
  - `rrule = "RRULE:FREQ=HOURLY;INTERVAL=4;BYMINUTE=0"`
  - `command = "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 /Users/linzezhang/.codex/automations/codex-usage-token-alert/check_token_usage_alert.py --once"`
  - `updated_at = 1781262108000`
  - prompt updated to mention CodexBar refresh and macOS Mail delivery to a Gmail inbox.
- [2] `check_token_usage_alert.py` now contains:
  - `USAGE_ALERT_SEND_BACKEND` defaulting to `macos-mail`
  - `USAGE_ALERT_PREFERRED_SOURCE=auto`
  - `USAGE_ALERT_FRESH_SAMPLE_MINUTES=10`
  - CodexBar launch/quit helpers and fresh-sample waiting logic
  - Gmail SMTP via `certifi` CA bundle
  - password whitespace normalization before SMTP login
- [3] Verification evidence from logs:
  - normal run wrote `event=check` with `remaining_percent=90.0`, `remaining_days=6`, `sampled_at=2026-06-12T10:49:48+00:00`, `trigger=false`
  - forced live send with macOS Mail wrote `event=alert_sent`, `mode=live`, `to=linzezhang35@gmail.com`
- [4] Keychain verification showed the credential entry exists with the expected service/account pair:
  - service `codex-usage-token-alert-gmail-smtp`
  - account `linzezhang35@gmail.com`

## Task 2: Final consistency check between conversation, automation config, and runtime behavior
Outcome: success

Preference signals:
- The user explicitly asked: “确认automation和本次对话完全一致” -> future runs should always do a final alignment pass when the user asks for synchronization.

Key steps:
- Compared `automation.toml`, `check_token_usage_alert.py`, `memory.md`, and the latest log entries.
- Found one remaining inconsistency: `automation.toml` prompt still said “发送 Gmail 通知” while the actual default backend was macOS Mail.
- Corrected the prompt to describe the actual behavior: CodexBar stale-sample refresh + macOS Mail delivery to Gmail inbox.
- Updated `updated_at` again to reflect the final synchronized state.
- Re-ran `py_compile` and confirmed the file still parsed.

Failures and how to do differently:
- The main risk in this workflow is configuration drift between the human-facing automation description and the executable defaults. Future runs should treat prompt text as part of the contract, not just comments.

Reusable knowledge:
- Final consistency checks should include three surfaces: executable script defaults, `automation.toml` metadata/prompt, and the latest persistent memory/log evidence.
- If those surfaces disagree, the prompt text should be corrected to match actual behavior before claiming success.

References:
- Final `automation.toml` prompt now states: local CodexBar weekly usage read, wake CodexBar if sample is stale, close it after refresh if the script started it, and send alert via macOS Mail to a Gmail inbox.
- Final check confirmed `py_compile` passed after the prompt/config sync.
