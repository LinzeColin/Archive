---
name: codex-usage-token-alert-local-check
description: Validate the local codex-usage-token-alert automation when the user asks to run it by command, verify CodexBar freshness and macOS Mail alert behavior, or debug silent local runs without model calls.
argument-hint: "[normal|dry-run]"
disable-model-invocation: true
user-invocable: false
allowed-tools:
  - Read
  - Grep
  - Bash
---

# codex-usage-token-alert-local-check

## When to use

- Use for `/Users/linzezhang/.codex/automations/codex-usage-token-alert` when the user says to run the alert locally, verify whether the real alert path would send, or inspect why no email was sent.
- Use when the user explicitly wants script-only execution with no extra LLM token usage.
- Do not use for redesigning the alert policy or for unrelated Codex analytics questions.

## Inputs / context to gather

1. Read the local automation files first:
   - `/Users/linzezhang/.codex/automations/codex-usage-token-alert/automation.toml`
   - `/Users/linzezhang/.codex/automations/codex-usage-token-alert/check_token_usage_alert.py`
   - `/Users/linzezhang/.codex/automations/codex-usage-token-alert/memory.md`
2. Confirm the intended mode:
   - normal local check: `--once`
   - branch validation without real email: `USAGE_ALERT_DRY_RUN=1`
3. Check the freshness contract before assuming the sample is usable:
   - stale CodexBar samples should trigger the built-in wake/read/close path
   - current production default sender is `macos-mail`, not Gmail SMTP
4. Plan to verify through logs/state, not stdout:
   - `logs/runner.log`
   - `state/state.json`

## Procedure

1. Confirm the documented entrypoint from `automation.toml`.
2. Read the current memory note for the latest cooldown/interval context.
3. Run the normal command first:
   - `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 /Users/linzezhang/.codex/automations/codex-usage-token-alert/check_token_usage_alert.py --once`
4. Inspect `logs/runner.log` and `state/state.json` immediately after the run.
5. Classify the result:
   - `event=check` with `trigger=false`: normal non-alert path succeeded
   - freshness failure / CodexBar refresh failure: no fresh sample was produced
   - `event=alert_sent`: the alert branch executed
   - `event=alert_failed`: the send path failed
6. If the goal is immediate validation and the sample/check path is blocked by timing protection, rerun with:
   - `USAGE_ALERT_INTERVAL_HOURS=0 ... check_token_usage_alert.py --once`
7. If the goal is to validate the alert branch without sending a real email, use:
   - `USAGE_ALERT_INTERVAL_HOURS=0 USAGE_ALERT_DRY_RUN=1 ... check_token_usage_alert.py --once`
   - optionally raise `USAGE_ALERT_MIN_RATIO_PERCENT` temporarily if current usage would not trigger
8. Record the outcome in `memory.md` with:
   - command used
   - whether interval/cooldown blocked the run
   - log evidence
   - whether the branch was normal, skipped, or dry-run validated

## Efficiency plan

1. Do not expect stdout; go straight to `logs/runner.log` and `state/state.json`.
2. Reuse the command already persisted in `automation.toml`; do not improvise alternate entrypoints.
3. Only use overrides that answer the current question:
   - `USAGE_ALERT_INTERVAL_HOURS=0` for immediate re-check
   - `USAGE_ALERT_DRY_RUN=1` for send-path validation
   - `USAGE_ALERT_MIN_RATIO_PERCENT=<higher>` only when you need to guarantee a trigger
4. Stop once you have decisive log evidence for fresh `event=check`, `event=alert_sent`, `event=alert_failed`, or a clear freshness/CodexBar failure.

## Pitfalls and fixes

- Symptom: the command exits 0 with no stdout.
  - Cause: the script is log-driven.
  - Fix: inspect `logs/runner.log` and `state/state.json` instead of treating silence as failure.
- Symptom: the script says the sample is stale or cannot get a fresh reading.
  - Cause: CodexBar was not refreshed successfully.
  - Fix: inspect the CodexBar wake/read/close path in `runner.log`; do not trust stale `sampled_at`.
- Symptom: the threshold should have triggered, but no new email was sent.
  - Cause: the send path failed or the threshold was not actually met on the fresh sample.
  - Fix: confirm `event=alert_sent` or `event=alert_failed` in the log; for controlled validation use `USAGE_ALERT_DRY_RUN=1`.
- Symptom: memory append text is mangled.
  - Cause: shell backticks or unsafe quoting during writeback.
  - Fix: write plain text without command substitution syntax.
- Symptom: the send backend seems wrong.
  - Cause: stale config/prompt text or wrong backend selection.
  - Fix: verify `automation.toml` and the script agree on `USAGE_ALERT_SEND_BACKEND`; current production default is `macos-mail`.

## Verification checklist

- Confirm the run stayed local/script-only and did not invoke any model.
- Confirm the exact command used matches `automation.toml` or a documented override.
- Confirm `logs/runner.log` shows the decisive event (`event=check`, `event=alert_sent`, `event=alert_failed`, or a clear freshness failure).
- Confirm `state/state.json` reflects the latest check/alert timestamps.
- Confirm any dry-run branch produced `mode=dry-run` rather than a real send.
