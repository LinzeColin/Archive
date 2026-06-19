from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional, Tuple

from .models import LimitWindow, TokenCountEvent, TokenUsage, parse_timestamp


DEFAULT_CODEX_ROOT = Path.home() / ".codex"


def iter_log_files(codex_root: Path = DEFAULT_CODEX_ROOT, include_archived: bool = True) -> Iterator[Path]:
    sessions = codex_root / "sessions"
    if sessions.exists():
        yield from sorted(sessions.rglob("*.jsonl"))
    if include_archived:
        archived = codex_root / "archived_sessions"
        if archived.exists():
            yield from sorted(archived.glob("*.jsonl"))


def _event_id(path: Path, line_no: int, raw_line: str) -> str:
    digest = hashlib.sha1(f"{path}:{line_no}:{raw_line}".encode("utf-8", "ignore")).hexdigest()
    return digest[:20]


def _session_id_from_path(path: Path) -> str:
    name = path.stem
    if "rollout-" in name:
        return name.replace("rollout-", "", 1)
    return name


def parse_token_count_events(path: Path) -> Iterator[TokenCountEvent]:
    session_id = _session_id_from_path(path)
    cwd = ""
    originator = ""

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            raw_line = raw_line.rstrip("\n")
            if not raw_line:
                continue
            try:
                item = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            item_type = item.get("type")
            payload = item.get("payload") or {}

            if item_type == "session_meta":
                session_id = payload.get("id") or session_id
                cwd = payload.get("cwd") or cwd
                originator = payload.get("originator") or originator
                continue

            if item_type != "event_msg" or payload.get("type") != "token_count":
                continue

            info = payload.get("info") or {}
            rate_limits = payload.get("rate_limits") or {}
            total_usage = TokenUsage.from_dict(info.get("total_token_usage") or {})
            last_usage = TokenUsage.from_dict(info.get("last_token_usage") or {})
            context_window = info.get("model_context_window")
            timestamp = parse_timestamp(item["timestamp"])

            yield TokenCountEvent(
                event_id=_event_id(path, line_no, raw_line),
                timestamp=timestamp,
                source_file=str(path),
                session_id=session_id,
                cwd=cwd,
                originator=originator,
                total_usage=total_usage,
                last_usage=last_usage,
                model_context_window=int(context_window) if context_window is not None else None,
                primary=LimitWindow.from_dict(rate_limits.get("primary")),
                secondary=LimitWindow.from_dict(rate_limits.get("secondary")),
                plan_type=rate_limits.get("plan_type"),
                limit_id=rate_limits.get("limit_id"),
                rate_limit_reached_type=rate_limits.get("rate_limit_reached_type"),
            )


def load_events(codex_root: Path = DEFAULT_CODEX_ROOT, include_archived: bool = True) -> Tuple[TokenCountEvent, ...]:
    seen = set()
    events = []
    for path in iter_log_files(codex_root, include_archived=include_archived):
        for event in parse_token_count_events(path):
            if event.event_id in seen:
                continue
            seen.add(event.event_id)
            events.append(event)
    events.sort(key=lambda event: event.timestamp)
    return tuple(events)


def latest_event(codex_root: Path = DEFAULT_CODEX_ROOT) -> Optional[TokenCountEvent]:
    events = load_events(codex_root, include_archived=False)
    return events[-1] if events else None
