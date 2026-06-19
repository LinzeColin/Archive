from __future__ import annotations

import json
import sqlite3
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .models import TokenCountEvent
from .parser import iter_log_files, parse_token_count_events


SCHEMA = """
CREATE TABLE IF NOT EXISTS token_events (
  event_id TEXT PRIMARY KEY,
  timestamp TEXT NOT NULL,
  session_id TEXT NOT NULL,
  cwd TEXT,
  originator TEXT,
  source_file TEXT NOT NULL,
  total_tokens INTEGER NOT NULL,
  input_tokens INTEGER NOT NULL,
  cached_input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  reasoning_output_tokens INTEGER NOT NULL,
  last_total_tokens INTEGER NOT NULL,
  model_context_window INTEGER,
  primary_used_percent REAL,
  primary_window_minutes INTEGER,
  primary_resets_at INTEGER,
  secondary_used_percent REAL,
  secondary_window_minutes INTEGER,
  secondary_resets_at INTEGER,
  plan_type TEXT,
  limit_id TEXT,
  rate_limit_reached_type TEXT,
  raw_metrics_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_token_events_timestamp ON token_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_token_events_session ON token_events(session_id);

CREATE TABLE IF NOT EXISTS file_state (
  path TEXT PRIMARY KEY,
  size INTEGER NOT NULL,
  mtime_ns INTEGER NOT NULL,
  scanned_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monitor_samples (
  sampled_at TEXT PRIMARY KEY,
  sample_bucket_at TEXT,
  source TEXT NOT NULL,
  latest_event_at TEXT,
  primary_used_percent REAL,
  primary_remaining_percent REAL,
  secondary_used_percent REAL,
  secondary_remaining_percent REAL,
  active_sessions INTEGER,
  total_sessions INTEGER,
  token_count_events INTEGER,
  threads_working INTEGER,
  agents_working INTEGER,
  projects_working INTEGER,
  latest_total_tokens_sum INTEGER,
  latest_upload_tokens_sum INTEGER,
  latest_output_tokens_sum INTEGER,
  latest_contextual_tokens_sum INTEGER,
  latest_reasoning_tokens_sum INTEGER,
  average_burn_rate_primary_percent_per_hour REAL,
  one_hour_burn_rate_primary_percent_per_hour REAL,
  summary_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_monitor_samples_sampled_at ON monitor_samples(sampled_at);
CREATE INDEX IF NOT EXISTS idx_monitor_samples_source ON monitor_samples(source);
"""


def default_db_path() -> Path:
    return Path.home() / ".codex_usage_monitor" / "usage.sqlite"


def connect(db_path: Path | None = None, timeout: float = 30) -> sqlite3.Connection:
    path = db_path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    conn = sqlite3.connect(path, timeout=timeout)
    conn.execute(f"PRAGMA busy_timeout = {max(1, int(timeout * 1000))}")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    _migrate_schema(conn)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return conn


