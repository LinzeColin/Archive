#!/usr/bin/env python3
"""Monitor Codex secondary (weekly) token usage and send an email alert."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import ssl
import os
import sqlite3
import subprocess
import time
from pathlib import Path
from email.message import EmailMessage
import smtplib
from typing import Dict, Optional, Tuple

UsageReading = Tuple[float, dt.datetime, str, Optional[dt.datetime]]


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_bool(raw: str, default: bool = False) -> bool:
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def _load_config() -> Dict[str, object]:
    cfg = {
        "check_interval_hours": int(os.getenv("USAGE_ALERT_INTERVAL_HOURS", "4")),
        "alert_ratio_percent": float(os.getenv("USAGE_ALERT_MIN_RATIO_PERCENT", "10")),
        "cooldown_hours": int(os.getenv("USAGE_ALERT_COOLDOWN_HOURS", "20")),
        "notify_to": os.getenv("USAGE_ALERT_TO", "linzezhang35@gmail.com"),
        "db_path": Path(os.getenv("USAGE_DB_PATH", os.path.expanduser("~/.codex_usage_monitor/usage.sqlite"))),
        "openai_dashboard_path": Path(
            os.getenv(
                "OPENAI_DASHBOARD_PATH",
                os.path.expanduser("~/Library/Application Support/com.steipete.codexbar/openai-dashboard.json"),
            )
        ),
        "history_jsonl_path": Path(
            os.getenv(
                "USAGE_HISTORY_PATH",
                os.path.expanduser("~/Library/Application Support/CodexBar/usage-history.jsonl"),
            )
        ),
        "state_path": Path(
            os.getenv(
                "USAGE_STATE_PATH",
                os.path.expanduser("~/.codex/automations/codex-usage-token-alert/state/state.json"),
            )
        ),
        "log_path": Path(
            os.getenv(
                "USAGE_LOG_PATH",
                os.path.expanduser("~/.codex/automations/codex-usage-token-alert/logs/runner.log"),
            )
        ),
        "smtp_host": os.getenv("USAGE_ALERT_SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("USAGE_ALERT_SMTP_PORT", "465")),
        "smtp_user": os.getenv("USAGE_ALERT_SMTP_USER", os.getenv("USAGE_ALERT_TO", "linzezhang35@gmail.com")),
        "smtp_password": os.getenv("USAGE_ALERT_SMTP_PASSWORD", ""),
        "smtp_from": os.getenv("USAGE_ALERT_SMTP_FROM", ""),
        "smtp_keychain_service": os.getenv("USAGE_ALERT_SMTP_KEYCHAIN_SERVICE", "codex-usage-token-alert-gmail-smtp"),
        "send_backend": os.getenv("USAGE_ALERT_SEND_BACKEND", "macos-mail").strip().lower(),
        "send_enabled": _parse_bool(os.getenv("USAGE_ALERT_SEND_ENABLED", "1"), True),
        "dry_run": _parse_bool(os.getenv("USAGE_ALERT_DRY_RUN", "0"), False),
        "tz_env": os.getenv("TZ", "Australia/Sydney"),
        "alert_subject_prefix": os.getenv("USAGE_ALERT_SUBJECT_PREFIX", "Codex 周窗口额度告警"),
        "week_window_minutes": int(os.getenv("USAGE_ALERT_WEEK_WINDOW_MINUTES", "10080")),
        "preferred_source": os.getenv("USAGE_ALERT_PREFERRED_SOURCE", "auto").strip().lower(),
        "max_sample_age_hours": int(os.getenv("USAGE_ALERT_MAX_SAMPLE_AGE_HOURS", "48")),
        "fresh_sample_minutes": int(os.getenv("USAGE_ALERT_FRESH_SAMPLE_MINUTES", "10")),
        "codexbar_bundle_id": os.getenv("USAGE_ALERT_CODEXBAR_BUNDLE_ID", "com.steipete.codexbar"),
        "codexbar_app_path": os.getenv("USAGE_ALERT_CODEXBAR_APP_PATH", "/Applications/CodexBar.app"),
        "codexbar_refresh_timeout_seconds": int(os.getenv("USAGE_ALERT_CODEXBAR_REFRESH_TIMEOUT_SECONDS", "120")),
    }

    threshold_ratio = float(cfg["alert_ratio_percent"])
    if 0 < threshold_ratio <= 1:
        threshold_ratio *= 100
    cfg["alert_ratio_percent"] = max(0.0, threshold_ratio)
    return cfg


def _read_keychain_password(service: str, account: str) -> str:
    if not service or not account:
        return ""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-w", "-s", service, "-a", account],
            text=True,
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        return ""
    return ""


def _read_state(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(path: Path, state: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_log(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
    record = dict(payload, recorded_at=ts)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _to_utc_datetime(value, value_type: str) -> Optional[dt.datetime]:
    if value in (None, "", 0):
        return None
    try:
        if value_type == "unix_sec":
            return dt.datetime.fromtimestamp(int(value), tz=dt.timezone.utc)
        if isinstance(value, (int, float)):
            return dt.datetime.fromtimestamp(int(value), tz=dt.timezone.utc)
        if isinstance(value, str):
            v = value.strip()
            if not v:
                return None
            return dt.datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except Exception:
        return None
    return None


def _load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _get_usage_from_sqlite(db_path: Path, window_minutes: int) -> Optional[UsageReading]:
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT secondary_used_percent, secondary_resets_at, timestamp
            FROM token_events
            WHERE secondary_window_minutes = ?
              AND secondary_used_percent IS NOT NULL
              AND secondary_resets_at IS NOT NULL
            ORDER BY datetime(timestamp) DESC
            LIMIT 1
            """,
            (window_minutes,),
        ).fetchone()
        if not row:
            return None
        used_percent, resets_at, timestamp = row
        used = float(used_percent)
        remaining = max(0.0, 100.0 - used)
        reset_dt = _to_utc_datetime(resets_at, "unix_sec")
        if reset_dt is None:
            return None
        return remaining, reset_dt, "sqlite:token_events", _to_utc_datetime(timestamp, "iso")
    except Exception:
        return None
    finally:
        conn.close()


