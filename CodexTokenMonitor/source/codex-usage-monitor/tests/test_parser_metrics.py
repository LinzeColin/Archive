import json
import re
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from codex_usage_monitor import cli
from codex_usage_monitor.cli import command_menu, load_dashboard_snapshot
from codex_usage_monitor.metrics import build_snapshot
from codex_usage_monitor.parser import parse_token_count_events
from codex_usage_monitor.project_names import ProjectNameResolver, load_project_name_resolver
from codex_usage_monitor.storage import (
    backfill_monitor_samples_from_events,
    connect,
    load_all_time_total_token_usage_from_db,
    load_monitor_history_from_db,
    record_monitor_sample,
    upsert_events,
)


EMPTY_RESOLVER = ProjectNameResolver({}, {})


def build_test_snapshot(events, **kwargs):
    kwargs.setdefault("project_name_resolver", EMPTY_RESOLVER)
    return build_snapshot(events, **kwargs).to_dict()


class ParserMetricsTest(unittest.TestCase):
    def test_parse_token_count_without_prompt_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rollout-2026-06-04T00-00-00-test.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "timestamp": "2026-06-04T00:00:00.000Z",
                                "type": "session_meta",
                                "payload": {"id": "session-a", "cwd": "/tmp/project", "originator": "Codex Desktop"},
                            }
                        ),
                        json.dumps(
                            {
                                "timestamp": "2026-06-04T00:01:00.000Z",
                                "type": "event_msg",
                                "payload": {
                                    "type": "token_count",
                                    "info": {
                                        "total_token_usage": {
                                            "input_tokens": 100,
                                            "cached_input_tokens": 50,
                                            "output_tokens": 20,
                                            "reasoning_output_tokens": 5,
                                            "total_tokens": 120,
                                        },
                                        "last_token_usage": {"total_tokens": 30},
                                        "model_context_window": 1000,
                                    },
                                    "rate_limits": {
                                        "primary": {"used_percent": 80, "window_minutes": 300, "resets_at": 1780569473},
                                        "secondary": {"used_percent": 20, "window_minutes": 10080, "resets_at": 1781138233},
                                        "plan_type": "pro",
                                        "limit_id": "codex",
                                    },
                                },
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            events = list(parse_token_count_events(path))
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].session_id, "session-a")
            self.assertEqual(events[0].cwd, "/tmp/project")
            self.assertEqual(events[0].primary.used_percent, 80)
            self.assertEqual(events[0].context_used_percent, 3)

            snapshot = build_test_snapshot(events)
            self.assertEqual(snapshot["latest_event"]["total_usage"]["total_tokens"], 120)
            self.assertEqual(snapshot["totals"]["latest_upload_tokens_sum"], 50)
            self.assertEqual(snapshot["totals"]["latest_input_tokens_sum"], 100)
            self.assertEqual(snapshot["totals"]["latest_cached_input_tokens_sum"], 50)
            self.assertEqual(snapshot["totals"]["latest_contextual_tokens_sum"], 50)
            self.assertEqual(snapshot["totals"]["threads_activated"], 1)
            self.assertEqual(snapshot["totals"]["agents_activated"], 1)
            self.assertEqual(snapshot["totals"]["projects_activated"], 1)
            self.assertEqual(snapshot["top_projects"][0]["threads"], 1)
            self.assertEqual(snapshot["top_projects"][0]["agents"], 1)
            self.assertEqual(snapshot["top_projects"][0]["latest_reasoning_tokens_sum"], 5)
            self.assertTrue(any(pattern["name"] == "Token traffic mix" for pattern in snapshot["behavior_patterns"]))
            self.assertTrue(any(alert["name"] == "primary" for alert in snapshot["alerts"]))
            self.assertIn("day_over_day", snapshot["period_comparisons"])
            self.assertEqual(snapshot["daily"][-1]["agents"], 1)
            self.assertTrue(snapshot["behavior_patterns"])
            self.assertTrue(snapshot["recommendations"])

    def test_project_display_names_use_alias_before_thread_index(self):
        events = list(
            parse_token_count_events_from_dicts(
                [
                    {
                        "event_id": "name-test",
                        "timestamp": "2026-06-04T00:01:00+00:00",
                        "source_file": "/tmp/test.jsonl",
                        "session_id": "session-a",
                        "cwd": "/tmp/project",
                        "originator": "Codex Desktop",
                        "total_usage": {"total_tokens": 120, "input_tokens": 100, "cached_input_tokens": 50, "output_tokens": 20},
                        "last_usage": {"total_tokens": 30},
                        "model_context_window": 1000,
                        "primary": {"used_percent": 40, "window_minutes": 300, "resets_at": 1780569473},
                        "secondary": {"used_percent": 20, "window_minutes": 10080, "resets_at": 1781138233},
                        "plan_type": "pro",
                        "limit_id": "codex",
                        "rate_limit_reached_type": None,
                    }
                ]
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            alias_path = Path(tmp) / "aliases.json"
            index_path = Path(tmp) / "session_index.jsonl"
            alias_path.write_text(json.dumps({"projects": {"/tmp/project": "Custom Research Name"}}), encoding="utf-8")
            index_path.write_text(
                json.dumps({"id": "session-a", "thread_name": "Synced Chat Name", "updated_at": "2026-06-04T00:02:00Z"}) + "\n",
                encoding="utf-8",
            )
            resolver = load_project_name_resolver(alias_path=alias_path, session_index_path=index_path)
            snapshot = build_snapshot(events, project_name_resolver=resolver).to_dict()

        project = snapshot["top_projects"][0]
        self.assertEqual(project["project"], "/tmp/project")
        self.assertEqual(project["display_name"], "Custom Research Name")
        self.assertEqual(project["display_name_source"], "alias")
        self.assertEqual(project["thread_names"], ["Synced Chat Name"])
        token_point = snapshot["token_timeline_points"][-1]
        self.assertEqual(token_point["cwd"], "/tmp/project")
        self.assertEqual(token_point["display_name"], "Custom Research Name")
        self.assertEqual(token_point["display_name_source"], "alias")
        self.assertEqual(token_point["thread_name"], "Synced Chat Name")
        self.assertEqual(token_point["token_used_total"], 120)

    def test_menu_shows_primary_remaining_not_used(self):
        event = {
            "event_id": "test",
            "timestamp": "2026-06-04T00:01:00+00:00",
            "source_file": "/tmp/test.jsonl",
            "session_id": "session-a",
            "cwd": "/tmp/project",
            "originator": "Codex Desktop",
            "total_usage": {"total_tokens": 120, "output_tokens": 20, "reasoning_output_tokens": 5},
            "last_usage": {"total_tokens": 30},
            "model_context_window": 1000,
            "primary": {"used_percent": 80, "window_minutes": 300, "resets_at": 1780569473},
            "secondary": {"used_percent": 20, "window_minutes": 10080, "resets_at": 1781138233},
            "plan_type": "pro",
            "limit_id": "codex",
            "rate_limit_reached_type": None,
        }
        args = type("Args", (), {"db": None, "menu_limit": 500, "dashboard_url": "http://127.0.0.1:8766/"})()
        buffer = StringIO()
        with patch("codex_usage_monitor.cli.load_recent_events_from_db", return_value=[]):
            with redirect_stdout(buffer):
                command_menu(args)
        self.assertIn("Codex --", buffer.getvalue())

        with patch("codex_usage_monitor.cli.load_recent_events_from_db") as load, patch(
            "codex_usage_monitor.cli.load_all_time_total_token_usage_from_db", return_value=987654
        ):
            load.return_value = list(parse_token_count_events_from_dicts([event]))
            buffer = StringIO()
            with redirect_stdout(buffer):
                command_menu(args)
        output = buffer.getvalue()
        self.assertIn("Codex 20% left | color=#7C5CFF", output)
        self.assertIn("5h reset:", output)
        self.assertIn("Weekly left: 80.00%", output)
        self.assertIn("Total Token Usage: 987.7k", output)
        self.assertNotIn("Tokens:", output)
        self.assertNotIn("Output:", output)
        self.assertNotIn("Reasoning:", output)
        self.assertNotIn("5h window: 80% used", output)

    def test_all_time_total_token_usage_uses_latest_per_session(self):
        events = [
            {
                "event_id": "s1-old",
                "timestamp": "2026-06-04T00:01:00+00:00",
                "source_file": "/tmp/test.jsonl",
                "session_id": "session-a",
                "cwd": "/tmp/project-a",
                "originator": "Codex Desktop",
                "total_usage": {"total_tokens": 100, "output_tokens": 20, "reasoning_output_tokens": 5},
                "last_usage": {"total_tokens": 30},
                "model_context_window": 1000,
                "primary": {"used_percent": 20, "window_minutes": 300, "resets_at": 1780569473},
                "secondary": {"used_percent": 20, "window_minutes": 10080, "resets_at": 1781138233},
                "plan_type": "pro",
                "limit_id": "codex",
                "rate_limit_reached_type": None,
            },
            {
                "event_id": "s1-new",
                "timestamp": "2026-06-04T00:02:00+00:00",
                "source_file": "/tmp/test.jsonl",
                "session_id": "session-a",
                "cwd": "/tmp/project-a",
                "originator": "Codex Desktop",
                "total_usage": {"total_tokens": 250, "output_tokens": 40, "reasoning_output_tokens": 10},
                "last_usage": {"total_tokens": 50},
                "model_context_window": 1000,
                "primary": {"used_percent": 30, "window_minutes": 300, "resets_at": 1780569473},
                "secondary": {"used_percent": 25, "window_minutes": 10080, "resets_at": 1781138233},
                "plan_type": "pro",
                "limit_id": "codex",
                "rate_limit_reached_type": None,
            },
            {
                "event_id": "s2-only",
                "timestamp": "2026-06-04T00:03:00+00:00",
                "source_file": "/tmp/test.jsonl",
                "session_id": "session-b",
                "cwd": "/tmp/project-b",
                "originator": "Codex Desktop",
                "total_usage": {"total_tokens": 400, "output_tokens": 80, "reasoning_output_tokens": 20},
                "last_usage": {"total_tokens": 60},
                "model_context_window": 1000,
                "primary": {"used_percent": 35, "window_minutes": 300, "resets_at": 1780569473},
                "secondary": {"used_percent": 25, "window_minutes": 10080, "resets_at": 1781138233},
                "plan_type": "pro",
                "limit_id": "codex",
                "rate_limit_reached_type": None,
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "usage.sqlite"
            with connect(db_path) as conn:
                upsert_events(conn, list(parse_token_count_events_from_dicts(events)))
            self.assertEqual(load_all_time_total_token_usage_from_db(db_path), 650)

    def test_dashboard_snapshot_reads_cache_before_background_sync(self):
        event = {
            "event_id": "test-dashboard",
            "timestamp": "2026-06-04T00:01:00+00:00",
            "source_file": "/tmp/test.jsonl",
            "session_id": "session-a",
            "cwd": "/tmp/project",
            "originator": "Codex Desktop",
            "total_usage": {"total_tokens": 120, "output_tokens": 20, "reasoning_output_tokens": 5},
            "last_usage": {"total_tokens": 30},
            "model_context_window": 1000,
            "primary": {"used_percent": 40, "window_minutes": 300, "resets_at": 1780569473},
            "secondary": {"used_percent": 20, "window_minutes": 10080, "resets_at": 1781138233},
            "plan_type": "pro",
            "limit_id": "codex",
            "rate_limit_reached_type": None,
        }

        class FakeThread:
            started = False

            def __init__(self, *args, **kwargs):
                pass

            def start(self):
                FakeThread.started = True

        for key in cli.DASHBOARD_CACHE:
            cli.DASHBOARD_CACHE[key] = False if key == "sync_in_progress" else None

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "usage.sqlite"
            with patch("codex_usage_monitor.cli.load_events_from_db_readonly") as load, patch("codex_usage_monitor.cli.Thread", FakeThread):
                load.return_value = list(parse_token_count_events_from_dicts([event]))
                snapshot = load_dashboard_snapshot(Path("/tmp/codex-root"), db_path=db_path)

        self.assertEqual(snapshot["dashboard_cache"]["source"], "sqlite")
        self.assertIsNotNone(snapshot["dashboard_cache"]["data_read_at"])
        self.assertEqual(snapshot["dashboard_cache"]["latest_event_at"], "2026-06-04T00:01:00+00:00")
        self.assertEqual(snapshot["latest_event"]["primary"]["remaining_percent"], 60.0)
        self.assertIn("persisted_sample_count", snapshot["monitor_history"])
        self.assertTrue(FakeThread.started)

    def test_monitor_history_records_real_samples_and_backfill(self):
        event = {
            "event_id": "history-test",
            "timestamp": "2026-06-04T00:01:00+00:00",
            "source_file": "/tmp/test.jsonl",
            "session_id": "session-a",
            "cwd": "/tmp/project",
            "originator": "Codex Desktop",
            "total_usage": {"total_tokens": 120, "input_tokens": 100, "cached_input_tokens": 50, "output_tokens": 20, "reasoning_output_tokens": 5},
            "last_usage": {"total_tokens": 30},
            "model_context_window": 1000,
            "primary": {"used_percent": 40, "window_minutes": 300, "resets_at": 1780569473},
            "secondary": {"used_percent": 20, "window_minutes": 10080, "resets_at": 1781138233},
            "plan_type": "pro",
            "limit_id": "codex",
            "rate_limit_reached_type": None,
        }
        events = list(parse_token_count_events_from_dicts([event]))
        snapshot = build_test_snapshot(events)

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "usage.sqlite"
            with connect(db_path) as conn:
                upsert_events(conn, events)
                inserted = backfill_monitor_samples_from_events(conn)
                self.assertEqual(inserted, 1)
                self.assertTrue(record_monitor_sample(conn, snapshot, "swiftbar", min_interval_seconds=0))
                history = load_monitor_history_from_db(conn, days=3650)

        self.assertEqual(history["sample_count"], 2)
        self.assertEqual(history["persisted_sample_count"], 1)
        self.assertEqual(history["backfill_sample_count"], 1)
        self.assertEqual(history["sources"]["swiftbar"], 1)
        self.assertEqual(history["sources"]["codex_log_backfill"], 1)
        self.assertEqual(sum(item["samples"] for item in history["hourly"]), 2)
        self.assertGreaterEqual(len(history["daily"]), 1)
        self.assertGreaterEqual(len(history["weekly"]), 1)
        self.assertEqual(sum(row["samples"] for row in history["daily"]), 2)
        self.assertEqual(sum(row["samples"] for row in history["weekly"]), 2)
        self.assertEqual(sum(sum(item["samples"] for item in row["hourly"]) for row in history["daily"]), 2)
        self.assertEqual(sum(sum(item["samples"] for item in row["hourly"]) for row in history["weekly"]), 2)
        self.assertEqual(len(history["window_samples"]), 2)
        self.assertIn("primary_remaining_percent", history["window_samples"][-1])
        self.assertIn("secondary_remaining_percent", history["window_samples"][-1])

    def test_monitor_history_ignores_future_samples_and_keeps_recording(self):
        event = {
            "event_id": "future-history-test",
            "timestamp": "2026-06-04T00:01:00+00:00",
            "source_file": "/tmp/test.jsonl",
            "session_id": "session-a",
            "cwd": "/tmp/project",
            "originator": "Codex Desktop",
            "total_usage": {"total_tokens": 120, "input_tokens": 100, "cached_input_tokens": 50, "output_tokens": 20, "reasoning_output_tokens": 5},
            "last_usage": {"total_tokens": 30},
            "model_context_window": 1000,
            "primary": {"used_percent": 40, "window_minutes": 300, "resets_at": 1780569473},
            "secondary": {"used_percent": 20, "window_minutes": 10080, "resets_at": 1781138233},
            "plan_type": "pro",
            "limit_id": "codex",
            "rate_limit_reached_type": None,
        }
        snapshot = build_test_snapshot(list(parse_token_count_events_from_dicts([event])))

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "usage.sqlite"
            with connect(db_path) as conn:
                future_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
                conn.execute(
                    """
                    INSERT INTO monitor_samples(
                      sampled_at, source, latest_total_tokens_sum, summary_json
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (future_at, "dashboard_cached", 999, "{}"),
                )
                conn.commit()
                self.assertTrue(record_monitor_sample(conn, snapshot, "dashboard_cached", min_interval_seconds=60))
                history = load_monitor_history_from_db(conn, days=1)

        self.assertEqual(history["sample_count"], 1)
        self.assertEqual(history["sources"]["dashboard_cached"], 1)
        self.assertNotEqual(history["last_sample_at"], future_at)
        self.assertEqual(history["window_samples"][-1]["latest_total_tokens_sum"], 120)

    def test_monitor_history_aggregates_full_retention_even_with_small_limit(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "usage.sqlite"
            with connect(db_path) as conn:
                for index in range(6):
                    sampled_at = (now - timedelta(minutes=6 - index)).isoformat()
                    conn.execute(
                        """
                        INSERT INTO monitor_samples(
                          sampled_at, source, latest_total_tokens_sum, summary_json
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (sampled_at, "dashboard_cached", 100 + index, "{}"),
                    )
                conn.commit()
                history = load_monitor_history_from_db(conn, days=1, limit=3)

        self.assertEqual(history["sample_count"], 6)
        self.assertEqual(history["window_samples"][-1]["latest_total_tokens_sum"], 105)
        self.assertEqual(sum(item["samples"] for item in history["hourly"]), 6)

    def test_monitor_backfill_is_incremental(self):
        base = {
            "source_file": "/tmp/test.jsonl",
            "session_id": "session-a",
            "cwd": "/tmp/project",
            "originator": "Codex Desktop",
            "total_usage": {"total_tokens": 120, "input_tokens": 100, "cached_input_tokens": 50, "output_tokens": 20, "reasoning_output_tokens": 5},
            "last_usage": {"total_tokens": 30},
            "model_context_window": 1000,
            "primary": {"used_percent": 40, "window_minutes": 300, "resets_at": 1780569473},
            "secondary": {"used_percent": 20, "window_minutes": 10080, "resets_at": 1781138233},
            "plan_type": "pro",
            "limit_id": "codex",
            "rate_limit_reached_type": None,
        }

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "usage.sqlite"
            with connect(db_path) as conn:
                first = dict(base, event_id="backfill-a", timestamp="2026-06-04T00:01:00+00:00")
                upsert_events(conn, list(parse_token_count_events_from_dicts([first])))
                self.assertEqual(backfill_monitor_samples_from_events(conn), 1)
                self.assertEqual(backfill_monitor_samples_from_events(conn), 0)

                second = dict(base, event_id="backfill-b", timestamp="2026-06-04T00:02:00+00:00")
                upsert_events(conn, list(parse_token_count_events_from_dicts([second])))
                self.assertEqual(backfill_monitor_samples_from_events(conn), 1)

                history = load_monitor_history_from_db(conn, days=3650)

        self.assertEqual(history["sources"]["codex_log_backfill"], 2)

    def test_monitor_sample_records_once_per_source_minute_bucket(self):
        event = {
            "event_id": "bucket-test",
            "timestamp": "2026-06-04T00:01:00+00:00",
            "source_file": "/tmp/test.jsonl",
            "session_id": "session-a",
            "cwd": "/tmp/project",
            "originator": "Codex Desktop",
            "total_usage": {"total_tokens": 120, "input_tokens": 100, "cached_input_tokens": 50, "output_tokens": 20, "reasoning_output_tokens": 5},
            "last_usage": {"total_tokens": 30},
            "model_context_window": 1000,
            "primary": {"used_percent": 40, "window_minutes": 300, "resets_at": 1780569473},
            "secondary": {"used_percent": 20, "window_minutes": 10080, "resets_at": 1781138233},
            "plan_type": "pro",
            "limit_id": "codex",
            "rate_limit_reached_type": None,
        }
        snapshot = build_test_snapshot(list(parse_token_count_events_from_dicts([event])))

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "usage.sqlite"
            with connect(db_path) as conn:
                self.assertTrue(record_monitor_sample(conn, snapshot, "dashboard_cached", min_interval_seconds=60))
                self.assertFalse(record_monitor_sample(conn, snapshot, "dashboard_cached", min_interval_seconds=60))
                history = load_monitor_history_from_db(conn, days=1)

        self.assertEqual(history["sources"]["dashboard_cached"], 1)

    def test_monitor_history_operational_error_returns_complete_empty_shape(self):
        class BrokenConnection:
            def execute(self, *args, **kwargs):
                raise sqlite3.OperationalError("database is locked")

        history = load_monitor_history_from_db(BrokenConnection(), days=3)

        self.assertEqual(history["sample_count"], 0)
        self.assertEqual(history["retention_days"], 3)
        self.assertEqual(history["recent"], [])
        self.assertEqual(history["window_samples"], [])

    def test_realtime_and_average_burn_rates(self):
        base = {
            "source_file": "/tmp/test.jsonl",
            "session_id": "session-a",
            "cwd": "/tmp/project",
            "originator": "Codex Desktop",
            "total_usage": {"total_tokens": 120, "output_tokens": 20, "reasoning_output_tokens": 5},
            "last_usage": {"total_tokens": 30},
            "model_context_window": 1000,
            "secondary": {"used_percent": 20, "window_minutes": 10080, "resets_at": 1781138233},
            "plan_type": "pro",
            "limit_id": "codex",
            "rate_limit_reached_type": None,
        }
        events = []
        for event_id, timestamp, used in [
            ("a", "2026-06-04T00:00:00+00:00", 10),
            ("b", "2026-06-04T00:30:00+00:00", 30),
            ("c", "2026-06-04T01:00:00+00:00", 40),
        ]:
            item = dict(base)
            item.update(
                {
                    "event_id": event_id,
                    "timestamp": timestamp,
                    "primary": {"used_percent": used, "window_minutes": 300, "resets_at": 1780569473},
                }
            )
            events.append(item)

        snapshot = build_test_snapshot(list(parse_token_count_events_from_dicts(events)), average_burn_minutes=60)
        self.assertAlmostEqual(snapshot["realtime_burn_rate_primary_percent_per_hour"], 20.0)
        self.assertAlmostEqual(snapshot["average_burn_rate_primary_percent_per_hour"], 30.0)
        self.assertEqual(snapshot["average_burn_rate_interval_minutes"], 60)
        self.assertTrue(all("token_used_total" in point for point in snapshot["trend_points"]))
        self.assertEqual(snapshot["trend_points"][-1]["token_used_total"], 120)
        self.assertTrue(all("display_name" in point for point in snapshot["token_timeline_points"]))
        self.assertEqual(snapshot["token_timeline_points"][-1]["display_name_source"], "path")
        self.assertEqual(snapshot["token_timeline_points"][-1]["token_used_total"], 120)
        windows = {item["key"]: item for item in snapshot["burn_rate_windows"]}
        self.assertEqual(set(windows), {"1h", "5h", "10h", "1d", "1w"})
        self.assertAlmostEqual(windows["1h"]["percent_per_hour"], 30.0)
        self.assertAlmostEqual(windows["5h"]["percent_per_hour"], 30.0)
        self.assertAlmostEqual(windows["5h"]["coverage_percent"], 20.0)
        self.assertEqual(snapshot["top_projects"][0]["recent_token_delta"], 0)
        self.assertEqual(snapshot["top_projects"][0]["token_burn_rate_per_hour"], 0.0)

        buffer = StringIO()
        with patch("codex_usage_monitor.cli.load_snapshot", return_value=snapshot):
            with redirect_stdout(buffer):
                cli.command_now(type("Args", (), {})())
        output = buffer.getvalue()
        self.assertIn("1h average burn rate: 30.00% / hour", output)
        self.assertIn("Custom average burn rate: 30.00% / hour over 60 minutes", output)
        self.assertNotIn("Realtime burn rate", output)

    def test_burn_rate_windows_ignore_stale_duplicate_limit_samples(self):
        base = {
            "source_file": "/tmp/test.jsonl",
            "session_id": "session-a",
            "cwd": "/tmp/project",
            "originator": "Codex Desktop",
            "total_usage": {"total_tokens": 120, "output_tokens": 20, "reasoning_output_tokens": 5},
            "last_usage": {"total_tokens": 30},
            "model_context_window": 1000,
            "secondary": {"used_percent": 20, "window_minutes": 10080, "resets_at": 1781138233},
            "plan_type": "pro",
            "limit_id": "codex",
            "rate_limit_reached_type": None,
        }
        events = []
        for event_id, timestamp, used in [
            ("a", "2026-06-04T00:00:00+00:00", 10),
            ("b", "2026-06-04T00:10:00+00:00", 20),
            ("stale", "2026-06-04T00:20:00+00:00", 15),
            ("c", "2026-06-04T00:30:00+00:00", 25),
            ("duplicate", "2026-06-04T00:40:00+00:00", 25),
            ("d", "2026-06-04T01:00:00+00:00", 30),
        ]:
            item = dict(base)
            item.update(
                {
                    "event_id": event_id,
                    "timestamp": timestamp,
                    "primary": {"used_percent": used, "window_minutes": 300, "resets_at": 1780569473},
                }
            )
            events.append(item)

        snapshot = build_test_snapshot(list(parse_token_count_events_from_dicts(events)), average_burn_minutes=60)
        windows = {item["key"]: item for item in snapshot["burn_rate_windows"]}
        self.assertAlmostEqual(windows["1h"]["percent_per_hour"], 20.0)
        self.assertAlmostEqual(windows["1h"]["percent_delta"], 20.0)


class RuntimeBoundaryTest(unittest.TestCase):
    def test_runtime_sources_do_not_call_model_apis(self):
        project = Path(__file__).resolve().parents[1]
        roots = [
            project / "codex_usage_monitor",
            project / "static",
            project / "menubar",
        ]
        root_files = [
            project / "codex-usage",
            project / "start-dashboard.sh",
            project / "start-dashboard-lan.sh",
            project / "stop-dashboard.sh",
            project / "install-menubar.sh",
            project / "quit-monitor-app.sh",
            project / "quit-swiftbar.sh",
            project / "resume-background-monitor.sh",
        ]
        files = []
        for root in roots:
            files.extend(path for path in root.rglob("*") if path.suffix in {".py", ".js", ".sh", ".swift"})
        files.extend(path for path in root_files if path.exists())

        forbidden_patterns = [
            r"api\.openai\.com",
            r"\bOPENAI_API_KEY\b",
            r"\bfrom\s+openai\b",
            r"\bimport\s+openai\b",
            r"\bopenai\.",
            r"\bChatCompletion\b",
            r"\bresponses\.create\b",
            r"\bclient\.responses\b",
            r"(^|\n)\s*(import\s+requests|from\s+requests\b)",
            r"\brequests\.(get|post|put|delete|patch|request|Session)\b",
            r"\bhttpx\.",
            r"\burllib\.request\b",
            r"\bcurl\b.*\bopenai\b",
            r"\bcodex\s+(exec|run|login|logout)\b",
        ]
        violations = []
        for path in files:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in forbidden_patterns:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    violations.append(f"{path.relative_to(project)} matches {pattern}")
        self.assertEqual([], violations)


def parse_token_count_events_from_dicts(events):
    from codex_usage_monitor.models import TokenCountEvent

    for event in events:
        yield TokenCountEvent.from_dict(event)


if __name__ == "__main__":
    unittest.main()