def _migrate_schema(conn: sqlite3.Connection) -> None:
    monitor_columns = {row[1] for row in conn.execute("PRAGMA table_info(monitor_samples)").fetchall()}
    if "sample_bucket_at" not in monitor_columns:
        conn.execute("ALTER TABLE monitor_samples ADD COLUMN sample_bucket_at TEXT")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_monitor_samples_source_bucket
        ON monitor_samples(source, sample_bucket_at)
        WHERE sample_bucket_at IS NOT NULL
        """
    )
    conn.commit()


def upsert_events(conn: sqlite3.Connection, events: Iterable[TokenCountEvent]) -> int:
    count = 0
    for event in events:
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR IGNORE INTO token_events(
              event_id, timestamp, session_id, cwd, originator, source_file,
              total_tokens, input_tokens, cached_input_tokens, output_tokens,
              reasoning_output_tokens, last_total_tokens, model_context_window,
              primary_used_percent, primary_window_minutes, primary_resets_at,
              secondary_used_percent, secondary_window_minutes, secondary_resets_at,
              plan_type, limit_id, rate_limit_reached_type, raw_metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.timestamp.isoformat(),
                event.session_id,
                event.cwd,
                event.originator,
                event.source_file,
                event.total_usage.total_tokens,
                event.total_usage.input_tokens,
                event.total_usage.cached_input_tokens,
                event.total_usage.output_tokens,
                event.total_usage.reasoning_output_tokens,
                event.last_usage.total_tokens,
                event.model_context_window,
                event.primary.used_percent,
                event.primary.window_minutes,
                event.primary.resets_at,
                event.secondary.used_percent,
                event.secondary.window_minutes,
                event.secondary.resets_at,
                event.plan_type,
                event.limit_id,
                event.rate_limit_reached_type,
                json.dumps(event.to_dict(), ensure_ascii=False),
            ),
        )
        if conn.total_changes > before:
            count += 1
    conn.commit()
    return count


def sync_from_logs(conn: sqlite3.Connection, codex_root: Path, include_archived: bool = True) -> int:
    inserted = 0
    for path in iter_log_files(codex_root, include_archived=include_archived):
        try:
            stat = path.stat()
        except OSError:
            continue
        row = conn.execute("SELECT size, mtime_ns FROM file_state WHERE path = ?", (str(path),)).fetchone()
        if row and int(row[0]) == stat.st_size and int(row[1]) == stat.st_mtime_ns:
            continue
        inserted += upsert_events(conn, parse_token_count_events(path))
        conn.execute(
            "INSERT OR REPLACE INTO file_state(path, size, mtime_ns, scanned_at) VALUES (?, ?, ?, datetime('now'))",
            (str(path), stat.st_size, stat.st_mtime_ns),
        )
    conn.commit()
    return inserted


def load_events_from_db(conn: sqlite3.Connection) -> List[TokenCountEvent]:
    rows = conn.execute("SELECT raw_metrics_json FROM token_events ORDER BY timestamp").fetchall()
    events = []
    for (raw_json,) in rows:
        try:
            events.append(TokenCountEvent.from_dict(json.loads(raw_json)))
        except (KeyError, TypeError, json.JSONDecodeError, ValueError):
            continue
    return events


def load_events_from_db_readonly(db_path: Path | None = None) -> List[TokenCountEvent]:
    path = db_path or default_db_path()
    if not path.exists():
        return []
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    try:
        conn.execute("PRAGMA busy_timeout = 2000")
        rows = conn.execute("SELECT raw_metrics_json FROM token_events ORDER BY timestamp").fetchall()
    finally:
        conn.close()
    events = []
    for (raw_json,) in rows:
        try:
            events.append(TokenCountEvent.from_dict(json.loads(raw_json)))
        except (KeyError, TypeError, json.JSONDecodeError, ValueError):
            continue
    return events


def load_recent_events_from_db(db_path: Path | None = None, limit: int = 500) -> List[TokenCountEvent]:
    path = db_path or default_db_path()
    if not path.exists():
        return []
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    try:
        rows = conn.execute(
            "SELECT raw_metrics_json FROM token_events ORDER BY timestamp DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    finally:
        conn.close()
    events = []
    for (raw_json,) in rows:
        try:
            events.append(TokenCountEvent.from_dict(json.loads(raw_json)))
        except (KeyError, TypeError, json.JSONDecodeError, ValueError):
            continue
    events.sort(key=lambda event: event.timestamp)
    return events


def load_all_time_total_token_usage_from_db(db_path: Path | None = None) -> int | None:
    path = db_path or default_db_path()
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error:
        return None
    try:
        conn.execute("PRAGMA busy_timeout = 2000")
        row = conn.execute(
            """
            SELECT COALESCE(SUM(latest_total), 0)
            FROM (
              SELECT e.session_id, MAX(e.total_tokens) AS latest_total
              FROM token_events e
              JOIN (
                SELECT session_id, MAX(timestamp) AS max_timestamp
                FROM token_events
                GROUP BY session_id
              ) latest
                ON latest.session_id = e.session_id
               AND latest.max_timestamp = e.timestamp
              GROUP BY e.session_id
            )
            """
        ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    return int(row[0] or 0) if row else 0


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _minute_bucket(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(second=0, microsecond=0).isoformat()


def _find_burn_window(snapshot: Dict[str, Any], key: str) -> Dict[str, Any]:
    for item in snapshot.get("burn_rate_windows") or []:
        if item.get("key") == key:
            return item
    return {}


def backfill_monitor_samples_from_events(conn: sqlite3.Connection) -> int:
    before = conn.total_changes
    conn.execute(
        """
        INSERT OR IGNORE INTO monitor_samples(
          sampled_at, source, latest_event_at,
          primary_used_percent, primary_remaining_percent,
          secondary_used_percent, secondary_remaining_percent,
          active_sessions, total_sessions, token_count_events,
          threads_working, agents_working, projects_working,
          latest_total_tokens_sum, latest_upload_tokens_sum, latest_output_tokens_sum,
          latest_contextual_tokens_sum, latest_reasoning_tokens_sum,
          average_burn_rate_primary_percent_per_hour, one_hour_burn_rate_primary_percent_per_hour,
          summary_json
        )
        SELECT
          timestamp,
          'codex_log_backfill',
          timestamp,
          primary_used_percent,
          CASE WHEN primary_used_percent IS NULL THEN NULL ELSE MAX(0, 100.0 - primary_used_percent) END,
          secondary_used_percent,
          CASE WHEN secondary_used_percent IS NULL THEN NULL ELSE MAX(0, 100.0 - secondary_used_percent) END,
          NULL,
          NULL,
          1,
          NULL,
          NULL,
          NULL,
          total_tokens,
          MAX(0, input_tokens - cached_input_tokens),
          output_tokens,
          cached_input_tokens,
          reasoning_output_tokens,
          NULL,
          NULL,
          json_object(
            'source', 'codex_log_backfill',
            'event_id', event_id,
            'session_id', session_id,
            'cwd', cwd
          )
        FROM token_events
        ORDER BY timestamp
        """
    )
    conn.commit()
    return conn.total_changes - before


def record_monitor_sample(
    conn: sqlite3.Connection,
    snapshot: Dict[str, Any],
    source: str,
    min_interval_seconds: int = 20,
) -> bool:
    latest = snapshot.get("latest_event") or {}
    primary = latest.get("primary") or {}
    secondary = latest.get("secondary") or {}
    totals = snapshot.get("totals") or {}
    one_hour = _find_burn_window(snapshot, "1h")
    now = datetime.now(timezone.utc)
    sample_bucket_at = _minute_bucket(now) if min_interval_seconds >= 60 and source != "codex_log_backfill" else None

    if sample_bucket_at is None:
        last_row = conn.execute(
            "SELECT sampled_at FROM monitor_samples WHERE source = ? ORDER BY sampled_at DESC LIMIT 1",
            (source,),
        ).fetchone()
        if last_row and min_interval_seconds > 0:
            last_at = _parse_iso(str(last_row[0]))
            elapsed_seconds = (now - last_at).total_seconds() if last_at else None
            if elapsed_seconds is not None and -300 <= elapsed_seconds < min_interval_seconds:
                return False

    summary = {
        "source": source,
        "generated_at": snapshot.get("generated_at"),
        "dashboard_cache": snapshot.get("dashboard_cache"),
        "latest_event_at": latest.get("timestamp"),
        "plan_type": latest.get("plan_type"),
    }
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO monitor_samples(
          sampled_at, sample_bucket_at, source, latest_event_at,
          primary_used_percent, primary_remaining_percent,
          secondary_used_percent, secondary_remaining_percent,
          active_sessions, total_sessions, token_count_events,
          threads_working, agents_working, projects_working,
          latest_total_tokens_sum, latest_upload_tokens_sum, latest_output_tokens_sum,
          latest_contextual_tokens_sum, latest_reasoning_tokens_sum,
          average_burn_rate_primary_percent_per_hour, one_hour_burn_rate_primary_percent_per_hour,
          summary_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now.isoformat(),
            sample_bucket_at,
            source,
            latest.get("timestamp"),
            primary.get("used_percent"),
            primary.get("remaining_percent"),
            secondary.get("used_percent"),
            secondary.get("remaining_percent"),
            totals.get("active_sessions"),
            totals.get("sessions"),
            totals.get("token_count_events"),
            totals.get("threads_working"),
            totals.get("agents_working"),
            totals.get("projects_working"),
            totals.get("latest_total_tokens_sum"),
            totals.get("latest_upload_tokens_sum"),
            totals.get("latest_output_tokens_sum"),
            totals.get("latest_contextual_tokens_sum"),
            totals.get("latest_reasoning_tokens_sum"),
            snapshot.get("average_burn_rate_primary_percent_per_hour"),
            one_hour.get("percent_per_hour"),
            json.dumps(summary, ensure_ascii=False),
        ),
    )
    conn.commit()
    return cursor.rowcount > 0


def load_monitor_history_from_db(
    conn: sqlite3.Connection,
    days: int = 14,
    limit: int = 100000,
) -> Dict[str, Any]:
    retention_days = max(1, int(days or 14))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)
    upper_cutoff = now + timedelta(minutes=5)
    try:
        rows = conn.execute(
            """
            SELECT
              sampled_at, source, latest_event_at,
              primary_used_percent, primary_remaining_percent,
              secondary_used_percent, secondary_remaining_percent,
              active_sessions, total_sessions, token_count_events,
              threads_working, agents_working, projects_working,
              latest_total_tokens_sum, latest_upload_tokens_sum, latest_output_tokens_sum,
              latest_contextual_tokens_sum, latest_reasoning_tokens_sum,
              average_burn_rate_primary_percent_per_hour, one_hour_burn_rate_primary_percent_per_hour
            FROM monitor_samples
            WHERE sampled_at >= ? AND sampled_at <= ?
            ORDER BY sampled_at ASC
            """,
            (cutoff.isoformat(), upper_cutoff.isoformat()),
        )
    except sqlite3.OperationalError:
        return empty_monitor_history(retention_days)

    keys = [
        "sampled_at",
        "source",
        "latest_event_at",
        "primary_used_percent",
        "primary_remaining_percent",
        "secondary_used_percent",
        "secondary_remaining_percent",
        "active_sessions",
        "total_sessions",
        "token_count_events",
        "threads_working",
        "agents_working",
        "projects_working",
        "latest_total_tokens_sum",
        "latest_upload_tokens_sum",
        "latest_output_tokens_sum",
        "latest_contextual_tokens_sum",
        "latest_reasoning_tokens_sum",
        "average_burn_rate_primary_percent_per_hour",
        "one_hour_burn_rate_primary_percent_per_hour",
    ]
    hourly = [
        {"hour": hour, "samples": 0, "monitor_samples": 0, "backfill_samples": 0, "active_samples": 0}
        for hour in range(24)
    ]
    daily: Dict[str, Dict[str, Any]] = {}
    weekly: Dict[str, Dict[str, Any]] = {}
    source_counts: Dict[str, int] = {}
    recent_samples: deque[Dict[str, Any]] = deque(maxlen=240)
    window_samples: deque[Dict[str, Any]] = deque(maxlen=5000)
    first_sample_at = None
    last_sample_at = None
    sample_count = 0
    for row in rows:
        sample = dict(zip(keys, row))
        sample_count += 1
        if first_sample_at is None:
            first_sample_at = sample.get("sampled_at")
        last_sample_at = sample.get("sampled_at")
        recent_samples.append(sample)
        window_samples.append(
            {
                "sampled_at": sample.get("sampled_at"),
                "source": sample.get("source"),
                "primary_used_percent": sample.get("primary_used_percent"),
                "primary_remaining_percent": sample.get("primary_remaining_percent"),
                "secondary_used_percent": sample.get("secondary_used_percent"),
                "secondary_remaining_percent": sample.get("secondary_remaining_percent"),
                "latest_total_tokens_sum": sample.get("latest_total_tokens_sum"),
            }
        )
        sampled_at = _parse_iso(str(sample.get("sampled_at") or ""))
        if sampled_at:
            local_dt = sampled_at.astimezone()
            hour = local_dt.hour
            day = local_dt.date().isoformat()
            week_start_date = (local_dt.date() - timedelta(days=local_dt.weekday()))
            week_end_date = week_start_date + timedelta(days=6)
            week_start = week_start_date.isoformat()
            week_end = week_end_date.isoformat()
        else:
            hour = 0
            day = "unknown"
            week_start = "unknown"
            week_end = "unknown"
        source = str(sample.get("source") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
        hourly[hour]["samples"] += 1
        if source == "codex_log_backfill":
            hourly[hour]["backfill_samples"] += 1
        else:
            hourly[hour]["monitor_samples"] += 1
        if int(sample.get("active_sessions") or 0) > 0:
            hourly[hour]["active_samples"] += 1
        if day not in daily:
            daily[day] = {
                "date": day,
                "samples": 0,
                "monitor_samples": 0,
                "backfill_samples": 0,
                "max_active_sessions": 0,
                "last_sample_at": None,
                "latest_total_tokens_sum": 0,
                "latest_upload_tokens_sum": 0,
                "latest_output_tokens_sum": 0,
                "latest_contextual_tokens_sum": 0,
                "latest_reasoning_tokens_sum": 0,
                "hourly": [
                    {"hour": item_hour, "samples": 0, "monitor_samples": 0, "backfill_samples": 0, "active_samples": 0}
                    for item_hour in range(24)
                ],
            }
        daily_row = daily[day]
        daily_row["samples"] += 1
        daily_row["hourly"][hour]["samples"] += 1
        if source == "codex_log_backfill":
            daily_row["backfill_samples"] += 1
            daily_row["hourly"][hour]["backfill_samples"] += 1
        else:
            daily_row["monitor_samples"] += 1
            daily_row["hourly"][hour]["monitor_samples"] += 1
        if int(sample.get("active_sessions") or 0) > 0:
            daily_row["hourly"][hour]["active_samples"] += 1
        daily_row["max_active_sessions"] = max(int(daily_row["max_active_sessions"]), int(sample.get("active_sessions") or 0))
        daily_row["last_sample_at"] = sample.get("sampled_at")
        daily_row["latest_total_tokens_sum"] = int(sample.get("latest_total_tokens_sum") or daily_row["latest_total_tokens_sum"] or 0)
        daily_row["latest_upload_tokens_sum"] = int(sample.get("latest_upload_tokens_sum") or daily_row["latest_upload_tokens_sum"] or 0)
        daily_row["latest_output_tokens_sum"] = int(sample.get("latest_output_tokens_sum") or daily_row["latest_output_tokens_sum"] or 0)
        daily_row["latest_contextual_tokens_sum"] = int(sample.get("latest_contextual_tokens_sum") or daily_row["latest_contextual_tokens_sum"] or 0)
        daily_row["latest_reasoning_tokens_sum"] = int(sample.get("latest_reasoning_tokens_sum") or daily_row["latest_reasoning_tokens_sum"] or 0)

        if week_start not in weekly:
            weekly[week_start] = {
                "week_start": week_start,
                "week_end": week_end,
                "samples": 0,
                "monitor_samples": 0,
                "backfill_samples": 0,
                "max_active_sessions": 0,
                "last_sample_at": None,
                "latest_total_tokens_sum": 0,
                "latest_upload_tokens_sum": 0,
                "latest_output_tokens_sum": 0,
                "latest_contextual_tokens_sum": 0,
                "latest_reasoning_tokens_sum": 0,
                "hourly": [
                    {"hour": item_hour, "samples": 0, "monitor_samples": 0, "backfill_samples": 0, "active_samples": 0}
                    for item_hour in range(24)
                ],
            }
        weekly_row = weekly[week_start]
        weekly_row["samples"] += 1
        weekly_row["hourly"][hour]["samples"] += 1
        if source == "codex_log_backfill":
            weekly_row["backfill_samples"] += 1
            weekly_row["hourly"][hour]["backfill_samples"] += 1
        else:
            weekly_row["monitor_samples"] += 1
            weekly_row["hourly"][hour]["monitor_samples"] += 1
        if int(sample.get("active_sessions") or 0) > 0:
            weekly_row["hourly"][hour]["active_samples"] += 1
        weekly_row["max_active_sessions"] = max(int(weekly_row["max_active_sessions"]), int(sample.get("active_sessions") or 0))
        weekly_row["last_sample_at"] = sample.get("sampled_at")
        weekly_row["latest_total_tokens_sum"] = int(sample.get("latest_total_tokens_sum") or weekly_row["latest_total_tokens_sum"] or 0)
        weekly_row["latest_upload_tokens_sum"] = int(sample.get("latest_upload_tokens_sum") or weekly_row["latest_upload_tokens_sum"] or 0)
        weekly_row["latest_output_tokens_sum"] = int(sample.get("latest_output_tokens_sum") or weekly_row["latest_output_tokens_sum"] or 0)
        weekly_row["latest_contextual_tokens_sum"] = int(sample.get("latest_contextual_tokens_sum") or weekly_row["latest_contextual_tokens_sum"] or 0)
        weekly_row["latest_reasoning_tokens_sum"] = int(sample.get("latest_reasoning_tokens_sum") or weekly_row["latest_reasoning_tokens_sum"] or 0)

    monitor_count = sum(count for source, count in source_counts.items() if source != "codex_log_backfill")
    backfill_count = int(source_counts.get("codex_log_backfill", 0))
    return {
        "sample_count": sample_count,
        "persisted_sample_count": monitor_count,
        "backfill_sample_count": backfill_count,
        "sources": source_counts,
        "first_sample_at": first_sample_at,
        "last_sample_at": last_sample_at,
        "retention_days": retention_days,
        "hourly": hourly,
        "daily": list(daily.values()),
        "weekly": list(weekly.values()),
        "recent": list(recent_samples),
        "window_samples": list(window_samples),
    }


def empty_monitor_history(days: int = 14, error: str | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "sample_count": 0,
        "persisted_sample_count": 0,
        "backfill_sample_count": 0,
        "first_sample_at": None,
        "last_sample_at": None,
        "retention_days": max(1, int(days or 14)),
        "hourly": [],
        "daily": [],
        "weekly": [],
        "recent": [],
        "window_samples": [],
    }
    if error:
        payload["last_error"] = error
    return payload


def load_monitor_history_from_db_readonly(
    db_path: Path | None = None,
    days: int = 14,
    limit: int = 100000,
) -> Dict[str, Any]:
    path = db_path or default_db_path()
    if not path.exists():
        return empty_monitor_history(days)
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
        conn.execute("PRAGMA busy_timeout = 2000")
        try:
            return load_monitor_history_from_db(conn, days=days, limit=limit)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return empty_monitor_history(days, error=f"{type(exc).__name__}: {exc}")