def _load_from_openai_dashboard(path: Path, window_minutes: int) -> Optional[UsageReading]:
    raw = _load_json(path)
    if not raw:
        return None

    candidates = []
    secondary = raw
    if isinstance(raw.get("snapshot"), dict) and raw["snapshot"].get("secondaryLimit"):
        secondary = raw["snapshot"].get("secondaryLimit", {})
    elif isinstance(raw.get("secondaryLimit"), dict):
        secondary = raw.get("secondaryLimit", {})

    if not isinstance(secondary, dict):
        return None

    if secondary.get("windowMinutes") and int(secondary.get("windowMinutes")) != int(window_minutes):
        return None

    used = secondary.get("usedPercent")
    resets = secondary.get("resetsAt")
    if used is None or not resets:
        return None
    try:
        used_percent = float(used)
        resets_dt = _to_utc_datetime(resets, "iso")
        if resets_dt is None:
            return None
        sampled_at = _to_utc_datetime(raw.get("updatedAt") or raw.get("snapshot", {}).get("updatedAt"), "iso")
        return max(0.0, 100.0 - used_percent), resets_dt, "openai-dashboard.json", sampled_at
    except Exception:
        return None


def _load_from_history_jsonl(path: Path, window_minutes: int) -> Optional[UsageReading]:
    if not path.exists():
        return None

    lines = []
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
    except Exception:
        return None

    if not lines:
        return None

    for line in reversed(lines):
        try:
            payload = json.loads(line)
        except Exception:
            continue

        if payload.get("windowKind") != "secondary":
            continue
        if int(payload.get("windowMinutes", 0) or 0) != int(window_minutes):
            continue

        used = payload.get("usedPercent")
        resets = payload.get("resetsAt")
        if used is None or not resets:
            continue
        try:
            resets_dt = _to_utc_datetime(resets, "iso")
            if resets_dt is None:
                continue
            sampled_at = _to_utc_datetime(payload.get("sampledAt"), "iso")
            return max(0.0, 100.0 - float(used)), resets_dt, "CodexBar/usage-history.jsonl", sampled_at
        except Exception:
            continue
    return None


def _is_fresh_sample(sampled_at: Optional[dt.datetime], cfg: Dict[str, object]) -> bool:
    if sampled_at is None:
        return False
    max_age_minutes = int(cfg.get("fresh_sample_minutes", 0) or 0)
    if max_age_minutes <= 0:
        return True
    age_seconds = (_now_utc() - sampled_at).total_seconds()
    return 0 <= age_seconds <= max_age_minutes * 60


