from __future__ import annotations

import argparse
import csv
import hmac
import json
import os
import secrets
import sys
import time
from datetime import datetime
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from ipaddress import ip_address
from pathlib import Path
from threading import Lock, RLock, Thread
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from .metrics import build_snapshot, format_percent, format_tokens
from .parser import DEFAULT_CODEX_ROOT, load_events
from .storage import (
    backfill_monitor_samples_from_events,
    connect,
    default_db_path,
    load_events_from_db,
    load_events_from_db_readonly,
    load_all_time_total_token_usage_from_db,
    load_monitor_history_from_db,
    load_monitor_history_from_db_readonly,
    load_recent_events_from_db,
    record_monitor_sample,
    sync_from_logs,
)


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
REPORTS_DIR = ROOT / "reports"
RUNTIME_DIR = ROOT / "runtime"
ACCESS_TOKEN_PATH = RUNTIME_DIR / "dashboard-access-token"
DASHBOARD_SYNC_LOCK = Lock()
DASHBOARD_BACKFILL_LOCK = Lock()
DASHBOARD_CACHE_LOCK = RLock()
DASHBOARD_CACHE: Dict[str, Any] = {
    "snapshot": None,
    "events": None,
    "cached_at": None,
    "data_read_at": None,
    "latest_event_at": None,
    "last_sync_started_at": None,
    "last_sync_finished_at": None,
    "sync_in_progress": False,
    "last_error": None,
    "average_burn_minutes": None,
}
DASHBOARD_SYNC_INTERVAL_SECONDS = 60.0
MONITOR_HISTORY_DAYS = 3650
MAX_DASHBOARD_HISTORY_DAYS = 3650
DASHBOARD_EVENT_LIMIT = 5000


def _dashboard_access_token(create: bool = False) -> str | None:
    token = str((os.environ.get("CODEX_USAGE_ACCESS_TOKEN") or "")).strip()
    if token:
        return token
    if ACCESS_TOKEN_PATH.exists():
        try:
            return ACCESS_TOKEN_PATH.read_text(encoding="utf-8").strip() or None
        except OSError:
            return None
    if not create:
        return None
    token = secrets.token_urlsafe(24)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    ACCESS_TOKEN_PATH.write_text(token + "\n", encoding="utf-8")
    try:
        ACCESS_TOKEN_PATH.chmod(0o600)
    except OSError:
        pass
    return token


def _is_local_client(address: str) -> bool:
    try:
        return ip_address(address).is_loopback
    except ValueError:
        return address in {"localhost"}


def _trim_dashboard_payload(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    snapshot["trend_points"] = list(snapshot.get("trend_points") or [])[-500:]
    snapshot["token_timeline_points"] = list(snapshot.get("token_timeline_points") or [])[-DASHBOARD_EVENT_LIMIT:]
    return snapshot


def _compact_dashboard_payload(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "generated_at": snapshot.get("generated_at"),
        "latest_event": snapshot.get("latest_event"),
        "alerts": snapshot.get("alerts") or [],
        "totals": snapshot.get("totals") or {},
        "burn_rate_windows": snapshot.get("burn_rate_windows") or [],
        "average_burn_rate_primary_percent_per_hour": snapshot.get("average_burn_rate_primary_percent_per_hour"),
        "average_burn_rate_interval_minutes": snapshot.get("average_burn_rate_interval_minutes"),
        "dashboard_cache": snapshot.get("dashboard_cache") or {},
    }


def _record_and_attach_monitor_history(
    snapshot: Dict[str, Any],
    db_path: Path | None,
    source: str,
    history_days: int = MONITOR_HISTORY_DAYS,
    include_history: bool = True,
    record_sample: bool = True,
) -> Dict[str, Any]:
    history_days = min(max(1, int(history_days or MONITOR_HISTORY_DAYS)), MAX_DASHBOARD_HISTORY_DAYS)
    if record_sample:
        try:
            with connect(db_path, timeout=2) as conn:
                record_monitor_sample(conn, snapshot, source=source, min_interval_seconds=60)
        except Exception as exc:
            with DASHBOARD_CACHE_LOCK:
                DASHBOARD_CACHE["last_error"] = f"{type(exc).__name__}: {exc}"
    if include_history:
        snapshot["monitor_history"] = load_monitor_history_from_db_readonly(db_path, days=history_days)
    else:
        snapshot.pop("monitor_history", None)
        snapshot = _compact_dashboard_payload(snapshot)

    def record_async() -> None:
        if not DASHBOARD_BACKFILL_LOCK.acquire(blocking=False):
            return
        try:
            with connect(db_path) as conn:
                backfill_monitor_samples_from_events(conn)
        except Exception:
            return
        finally:
            DASHBOARD_BACKFILL_LOCK.release()

    if include_history:
        Thread(target=record_async, daemon=True).start()
    return snapshot


def load_snapshot(args: argparse.Namespace) -> Dict[str, Any]:
    average_burn_minutes = int(getattr(args, "average_burn_minutes", 60) or 60)
    if args.no_cache:
        events = load_events(Path(args.codex_root), include_archived=not args.no_archived)
    else:
        with connect(Path(args.db) if args.db else None) as conn:
            if not args.cache_only:
                sync_from_logs(conn, Path(args.codex_root), include_archived=not args.no_archived)
            events = load_events_from_db(conn)
            if args.cache_only and not events:
                sync_from_logs(conn, Path(args.codex_root), include_archived=not args.no_archived)
                events = load_events_from_db(conn)
    return build_snapshot(events, average_burn_minutes=average_burn_minutes).to_dict()


def _dashboard_cache_meta(source: str) -> Dict[str, Any]:
    with DASHBOARD_CACHE_LOCK:
        return {
            "source": source,
            "cached_at": DASHBOARD_CACHE.get("cached_at"),
            "data_read_at": DASHBOARD_CACHE.get("data_read_at") or DASHBOARD_CACHE.get("cached_at"),
            "latest_event_at": DASHBOARD_CACHE.get("latest_event_at"),
            "sync_in_progress": bool(DASHBOARD_CACHE.get("sync_in_progress")),
            "last_sync_started_at": DASHBOARD_CACHE.get("last_sync_started_at"),
            "last_sync_finished_at": DASHBOARD_CACHE.get("last_sync_finished_at"),
            "last_error": DASHBOARD_CACHE.get("last_error"),
            "refresh_interval_seconds": int(DASHBOARD_SYNC_INTERVAL_SECONDS),
        }


def _store_dashboard_snapshot(
    snapshot: Dict[str, Any],
    source: str,
    events: list[Any] | None = None,
    average_burn_minutes: int = 60,
) -> Dict[str, Any]:
    now_iso = datetime.now().astimezone().isoformat()
    stored_snapshot = _trim_dashboard_payload(json.loads(json.dumps(snapshot, ensure_ascii=False)))
    latest_event = snapshot.get("latest_event") or {}
    with DASHBOARD_CACHE_LOCK:
        DASHBOARD_CACHE["snapshot"] = stored_snapshot
        if events is not None:
            DASHBOARD_CACHE["events"] = events
        DASHBOARD_CACHE["cached_at"] = now_iso
        DASHBOARD_CACHE["data_read_at"] = now_iso
        DASHBOARD_CACHE["latest_event_at"] = latest_event.get("timestamp")
        DASHBOARD_CACHE["last_error"] = None
        DASHBOARD_CACHE["average_burn_minutes"] = int(average_burn_minutes or 60)
    response = json.loads(json.dumps(stored_snapshot, ensure_ascii=False))
    response["dashboard_cache"] = _dashboard_cache_meta(source)
    return response


def _dashboard_cached_snapshot(average_burn_minutes: int) -> Dict[str, Any] | None:
    with DASHBOARD_CACHE_LOCK:
        events = DASHBOARD_CACHE.get("events")
        snapshot = DASHBOARD_CACHE.get("snapshot")
        cached_average = int(DASHBOARD_CACHE.get("average_burn_minutes") or 60)
        if snapshot is not None and cached_average == int(average_burn_minutes or 60):
            copied = json.loads(json.dumps(snapshot, ensure_ascii=False))
            copied["dashboard_cache"] = _dashboard_cache_meta("memory")
            return copied
        if events is not None:
            event_list = list(events)
        elif snapshot is not None:
            copied = json.loads(json.dumps(snapshot, ensure_ascii=False))
            copied["dashboard_cache"] = _dashboard_cache_meta("memory")
            return copied
        else:
            return None
    snapshot = build_snapshot(event_list, average_burn_minutes=average_burn_minutes).to_dict()
    snapshot["dashboard_cache"] = _dashboard_cache_meta("memory")
    return snapshot


def _load_dashboard_snapshot_from_db(db_path: Path | None = None, average_burn_minutes: int = 60) -> Dict[str, Any]:
    events = load_events_from_db_readonly(db_path)
    snapshot = build_snapshot(events, average_burn_minutes=average_burn_minutes).to_dict()
    return _store_dashboard_snapshot(snapshot, "sqlite", events=events, average_burn_minutes=average_burn_minutes)


def _sync_dashboard_snapshot(codex_root: Path, db_path: Path | None, include_archived: bool) -> None:
    if not DASHBOARD_SYNC_LOCK.acquire(blocking=False):
        return
    with DASHBOARD_CACHE_LOCK:
        DASHBOARD_CACHE["sync_in_progress"] = True
        DASHBOARD_CACHE["last_sync_started_at"] = datetime.now().astimezone().isoformat()
        DASHBOARD_CACHE["last_error"] = None
    try:
        with connect(db_path) as conn:
            sync_from_logs(conn, codex_root, include_archived=include_archived)
        events = load_events_from_db_readonly(db_path)
        snapshot = build_snapshot(events).to_dict()
        _store_dashboard_snapshot(snapshot, "sync", events=events, average_burn_minutes=60)
        with DASHBOARD_CACHE_LOCK:
            DASHBOARD_CACHE["last_sync_finished_at"] = datetime.now().astimezone().isoformat()
    except Exception as exc:  # Dashboard must stay responsive even if a log file or DB write fails.
        with DASHBOARD_CACHE_LOCK:
            DASHBOARD_CACHE["last_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        with DASHBOARD_CACHE_LOCK:
            DASHBOARD_CACHE["sync_in_progress"] = False
        DASHBOARD_SYNC_LOCK.release()


def _maybe_start_dashboard_sync(codex_root: Path, db_path: Path | None, include_archived: bool, force: bool = False) -> None:
    with DASHBOARD_CACHE_LOCK:
        started = DASHBOARD_CACHE.get("last_sync_started_at")
        in_progress = bool(DASHBOARD_CACHE.get("sync_in_progress"))
    if in_progress:
        return
    if not force and started:
        try:
            last_started = datetime.fromisoformat(str(started))
            if (datetime.now().astimezone() - last_started).total_seconds() < DASHBOARD_SYNC_INTERVAL_SECONDS:
                return
        except ValueError:
            pass
    Thread(
        target=_sync_dashboard_snapshot,
        args=(codex_root, db_path, include_archived),
        daemon=True,
    ).start()


def load_dashboard_snapshot(
    codex_root: Path,
    db_path: Path | None = None,
    include_archived: bool = True,
    force_sync: bool = False,
    average_burn_minutes: int = 60,
    history_days: int = MONITOR_HISTORY_DAYS,
    include_history: bool = True,
) -> Dict[str, Any]:
    average_burn_minutes = max(1, int(average_burn_minutes or 60))
    history_days = min(max(1, int(history_days or MONITOR_HISTORY_DAYS)), MAX_DASHBOARD_HISTORY_DAYS)
    if force_sync:
        _sync_dashboard_snapshot(codex_root, db_path, include_archived)
        snapshot = _dashboard_cached_snapshot(average_burn_minutes)
        if snapshot is not None:
            snapshot["dashboard_cache"] = _dashboard_cache_meta("sync")
            return _record_and_attach_monitor_history(
                snapshot,
                db_path,
                "dashboard_sync",
                history_days=history_days,
                include_history=include_history,
                record_sample=include_history,
            )

    cached = _dashboard_cached_snapshot(average_burn_minutes)
    if cached is not None:
        if include_history:
            _maybe_start_dashboard_sync(codex_root, db_path, include_archived)
        return _record_and_attach_monitor_history(
            cached,
            db_path,
            "dashboard_cached",
            history_days=history_days,
            include_history=include_history,
            record_sample=include_history,
        )

    try:
        snapshot = _load_dashboard_snapshot_from_db(db_path, average_burn_minutes=average_burn_minutes)
    except Exception as exc:
        with DASHBOARD_CACHE_LOCK:
            DASHBOARD_CACHE["last_error"] = f"{type(exc).__name__}: {exc}"
        snapshot = build_snapshot([]).to_dict()
        snapshot["dashboard_cache"] = _dashboard_cache_meta("empty")
    if include_history:
        _maybe_start_dashboard_sync(codex_root, db_path, include_archived)
    return _record_and_attach_monitor_history(
        snapshot,
        db_path,
        "dashboard_sqlite",
        history_days=history_days,
        include_history=include_history,
        record_sample=include_history,
    )


def command_now(args: argparse.Namespace) -> int:
    snapshot = load_snapshot(args)
    latest = snapshot["latest_event"]
    if not latest:
        print("No Codex token_count events found.")
        return 1

    primary = latest["primary"]
    secondary = latest["secondary"]
    total = latest["total_usage"]
    last = latest["last_usage"]

    print("Codex Token Monitor")
    print(f"Generated: {snapshot['generated_at']}")
    print(f"Plan: {latest.get('plan_type') or '--'}")
    print(f"5h window: {format_percent(primary.get('used_percent'))} used, resets {primary.get('resets_at_iso') or '--'}")
    print(f"Weekly window: {format_percent(secondary.get('used_percent'))} used, resets {secondary.get('resets_at_iso') or '--'}")
    print(f"Context: {format_percent(latest.get('context_used_percent'))} of {format_tokens(latest.get('model_context_window') or 0)}")
    print(
        "Total tokens: "
        f"{format_tokens(total['total_tokens'])} "
        f"(input {format_tokens(total['input_tokens'])}, cached {format_tokens(total['cached_input_tokens'])}, "
        f"output {format_tokens(total['output_tokens'])}, reasoning {format_tokens(total['reasoning_output_tokens'])})"
    )
    print(f"Last turn: {format_tokens(last['total_tokens'])} tokens")
    one_hour_window = next((item for item in snapshot.get("burn_rate_windows", []) if item.get("key") == "1h"), None)
    if one_hour_window and one_hour_window.get("percent_per_hour") is not None:
        print(f"1h average burn rate: {one_hour_window['percent_per_hour']:.2f}% / hour")
    if snapshot["average_burn_rate_primary_percent_per_hour"] is not None:
        print(
            "Custom average burn rate: "
            f"{snapshot['average_burn_rate_primary_percent_per_hour']:.2f}% / hour "
            f"over {snapshot['average_burn_rate_interval_minutes']} minutes"
        )
    print(f"Recent sessions: {len(snapshot['sessions'])}")
    for alert in snapshot["alerts"]:
        print(f"[{alert['severity'].upper()}] {alert['message']}")
    return 0


def command_json(args: argparse.Namespace) -> int:
    print(json.dumps(load_snapshot(args), ensure_ascii=False, indent=2))
    return 0


def command_menu(args: argparse.Namespace) -> int:
    events = load_recent_events_from_db(Path(args.db) if args.db else None, limit=args.menu_limit)
    if not events:
        print("Codex --")
        print("---")
        print("No cached data")
        return 0
    snapshot = build_snapshot(events).to_dict()
    if getattr(args, "history_log", False):
        def record_menu_async() -> None:
            try:
                with connect(Path(args.db) if args.db else None) as conn:
                    record_monitor_sample(conn, snapshot, source="swiftbar", min_interval_seconds=60)
            except Exception:
                return

        Thread(target=record_menu_async, daemon=True).start()
    latest = snapshot.get("latest_event") or {}
    primary = latest.get("primary") or {}
    secondary = latest.get("secondary") or {}
    total = latest.get("total_usage") or {}
    all_time_total_tokens = load_all_time_total_token_usage_from_db(Path(args.db) if args.db else None)
    if all_time_total_tokens is None:
        all_time_total_tokens = int(total.get("total_tokens") or 0)
    alerts = snapshot.get("alerts") or []

    def pct(value: Any, digits: int = 0) -> str:
        return "--" if value is None else f"{float(value):.{digits}f}%"

    def remaining(value: Any) -> float | None:
        if value is None:
            return None
        return max(0.0, 100.0 - float(value))

    def color_for_remaining(value: float | None) -> str:
        if value is None:
            return "gray"
        if value > 50:
            return "#00A3FF"
        if value >= 10:
            return "#7C5CFF"
        return "#FF3B30"

    def menu_text(value: Any) -> str:
        text = str(value or "--")
        return "".join(" / " if ch in {"\n", "\r", "|"} else ch for ch in text if ch == "\t" or ord(ch) >= 32).strip()

    def reset_minutes(reset_value: Any) -> int | None:
        if reset_value is None:
            return None
        return max(0, int((int(reset_value) - time.time() + 59) // 60))

    def reset_time(reset_value: Any) -> str:
        if reset_value is None:
            return "--"
        reset_dt = datetime.fromtimestamp(int(reset_value)).astimezone()
        now_dt = datetime.now().astimezone()
        if reset_dt.date() == now_dt.date():
            return reset_dt.strftime("%H:%M")
        return reset_dt.strftime("%Y-%m-%d %H:%M")

    primary_left = remaining(primary.get("used_percent"))
    secondary_left = remaining(secondary.get("used_percent"))
    color = color_for_remaining(primary_left)
    if primary_left == 0:
        minutes = reset_minutes(primary.get("resets_at"))
        title_text = f"Codex {minutes}m reset" if minutes is not None else "Codex reset soon"
    else:
        title_text = f"Codex {pct(primary_left)} left"
    print(f"{title_text} | color={color}")
    print("---")
    print(f"5h reset: {reset_time(primary.get('resets_at'))}")
    if primary_left == 0:
        minutes = reset_minutes(primary.get("resets_at"))
        print(f"Reset countdown: {minutes} min" if minutes is not None else "Reset countdown: --")
    print(f"Weekly left: {pct(secondary_left, 2)}")
    print(f"Total Token Usage: {format_tokens(int(all_time_total_tokens or 0))}")
    print(f"Plan: {menu_text(latest.get('plan_type') or '--')}")
    if alerts:
        print("---")
        for alert in alerts[:5]:
            print(f"{menu_text(str(alert['severity']).upper())}: {menu_text(alert['message'])}")
    print("---")
    print(f"Open dashboard | href={args.dashboard_url}")
    print("Refresh | refresh=true")
    return 0


def command_report(args: argparse.Namespace) -> int:
    snapshot = load_snapshot(args)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = Path(args.output) if args.output else REPORTS_DIR / "codex_usage_report.json"
    csv_path = json_path.with_suffix(".csv")
    md_path = json_path.with_suffix(".md")

    json_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["date", "sessions", "events", "latest_total_tokens_sum", "latest_output_tokens_sum", "latest_reasoning_tokens_sum"],
        )
        writer.writeheader()
        writer.writerows(snapshot["daily"])

    latest = snapshot["latest_event"] or {}
    primary = latest.get("primary") or {}
    secondary = latest.get("secondary") or {}
    lines = [
        "# Codex Token Report",
        "",
        f"- Generated: `{snapshot['generated_at']}`",
        f"- Plan: `{latest.get('plan_type') or '--'}`",
        f"- 5h window used: `{format_percent(primary.get('used_percent'))}`",
        f"- Weekly window used: `{format_percent(secondary.get('used_percent'))}`",
        f"- Recent sessions: `{len(snapshot['sessions'])}`",
        "",
        "## Alerts",
        "",
    ]
    if snapshot["alerts"]:
        lines.extend(f"- [{item['severity']}] {item['message']}" for item in snapshot["alerts"])
    else:
        lines.append("- None")
    lines.extend(["", "## Daily Summary", ""])
    for row in snapshot["daily"][-14:]:
        lines.append(f"- {row['date']}: {row['sessions']} sessions, {format_tokens(row['latest_total_tokens_sum'])} latest-token sum")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Saved: {json_path}")
    print(f"Saved: {csv_path}")
    print(f"Saved: {md_path}")
    return 0


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args: Any,
        codex_root: Path,
        db_path: Path | None,
        include_archived: bool,
        access_token: str | None,
        **kwargs: Any,
    ) -> None:
        self.codex_root = codex_root
        self.db_path = db_path
        self.include_archived = include_archived
        self.access_token = access_token
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self) -> None:
        cookie_token = getattr(self, "_set_access_cookie", None)
        if cookie_token:
            self.send_header("Set-Cookie", f"codex_usage_token={cookie_token}; Path=/; SameSite=Lax")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def _cookie_token(self) -> str:
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
        except Exception:
            return ""
        morsel = cookie.get("codex_usage_token")
        return morsel.value if morsel else ""

    def _authorized(self, query: Dict[str, list[str]]) -> bool:
        if _is_local_client(str(self.client_address[0])):
            return True
        if not self.access_token:
            return False
        supplied = query.get("token", [""])[0] or self.headers.get("X-Codex-Usage-Token", "") or self._cookie_token()
        authorized = hmac.compare_digest(str(supplied), self.access_token)
        if authorized and query.get("token", [""])[0]:
            self._set_access_cookie = str(supplied)
        return authorized

    def _send_text(self, status: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "text/plain; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        parsed_for_cookie = urlparse(self.path)
        query_for_cookie = parse_qs(parsed_for_cookie.query)
        if self.access_token and query_for_cookie.get("token", [""])[0]:
            supplied = query_for_cookie.get("token", [""])[0]
            if hmac.compare_digest(str(supplied), self.access_token):
                self._set_access_cookie = str(supplied)
        elif (
            self.access_token
            and not _is_local_client(str(self.client_address[0]))
            and parsed_for_cookie.path in {"/", "/index.html"}
        ):
            self._set_access_cookie = self.access_token
        if self.path.startswith("/api/snapshot"):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            if not self._authorized(query):
                self._send_text(403, "Forbidden")
                return
            force_sync = query.get("force", ["0"])[0] in {"1", "true", "yes"}
            include_history = query.get("include_history", ["1"])[0] not in {"0", "false", "no"}
            try:
                average_burn_minutes = max(1, int(query.get("avg_minutes", ["60"])[0]))
            except (TypeError, ValueError):
                average_burn_minutes = 60
            try:
                history_days = min(max(1, int(query.get("history_days", [str(MONITOR_HISTORY_DAYS)])[0])), MAX_DASHBOARD_HISTORY_DAYS)
            except (TypeError, ValueError):
                history_days = MONITOR_HISTORY_DAYS
            payload = json.dumps(
                load_dashboard_snapshot(
                    self.codex_root,
                    db_path=self.db_path,
                    include_archived=self.include_archived,
                    force_sync=force_sync,
                    average_burn_minutes=average_burn_minutes,
                    history_days=history_days,
                    include_history=include_history,
                ),
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("cache-control", "no-store")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/widget":
            self.path = "/widget.html"
        return super().do_GET()


def command_dashboard(args: argparse.Namespace) -> int:
    def handler(*handler_args: Any, **handler_kwargs: Any) -> DashboardHandler:
        return DashboardHandler(
            *handler_args,
            codex_root=Path(args.codex_root),
            db_path=Path(args.db) if args.db else None,
            include_archived=not args.no_archived,
            access_token=access_token,
            **handler_kwargs,
        )

    host = str(args.host or "127.0.0.1")
    access_token = _dashboard_access_token(create=host in {"0.0.0.0", "::"})
    address = (host, int(args.port))
    httpd = ThreadingHTTPServer(address, handler)
    display_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    print(f"Dashboard: http://{display_host}:{args.port}/")
    print(f"Widget:    http://{display_host}:{args.port}/widget")
    if host == "0.0.0.0":
        print("LAN mode: open http://<this-mac-ip>:{}/ from another device on the same Wi-Fi.".format(args.port))
        if access_token:
            print("LAN access token is required for API requests.")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def command_watch(args: argparse.Namespace) -> int:
    while True:
        print("\033[2J\033[H", end="")
        command_now(args)
        time.sleep(float(args.interval))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex-only local usage monitor")
    parser.add_argument("--codex-root", default=str(DEFAULT_CODEX_ROOT), help="Codex data directory")
    parser.add_argument("--no-archived", action="store_true", help="Skip archived_sessions")
    parser.add_argument("--no-cache", action="store_true", help="Scan JSONL files directly instead of using SQLite cache")
    parser.add_argument("--cache-only", action="store_true", help="Read existing SQLite cache without syncing logs first")
    parser.add_argument("--db", default=str(default_db_path()), help="SQLite cache path")
    parser.add_argument("--average-burn-minutes", default=60, type=int, help="Average burn-rate interval in minutes")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("now", help="Print current usage snapshot").set_defaults(func=command_now)
    sub.add_parser("json", help="Print full JSON snapshot").set_defaults(func=command_json)
    menu = sub.add_parser("menu", help="Print xbar/SwiftBar menu output from cache")
    menu.add_argument("--dashboard-url", default="http://127.0.0.1:8766/")
    menu.add_argument("--menu-limit", default=500, type=int)
    menu.add_argument("--no-history-log", dest="history_log", action="store_false", help="Do not record this menu refresh as a monitor sample")
    menu.set_defaults(history_log=True)
    menu.set_defaults(func=command_menu)
    report = sub.add_parser("report", help="Write JSON, CSV, and Markdown reports")
    report.add_argument("--output", default=None, help="Output JSON path")
    report.set_defaults(func=command_report)
    dashboard = sub.add_parser("dashboard", help="Serve local dashboard")
    dashboard.add_argument("--host", default="127.0.0.1", help="Bind host. Use 0.0.0.0 for same-Wi-Fi phone access.")
    dashboard.add_argument("--port", default=8765, type=int)
    dashboard.set_defaults(func=command_dashboard)
    watch = sub.add_parser("watch", help="Live terminal snapshot")
    watch.add_argument("--interval", default=5.0, type=float)
    watch.set_defaults(func=command_watch)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