def _is_codexbar_running(bundle_id: str) -> bool:
    try:
        result = subprocess.run(
            ["pgrep", "-x", "CodexBar"],
            text=True,
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass

    script = f'tell application "System Events" to exists (application process id "{bundle_id}")'
    try:
        result = subprocess.run(["osascript", "-e", script], text=True, capture_output=True, timeout=10)
        return result.returncode == 0 and result.stdout.strip().lower() == "true"
    except Exception:
        return False


def _start_codexbar(cfg: Dict[str, object]) -> bool:
    app_path = str(cfg.get("codexbar_app_path", "") or "")
    try:
        if app_path:
            result = subprocess.run(["open", "-g", app_path], text=True, capture_output=True, timeout=10)
        else:
            result = subprocess.run(["open", "-g", "-b", str(cfg["codexbar_bundle_id"])], text=True, capture_output=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


def _stop_codexbar(cfg: Dict[str, object]) -> bool:
    script = f'tell application id "{cfg["codexbar_bundle_id"]}" to quit'
    try:
        result = subprocess.run(["osascript", "-e", script], text=True, capture_output=True, timeout=20)
        return result.returncode == 0
    except Exception:
        return False


def _wait_for_fresh_codexbar_reading(cfg: Dict[str, object], started_by_script: bool) -> Optional[UsageReading]:
    deadline = time.time() + int(cfg.get("codexbar_refresh_timeout_seconds", 120) or 120)
    best = None
    while time.time() < deadline:
        best = _load_from_history_jsonl(Path(cfg["history_jsonl_path"]), int(cfg["week_window_minutes"]))
        if best and best[1] > _now_utc() and _is_fresh_sample(best[3], cfg):
            return best
        dashboard = _load_from_openai_dashboard(Path(cfg["openai_dashboard_path"]), int(cfg["week_window_minutes"]))
        if dashboard and dashboard[1] > _now_utc() and _is_fresh_sample(dashboard[3], cfg):
            return dashboard
        time.sleep(5)

    if started_by_script:
        _stop_codexbar(cfg)
    return best


def _refresh_codexbar_if_needed(cfg: Dict[str, object], initial: Optional[UsageReading]) -> Optional[UsageReading]:
    if initial and initial[1] > _now_utc() and _is_fresh_sample(initial[3], cfg):
        return initial

    running_before = _is_codexbar_running(str(cfg["codexbar_bundle_id"]))
    started_by_script = False
    if not running_before:
        started_by_script = _start_codexbar(cfg)

    refreshed = _wait_for_fresh_codexbar_reading(cfg, started_by_script)
    if started_by_script:
        _stop_codexbar(cfg)
    return refreshed


def get_weekly_usage(cfg: Dict[str, object]) -> UsageReading:
    window_minutes = int(cfg["week_window_minutes"])
    db_path = cfg["db_path"]
    dashboard_path = cfg["openai_dashboard_path"]
    history_path = cfg["history_jsonl_path"]
    preferred = str(cfg.get("preferred_source", "auto")).strip().lower()

    source_map = {
        "sqlite": _get_usage_from_sqlite,
        "dashboard": _load_from_openai_dashboard,
        "history": _load_from_history_jsonl,
        "openai-dashboard": _load_from_openai_dashboard,
        "usage-history": _load_from_history_jsonl,
    }

    if preferred == "dashboard":
        loaders = (_load_from_openai_dashboard,)
    elif preferred == "sqlite":
        loaders = (_get_usage_from_sqlite,)
    elif preferred == "history":
        loaders = (_load_from_history_jsonl,)
    elif preferred == "auto":
        loaders = (
            _load_from_history_jsonl,
            _load_from_openai_dashboard,
            _get_usage_from_sqlite,
        )
    elif preferred in source_map:
        primary = source_map[preferred]
        loaders = (primary, _load_from_openai_dashboard, _get_usage_from_sqlite, _load_from_history_jsonl)
    else:
        loaders = (
            _load_from_openai_dashboard,
            _get_usage_from_sqlite,
            _load_from_history_jsonl,
        )

    # deduplicate loaders while keeping order
    seen = set()
    deduped = []
    for loader in loaders:
        if loader not in seen:
            seen.add(loader)
            deduped.append(loader)
    loaders = tuple(deduped)

    stale_codexbar_reading = None
    for loader in loaders:
        result = loader(db_path if loader is _get_usage_from_sqlite else (dashboard_path if loader is _load_from_openai_dashboard else history_path), window_minutes)
        if not result:
            continue
        remaining, resets_at, source, sampled_at = result
        if source.startswith("CodexBar/") or source == "openai-dashboard.json":
            refreshed = _refresh_codexbar_if_needed(cfg, result)
            if refreshed:
                result = refreshed
                remaining, resets_at, source, sampled_at = result
            stale_codexbar_reading = result
        if resets_at <= _now_utc():
            continue
        max_age_hours = int(cfg.get("max_sample_age_hours", 0) or 0)
        if sampled_at and max_age_hours > 0 and (_now_utc() - sampled_at).total_seconds() > max_age_hours * 3600:
            continue
        if sampled_at is None and max_age_hours > 0:
            continue
        if result:
            return result

    if stale_codexbar_reading:
        sampled = stale_codexbar_reading[3].isoformat() if stale_codexbar_reading[3] else "unknown"
        raise RuntimeError(f"CodexBar did not provide a fresh weekly usage sample; latest sampled_at={sampled}")
    raise RuntimeError("No usable usage source found. Check sqlite/dashboard/history files.")


def _remaining_days_left(reset_time: dt.datetime) -> int:
    now = _now_utc()
    seconds = (reset_time - now).total_seconds()
    if seconds <= 0:
        return 0
    # use ceiling to avoid false negatives near reset boundaries
    return max(1, math.ceil(seconds / 86400))


def _remaining_window_text(reset_time: dt.datetime) -> str:
    now = _now_utc()
    seconds = max(0, int((reset_time - now).total_seconds()))
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    return f"{days}天{hours}小时"


def _should_send_alert(remaining_percent: float, remaining_days: int, cfg: Dict[str, object]) -> bool:
    if remaining_days <= 0:
        return False
    ratio = remaining_percent / remaining_days
    return ratio < cfg["alert_ratio_percent"]


def _format_local_dt(value: dt.datetime, tz_name: str) -> str:
    try:
        # keep display readable in requested zone
        import zoneinfo

        tz = zoneinfo.ZoneInfo(tz_name)
        local_time = value.astimezone(tz)
        return f"{local_time.strftime('%Y-%m-%d %H:%M:%S')} {local_time.tzname()}"
    except Exception:
        return f"{value.astimezone(dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"


def _send_via_macos_mail(to_addr: str, subject: str, body: str, dry_run: bool) -> bool:
    if dry_run:
        return True
    applescript = """
on run argv
  set recipientAddress to item 1 of argv
  set subjectText to item 2 of argv
  set bodyText to item 3 of argv

  tell application "Mail"
    set m to make new outgoing message with properties {subject:subjectText, content:bodyText, visible:false}
    tell m
      make new to recipient at end of to recipients with properties {address:recipientAddress}
    end tell
    send m
  end tell
end run
"""
    result = subprocess.run(
        ["osascript", "-e", applescript, to_addr, subject, body],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Apple Mail send failed: {result.stderr.strip() or result.stdout.strip()}")
    return True


def _send_via_gmail_smtp(
    to_addr: str,
    subject: str,
    body: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from: str,
    dry_run: bool,
) -> bool:
    if dry_run:
        return True
    if not smtp_user or not smtp_password:
        raise RuntimeError("Gmail SMTP disabled: missing USAGE_ALERT_SMTP_USER or USAGE_ALERT_SMTP_PASSWORD")
    sender = smtp_from or smtp_user
    smtp_password = "".join(str(smtp_password).split())

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as smtp:
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg, from_addr=sender, to_addrs=[to_addr])
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Codex weekly token usage and alert by email when ratio is below threshold")
    parser.add_argument("--dry-run", action="store_true", help="Do not actually send email")
    parser.add_argument("--once", action="store_true", help="Force single check run and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = _load_config()
    if args.dry_run:
        cfg["dry_run"] = True
    if not cfg["smtp_password"]:
        cfg["smtp_password"] = _read_keychain_password(str(cfg["smtp_keychain_service"]), str(cfg["smtp_user"]))

    state = _read_state(cfg["state_path"])
    now = _now_utc()

    last_check_at_raw = state.get("last_check_at")
    if last_check_at_raw and cfg["check_interval_hours"] > 0 and not args.once:
        try:
            last_check_at = dt.datetime.fromisoformat(last_check_at_raw)
            if last_check_at.tzinfo is None:
                last_check_at = last_check_at.replace(tzinfo=dt.timezone.utc)
            if (now - last_check_at).total_seconds() < int(cfg["check_interval_hours"]) * 3600:
                _append_log(
                    cfg["log_path"],
                    {
                        "event": "check_skipped",
                        "reason": "interval_guard",
                        "last_check_at": last_check_at_raw,
                        "interval_hours": cfg["check_interval_hours"],
                    },
                )
                return 0
        except Exception:
            pass
    state["last_check_at"] = now.isoformat()
    _write_state(cfg["state_path"], state)

    try:
        remaining_percent, resets_at, source, sampled_at = get_weekly_usage(cfg)
    except Exception as exc:
        msg = f"usage read failed: {exc}"
        _append_log(cfg["log_path"], {"event": "usage_read_failed", "message": msg})
        print(msg)
        return 2

    remaining_days = _remaining_days_left(resets_at)
    should_send = _should_send_alert(remaining_percent, remaining_days, cfg)
    ratio_per_day = remaining_percent / remaining_days if remaining_days > 0 else None

    record = {
        "event": "check",
        "remaining_percent": remaining_percent,
        "remaining_days": remaining_days,
        "ratio_per_day_percent": ratio_per_day,
        "alert_ratio_percent": cfg["alert_ratio_percent"],
        "resets_at": resets_at.isoformat(),
        "source": source,
        "sampled_at": sampled_at.isoformat() if sampled_at else None,
        "send_enabled": cfg["send_enabled"],
        "dry_run": cfg["dry_run"],
        "trigger": bool(should_send),
    }
    _append_log(cfg["log_path"], record)

    if should_send and cfg["send_enabled"]:
        last_alert_at_raw = state.get("last_alert_at")
        cooldown_ok = True
        if last_alert_at_raw:
            try:
                last_alert_at = dt.datetime.fromisoformat(last_alert_at_raw)
                if last_alert_at.tzinfo is None:
                    last_alert_at = last_alert_at.replace(tzinfo=dt.timezone.utc)
                cooldown_seconds = (now - last_alert_at).total_seconds()
                cooldown_ok = cooldown_seconds >= int(cfg["cooldown_hours"]) * 3600
            except Exception:
                cooldown_ok = True

        if not cooldown_ok:
            _append_log(cfg["log_path"], {"event": "alert_skipped", "reason": "cooldown", "last_alert_at": last_alert_at_raw})
            return 0

        to_addr = cfg["notify_to"]
        subject = f"{cfg['alert_subject_prefix']}"

        window_start = resets_at - dt.timedelta(minutes=int(cfg["week_window_minutes"]))
        body = (
            "周窗口额度预警\n"
            "=====================\n"
            f"检测时间：{_format_local_dt(now, cfg['tz_env'])}\n"
            f"周窗口剩余时间：{_remaining_window_text(resets_at)}\n"
            f"周窗口额度剩余：{remaining_percent:.2f}%\n"
            f"读数来源：{source}\n"
            f"读数采样时间：{_format_local_dt(sampled_at, cfg['tz_env']) if sampled_at else 'unknown'}\n"
            f"周窗口起始时间：{_format_local_dt(window_start, cfg['tz_env'])}\n"
            f"周窗口更新时间：{_format_local_dt(resets_at, cfg['tz_env'])}\n"
            "=====================\n"
        )
        if cfg["dry_run"]:
            body = "[演练]\n" + body

        try:
            backend = str(cfg.get("send_backend", "gmail")).strip().lower()
            if backend == "gmail":
                _send_via_gmail_smtp(
                    to_addr=to_addr,
                    subject=subject,
                    body=body,
                    smtp_host=cfg["smtp_host"],
                    smtp_port=int(cfg["smtp_port"]),
                    smtp_user=cfg["smtp_user"],
                    smtp_password=cfg["smtp_password"],
                    smtp_from=cfg["smtp_from"],
                    dry_run=bool(cfg["dry_run"]),
                )
            elif backend == "macos-mail":
                _send_via_macos_mail(to_addr, subject, body, bool(cfg["dry_run"]))
            else:
                raise RuntimeError(f"Unknown send backend: {backend}")
            state["last_alert_at"] = now.isoformat()
            state["last_alert_days_left"] = remaining_days
            state["last_alert_ratio_per_day"] = ratio_per_day
            state["last_alert_source"] = source
            _write_state(cfg["state_path"], state)
            _append_log(cfg["log_path"], {"event": "alert_sent", "to": to_addr, "mode": "dry-run" if cfg["dry_run"] else "live"})
            print("alert sent" if not cfg["dry_run"] else "dry-run success")
        except Exception as exc:
            _append_log(cfg["log_path"], {"event": "alert_failed", "message": str(exc)})
            print(f"alert failed: {exc}")
            return 3
    else:
        if should_send and not cfg["send_enabled"]:
            _append_log(cfg["log_path"], {"event": "alert_skipped", "reason": "disabled"})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
