from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional

from .models import Alert, SessionSummary, Snapshot, TokenCountEvent
from .project_names import ProjectNameResolver, load_project_name_resolver

BURN_RATE_WINDOWS = [
    ("1h", "1h", 60),
    ("5h", "5h", 300),
    ("10h", "10h", 600),
    ("1d", "1d", 1440),
    ("1w", "1w", 10080),
]


def build_snapshot(
    events: Iterable[TokenCountEvent],
    active_minutes: int = 20,
    average_burn_minutes: int = 60,
    project_name_resolver: ProjectNameResolver | None = None,
) -> Snapshot:
    ordered = sorted(events, key=lambda event: event.timestamp)
    now = datetime.now(timezone.utc)
    average_burn_minutes = max(1, int(average_burn_minutes or 60))
    project_name_resolver = project_name_resolver or load_project_name_resolver()
    latest = _representative_latest(ordered)
    sessions = _session_summaries(ordered, now=now, active_minutes=active_minutes)
    alerts = _alerts(latest)
    trend_points = _trend_points(ordered)
    token_timeline_points = _token_timeline_points(ordered, project_name_resolver)
    daily = _daily_summary(ordered)
    realtime_burn_rate = _realtime_burn_rate_primary(ordered)
    average_burn_rate = _average_burn_rate_primary(ordered, average_burn_minutes)
    burn_rate_windows = _burn_rate_windows(ordered)
    top_projects = _top_projects(ordered, sessions, average_burn_minutes, project_name_resolver)
    period_comparisons = _period_comparisons(daily)
    behavior_patterns = _behavior_patterns(ordered, sessions, top_projects)
    recommendations = _recommendations(latest, period_comparisons, behavior_patterns, average_burn_rate, sessions)
    totals = _totals(ordered, sessions)
    return Snapshot(
        generated_at=now,
        latest_event=latest,
        sessions=sessions,
        alerts=alerts,
        burn_rate_primary_percent_per_hour=average_burn_rate,
        realtime_burn_rate_primary_percent_per_hour=realtime_burn_rate,
        average_burn_rate_primary_percent_per_hour=average_burn_rate,
        average_burn_rate_interval_minutes=average_burn_minutes,
        burn_rate_windows=burn_rate_windows,
        trend_points=trend_points,
        token_timeline_points=token_timeline_points,
        daily=daily,
        top_projects=top_projects,
        period_comparisons=period_comparisons,
        behavior_patterns=behavior_patterns,
        recommendations=recommendations,
        totals=totals,
    )


def _representative_latest(events: List[TokenCountEvent]) -> Optional[TokenCountEvent]:
    if not events:
        return None
    newest = events[-1]
    cutoff = newest.timestamp - timedelta(minutes=10)
    recent = [event for event in events if event.timestamp >= cutoff]
    primary_reset = max((event.primary.resets_at or 0 for event in recent), default=0)
    if primary_reset:
        recent = [event for event in recent if (event.primary.resets_at or 0) == primary_reset]
    recent.sort(
        key=lambda event: (
            float(event.primary.used_percent or -1),
            float(event.secondary.used_percent or -1),
            event.timestamp,
        ),
        reverse=True,
    )
    return recent[0] if recent else newest


def _session_summaries(events: List[TokenCountEvent], now: datetime, active_minutes: int) -> List[SessionSummary]:
    grouped: Dict[str, List[TokenCountEvent]] = defaultdict(list)
    for event in events:
        grouped[event.session_id].append(event)

    summaries = []
    active_cutoff = now - timedelta(minutes=active_minutes)
    for session_id, items in grouped.items():
        items.sort(key=lambda event: event.timestamp)
        latest = items[-1]
        latest_upload_tokens = _upload_tokens(latest.total_usage.input_tokens, latest.total_usage.cached_input_tokens)
        latest_contextual_tokens = _contextual_tokens(latest.total_usage.cached_input_tokens)
        summaries.append(
            SessionSummary(
                session_id=session_id,
                cwd=latest.cwd,
                originator=latest.originator,
                start_time=items[0].timestamp if items else None,
                last_update=latest.timestamp,
                latest_total_tokens=latest.total_usage.total_tokens,
                latest_upload_tokens=latest_upload_tokens,
                latest_input_tokens=latest.total_usage.input_tokens,
                latest_cached_input_tokens=latest.total_usage.cached_input_tokens,
                latest_output_tokens=latest.total_usage.output_tokens,
                latest_reasoning_tokens=latest.total_usage.reasoning_output_tokens,
                latest_contextual_tokens=latest_contextual_tokens,
                event_count=len(items),
                active=latest.timestamp >= active_cutoff,
            )
        )
    summaries.sort(key=lambda item: item.last_update, reverse=True)
    return summaries


def _alerts(latest: Optional[TokenCountEvent]) -> List[Alert]:
    if latest is None:
        return [Alert("critical", "no_data", "No Codex token_count events found.", None)]

    alerts: List[Alert] = []
    checks = [
        ("primary", "5-hour window", latest.primary.used_percent),
        ("secondary", "weekly window", latest.secondary.used_percent),
        ("context", "last turn context pressure", latest.context_used_percent),
    ]
    for name, label, value in checks:
        if value is None:
            continue
        if value >= 95:
            alerts.append(Alert("critical", name, f"{label} is at {value:.1f}%.", value))
        elif value >= 85:
            alerts.append(Alert("warning", name, f"{label} is at {value:.1f}%.", value))
        elif value >= 70:
            alerts.append(Alert("notice", name, f"{label} is at {value:.1f}%.", value))

    if latest.rate_limit_reached_type:
        alerts.append(
            Alert(
                "critical",
                "rate_limit_reached",
                f"Rate limit reached: {latest.rate_limit_reached_type}.",
                None,
            )
        )
    return alerts


def _trend_points(events: List[TokenCountEvent]) -> List[Dict[str, object]]:
    if not events:
        return []
    cutoff = events[-1].timestamp - timedelta(hours=24)
    points = []
    latest_total_by_session: Dict[str, int] = {}
    for event in events:
        latest_total_by_session[event.session_id] = event.total_usage.total_tokens
        if event.timestamp < cutoff:
            continue
        points.append(
            {
                "timestamp": event.timestamp.isoformat(),
                "primary_used_percent": event.primary.used_percent,
                "secondary_used_percent": event.secondary.used_percent,
                "total_tokens": event.total_usage.total_tokens,
                "token_used_total": sum(latest_total_by_session.values()),
                "session_id": event.session_id,
            }
        )
    return points[-500:]


def _display_name_for_event(
    event: TokenCountEvent,
    project_name_resolver: ProjectNameResolver,
) -> Dict[str, object]:
    project = event.cwd or "(unknown)"
    alias = project_name_resolver.alias_for(project)
    thread_name = project_name_resolver.thread_name_for(event.session_id)
    if alias:
        display_name = alias
        source = "alias"
    elif thread_name:
        display_name = thread_name
        source = "thread_index"
    else:
        display_name = project
        source = "path"
    return {
        "project": project,
        "display_name": display_name,
        "display_name_source": source,
        "thread_name": thread_name,
    }


def _token_timeline_points(
    events: List[TokenCountEvent],
    project_name_resolver: ProjectNameResolver,
) -> List[Dict[str, object]]:
    if not events:
        return []
    latest_total_by_session: Dict[str, int] = {}
    points = []
    for event in events:
        latest_total_by_session[event.session_id] = event.total_usage.total_tokens
        name = _display_name_for_event(event, project_name_resolver)
        points.append(
            {
                "timestamp": event.timestamp.isoformat(),
                "session_id": event.session_id,
                "cwd": event.cwd,
                "originator": event.originator,
                "project": name["project"],
                "display_name": name["display_name"],
                "display_name_source": name["display_name_source"],
                "thread_name": name["thread_name"],
                "total_tokens": event.total_usage.total_tokens,
                "upload_tokens": _upload_tokens(event.total_usage.input_tokens, event.total_usage.cached_input_tokens),
                "input_tokens": event.total_usage.input_tokens,
                "cached_input_tokens": event.total_usage.cached_input_tokens,
                "output_tokens": event.total_usage.output_tokens,
                "contextual_tokens": _contextual_tokens(event.total_usage.cached_input_tokens),
                "reasoning_tokens": event.total_usage.reasoning_output_tokens,
                "token_used_total": sum(latest_total_by_session.values()),
            }
        )
    return points[-5000:]


def _daily_summary(events: List[TokenCountEvent]) -> List[Dict[str, object]]:
    grouped: Dict[str, List[TokenCountEvent]] = defaultdict(list)
    for event in events:
        grouped[event.timestamp.date().isoformat()].append(event)

    rows = []
    for day, items in sorted(grouped.items()):
        latest_by_session: Dict[str, TokenCountEvent] = {}
        for event in sorted(items, key=lambda item: item.timestamp):
            latest_by_session[event.session_id] = event
        total_tokens = sum(event.total_usage.total_tokens for event in latest_by_session.values())
        upload_tokens = sum(_upload_tokens(event.total_usage.input_tokens, event.total_usage.cached_input_tokens) for event in latest_by_session.values())
        input_tokens = sum(event.total_usage.input_tokens for event in latest_by_session.values())
        cached_input_tokens = sum(event.total_usage.cached_input_tokens for event in latest_by_session.values())
        output_tokens = sum(event.total_usage.output_tokens for event in latest_by_session.values())
        reasoning_tokens = sum(event.total_usage.reasoning_output_tokens for event in latest_by_session.values())
        contextual_tokens = sum(_contextual_tokens(event.total_usage.cached_input_tokens) for event in latest_by_session.values())
        rows.append(
            {
                "date": day,
                "sessions": len(latest_by_session),
                "agents": len(latest_by_session),
                "events": len(items),
                "latest_total_tokens_sum": total_tokens,
                "latest_upload_tokens_sum": upload_tokens,
                "latest_input_tokens_sum": input_tokens,
                "latest_cached_input_tokens_sum": cached_input_tokens,
                "latest_output_tokens_sum": output_tokens,
                "latest_reasoning_tokens_sum": reasoning_tokens,
                "latest_contextual_tokens_sum": contextual_tokens,
            }
        )
    return rows


def _top_projects(
    events: List[TokenCountEvent],
    sessions: List[SessionSummary],
    burn_interval_minutes: int,
    project_name_resolver: ProjectNameResolver,
) -> List[Dict[str, object]]:
    grouped: Dict[str, Dict[str, object]] = {}
    latest_session_by_project: Dict[str, SessionSummary] = {}
    project_burn = _project_token_burn_rates(events, burn_interval_minutes)
    for session in sessions:
        project = session.cwd or "(unknown)"
        if project not in latest_session_by_project or session.last_update > latest_session_by_project[project].last_update:
            latest_session_by_project[project] = session
        if project not in grouped:
            grouped[project] = {
                "project": project,
                "display_name": project,
                "display_name_source": "path",
                "thread_names": [],
                "threads": 0,
                "working_threads": 0,
                "agents": 0,
                "working_agents": 0,
                "sessions": 0,
                "active_sessions": 0,
                "events": 0,
                "latest_total_tokens_sum": 0,
                "latest_upload_tokens_sum": 0,
                "latest_input_tokens_sum": 0,
                "latest_cached_input_tokens_sum": 0,
                "latest_output_tokens_sum": 0,
                "latest_contextual_tokens_sum": 0,
                "latest_reasoning_tokens_sum": 0,
                "last_update": session.last_update.isoformat(),
            }
        row = grouped[project]
        row["threads"] = int(row["threads"]) + 1
        row["working_threads"] = int(row["working_threads"]) + int(session.active)
        row["agents"] = int(row["agents"]) + 1
        row["working_agents"] = int(row["working_agents"]) + int(session.active)
        row["sessions"] = int(row["threads"])
        row["active_sessions"] = int(row["working_threads"])
        row["events"] = int(row["events"]) + session.event_count
        row["latest_total_tokens_sum"] = int(row["latest_total_tokens_sum"]) + session.latest_total_tokens
        row["latest_upload_tokens_sum"] = int(row["latest_upload_tokens_sum"]) + session.latest_upload_tokens
        row["latest_input_tokens_sum"] = int(row["latest_input_tokens_sum"]) + session.latest_input_tokens
        row["latest_cached_input_tokens_sum"] = int(row["latest_cached_input_tokens_sum"]) + session.latest_cached_input_tokens
        row["latest_output_tokens_sum"] = int(row["latest_output_tokens_sum"]) + session.latest_output_tokens
        row["latest_contextual_tokens_sum"] = int(row["latest_contextual_tokens_sum"]) + session.latest_contextual_tokens
        row["latest_reasoning_tokens_sum"] = int(row["latest_reasoning_tokens_sum"]) + session.latest_reasoning_tokens
        thread_name = project_name_resolver.thread_name_for(session.session_id)
        if thread_name and thread_name not in row["thread_names"]:
            row["thread_names"].append(thread_name)
        if session.last_update.isoformat() > str(row["last_update"]):
            row["last_update"] = session.last_update.isoformat()
    rows = list(grouped.values())
    for row in rows:
        project = str(row.get("project") or "")
        alias = project_name_resolver.alias_for(project)
        latest_session = latest_session_by_project.get(project)
        latest_thread_name = project_name_resolver.thread_name_for(latest_session.session_id) if latest_session else None
        if alias:
            row["display_name"] = alias
            row["display_name_source"] = "alias"
        elif latest_thread_name:
            row["display_name"] = latest_thread_name
            row["display_name_source"] = "thread_index"
        else:
            row["display_name"] = project
            row["display_name_source"] = "path"
        row["thread_names"] = list(row.get("thread_names") or [])[:8]
        burn = project_burn.get(project, {})
        row["token_burn_rate_per_hour"] = burn.get("token_burn_rate_per_hour", 0.0)
        row["recent_token_delta"] = burn.get("recent_token_delta", 0)
        row["burn_interval_minutes"] = burn.get("burn_interval_minutes", burn_interval_minutes)
    rows.sort(key=lambda row: int(row["latest_total_tokens_sum"]), reverse=True)
    return rows[:12]


def _project_token_burn_rates(events: List[TokenCountEvent], interval_minutes: int) -> Dict[str, Dict[str, object]]:
    if not events:
        return {}
    interval_minutes = max(1, int(interval_minutes or 60))
    end = events[-1].timestamp
    cutoff = end - timedelta(minutes=interval_minutes)
    grouped: Dict[str, Dict[str, List[TokenCountEvent]]] = defaultdict(lambda: defaultdict(list))
    for event in events:
        grouped[event.cwd or "(unknown)"][event.session_id].append(event)

    rows: Dict[str, Dict[str, object]] = {}
    interval_hours = interval_minutes / 60.0
    for project, by_session in grouped.items():
        token_delta = 0
        for items in by_session.values():
            items.sort(key=lambda item: item.timestamp)
            previous = None
            for item in items:
                if item.timestamp < cutoff:
                    previous = item
                    continue
                if previous is not None:
                    token_delta += max(0, item.total_usage.total_tokens - previous.total_usage.total_tokens)
                previous = item
        rows[project] = {
            "recent_token_delta": token_delta,
            "token_burn_rate_per_hour": token_delta / interval_hours if interval_hours else 0.0,
            "burn_interval_minutes": interval_minutes,
        }
    return rows


def _delta(current: float, previous: float) -> Dict[str, object]:
    absolute = current - previous
    if previous == 0:
        percent = None if current == 0 else 100.0
    else:
        percent = (absolute / previous) * 100.0
    return {"current": current, "previous": previous, "absolute": absolute, "percent": percent}


def _sum_daily(rows: List[Dict[str, object]], key: str) -> float:
    return float(sum(float(row.get(key) or 0) for row in rows))


def _period_comparisons(daily: List[Dict[str, object]]) -> Dict[str, object]:
    today = daily[-1:] or []
    yesterday = daily[-2:-1] if len(daily) >= 2 else []
    last_7 = daily[-7:]
    previous_7 = daily[-14:-7] if len(daily) >= 8 else []
    return {
        "day_over_day": {
            "tokens": _delta(_sum_daily(today, "latest_total_tokens_sum"), _sum_daily(yesterday, "latest_total_tokens_sum")),
            "sessions": _delta(_sum_daily(today, "sessions"), _sum_daily(yesterday, "sessions")),
            "events": _delta(_sum_daily(today, "events"), _sum_daily(yesterday, "events")),
            "input": _delta(_sum_daily(today, "latest_upload_tokens_sum"), _sum_daily(yesterday, "latest_upload_tokens_sum")),
            "output": _delta(_sum_daily(today, "latest_output_tokens_sum"), _sum_daily(yesterday, "latest_output_tokens_sum")),
            "contextual": _delta(_sum_daily(today, "latest_contextual_tokens_sum"), _sum_daily(yesterday, "latest_contextual_tokens_sum")),
            "reasoning": _delta(_sum_daily(today, "latest_reasoning_tokens_sum"), _sum_daily(yesterday, "latest_reasoning_tokens_sum")),
        },
        "week_over_week": {
            "tokens": _delta(_sum_daily(last_7, "latest_total_tokens_sum"), _sum_daily(previous_7, "latest_total_tokens_sum")),
            "sessions": _delta(_sum_daily(last_7, "sessions"), _sum_daily(previous_7, "sessions")),
            "events": _delta(_sum_daily(last_7, "events"), _sum_daily(previous_7, "events")),
            "input": _delta(_sum_daily(last_7, "latest_upload_tokens_sum"), _sum_daily(previous_7, "latest_upload_tokens_sum")),
            "output": _delta(_sum_daily(last_7, "latest_output_tokens_sum"), _sum_daily(previous_7, "latest_output_tokens_sum")),
            "contextual": _delta(_sum_daily(last_7, "latest_contextual_tokens_sum"), _sum_daily(previous_7, "latest_contextual_tokens_sum")),
            "reasoning": _delta(_sum_daily(last_7, "latest_reasoning_tokens_sum"), _sum_daily(previous_7, "latest_reasoning_tokens_sum")),
        },
    }


def _upload_tokens(input_tokens: int, cached_input_tokens: int) -> int:
    return max(0, int(input_tokens or 0) - int(cached_input_tokens or 0))


def _contextual_tokens(cached_input_tokens: int) -> int:
    return max(0, int(cached_input_tokens or 0))


def _behavior_patterns(
    events: List[TokenCountEvent],
    sessions: List[SessionSummary],
    top_projects: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    if not events:
        return []
    hourly: Dict[int, int] = defaultdict(int)
    for event in events:
        hourly[event.timestamp.astimezone().hour] += 1
    peak_hour, peak_events = max(hourly.items(), key=lambda item: item[1])
    total_project_tokens = sum(int(project.get("latest_total_tokens_sum") or 0) for project in top_projects)
    top_project_share = 0.0
    if total_project_tokens and top_projects:
        top_project_share = int(top_projects[0].get("latest_total_tokens_sum") or 0) / total_project_tokens * 100.0
    active_sessions = sum(1 for session in sessions if session.active)
    latest = events[-1]
    total_tokens = latest.total_usage.total_tokens or 1
    input_ratio = _upload_tokens(latest.total_usage.input_tokens, latest.total_usage.cached_input_tokens) / total_tokens * 100.0
    output_ratio = latest.total_usage.output_tokens / total_tokens * 100.0
    contextual_ratio = _contextual_tokens(latest.total_usage.cached_input_tokens) / total_tokens * 100.0
    reasoning_ratio = latest.total_usage.reasoning_output_tokens / total_tokens * 100.0
    return [
        {
            "name": "Peak operating hour",
            "value": f"{peak_hour:02d}:00",
            "detail": f"{peak_events} token events recorded in this local hour.",
            "severity": "info",
        },
        {
            "name": "Concurrent active work",
            "value": str(active_sessions),
            "detail": "Sessions active in the last 20 minutes.",
            "severity": "warning" if active_sessions >= 5 else "info",
        },
        {
            "name": "Project concentration",
            "value": f"{top_project_share:.1f}%",
            "detail": "Share of latest token sum represented by the largest project.",
            "severity": "warning" if top_project_share >= 50 else "info",
        },
        {
            "name": "Token traffic mix",
            "value": f"{input_ratio:.2f}% / {output_ratio:.2f}% / {contextual_ratio:.2f}% / {reasoning_ratio:.2f}%",
            "detail": "Latest representative session upload, download, contextual and reasoning share of cumulative tokens.",
            "severity": "info",
        },
    ]


def _recommendations(
    latest: Optional[TokenCountEvent],
    period_comparisons: Dict[str, object],
    behavior_patterns: List[Dict[str, object]],
    burn_rate: Optional[float],
    sessions: List[SessionSummary],
) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []
    if latest is None:
        return [{"priority": "high", "title": "No Codex token data", "detail": "Confirm Codex is writing local token_count events."}]
    remaining = latest.primary.remaining_percent()
    if remaining is not None and remaining < 10:
        items.append({"priority": "high", "title": "Protect the 5h window", "detail": "Pause non-critical runs until reset or consolidate work into fewer, smaller prompts."})
    elif remaining is not None and remaining < 50:
        items.append({"priority": "medium", "title": "Watch short-window capacity", "detail": "Batch lower-priority tasks and avoid parallel long-running sessions before reset."})
    else:
        items.append({"priority": "low", "title": "5h capacity is healthy", "detail": "Current short-window allowance is sufficient; keep monitoring burn rate during parallel work."})

    dod = ((period_comparisons.get("day_over_day") or {}).get("tokens") or {})
    dod_percent = dod.get("percent")
    if dod_percent is not None and float(dod_percent) > 50:
        items.append({"priority": "medium", "title": "Daily usage spike", "detail": f"Token sum is up {float(dod_percent):.1f}% versus the previous day; review large sessions and repeated retries."})
    if burn_rate is not None and burn_rate > 20:
        items.append({"priority": "medium", "title": "High 5h burn rate", "detail": f"Current primary-window burn is {burn_rate:.2f}% per hour; reduce concurrent background work if you need quota later."})
    active_sessions = sum(1 for session in sessions if session.active)
    if active_sessions >= 5:
        items.append({"priority": "medium", "title": "Too many active sessions", "detail": f"{active_sessions} sessions are active; close or finish stale work to reduce quota noise."})
    for pattern in behavior_patterns:
        if pattern.get("name") == "Project concentration" and str(pattern.get("severity")) == "warning":
            items.append({"priority": "low", "title": "One project dominates usage", "detail": "Check whether this is expected sustained work or a runaway/retry-heavy task."})
    return items[:6]


def _totals(events: List[TokenCountEvent], sessions: List[SessionSummary]) -> Dict[str, object]:
    active_sessions = sum(1 for session in sessions if session.active)
    projects = {session.cwd or "(unknown)" for session in sessions}
    working_projects = {session.cwd or "(unknown)" for session in sessions if session.active}
    latest_by_session = {session.session_id: session for session in sessions}
    return {
        "token_count_events": len(events),
        "sessions": len(sessions),
        "active_sessions": active_sessions,
        "threads_activated": len(sessions),
        "threads_working": active_sessions,
        "agents_activated": len(sessions),
        "agents_working": active_sessions,
        "projects_activated": len(projects),
        "projects_working": len(working_projects),
        "latest_total_tokens_sum": sum(session.latest_total_tokens for session in latest_by_session.values()),
        "latest_upload_tokens_sum": sum(session.latest_upload_tokens for session in latest_by_session.values()),
        "latest_input_tokens_sum": sum(session.latest_input_tokens for session in latest_by_session.values()),
        "latest_cached_input_tokens_sum": sum(session.latest_cached_input_tokens for session in latest_by_session.values()),
        "latest_output_tokens_sum": sum(session.latest_output_tokens for session in latest_by_session.values()),
        "latest_reasoning_tokens_sum": sum(session.latest_reasoning_tokens for session in latest_by_session.values()),
        "latest_contextual_tokens_sum": sum(session.latest_contextual_tokens for session in latest_by_session.values()),
    }


def _primary_window_samples(events: List[TokenCountEvent]) -> List[TokenCountEvent]:
    samples = [event for event in events if event.primary.used_percent is not None]
    if not samples:
        return []
    end = samples[-1]
    return [
        event
        for event in samples
        if event.primary.resets_at == end.primary.resets_at
        and event.primary.used_percent is not None
        and event.primary.used_percent <= end.primary.used_percent
    ]


def _burn_rate_between(start: TokenCountEvent, end: TokenCountEvent) -> Optional[float]:
    hours = (end.timestamp - start.timestamp).total_seconds() / 3600.0
    if hours <= 0:
        return None
    delta = float(end.primary.used_percent or 0) - float(start.primary.used_percent or 0)
    if delta < 0:
        return None
    return delta / hours


def _realtime_burn_rate_primary(events: List[TokenCountEvent]) -> Optional[float]:
    samples = _primary_window_samples(events)
    if len(samples) < 2:
        return None
    end = samples[-1]
    for start in reversed(samples[:-1]):
        if start.timestamp < end.timestamp:
            return _burn_rate_between(start, end)
    return None


def _average_burn_rate_primary(events: List[TokenCountEvent], interval_minutes: int) -> Optional[float]:
    samples = _primary_window_samples(events)
    if len(samples) < 2:
        return None
    end = samples[-1]
    start_cutoff = end.timestamp - timedelta(minutes=max(1, int(interval_minutes)))
    window = [event for event in samples if event.timestamp >= start_cutoff]
    before_window = [event for event in samples if event.timestamp <= start_cutoff]
    if before_window:
        start = before_window[-1]
    elif window:
        start = window[0]
    else:
        return None
    if start.timestamp >= end.timestamp:
        return None
    return _burn_rate_between(start, end)


def _burn_rate_windows(events: List[TokenCountEvent]) -> List[Dict[str, object]]:
    raw_samples = [event for event in events if event.primary.used_percent is not None]
    samples = _canonical_primary_samples(raw_samples)
    if len(samples) < 2:
        return [
            {
                "key": key,
                "label": label,
                "minutes": minutes,
                "percent_per_hour": None,
                "percent_delta": None,
                "observed_minutes": 0,
                "sample_count": len(samples),
                "coverage_percent": 0.0,
            }
            for key, label, minutes in BURN_RATE_WINDOWS
        ]

    return [_burn_rate_window(samples, key, label, minutes) for key, label, minutes in BURN_RATE_WINDOWS]


def _canonical_primary_samples(samples: List[TokenCountEvent]) -> List[TokenCountEvent]:
    canonical: List[TokenCountEvent] = []
    current_reset = -1
    current_used = -1.0
    for event in sorted(samples, key=lambda item: item.timestamp):
        used = float(event.primary.used_percent or 0)
        reset = int(event.primary.resets_at or 0)
        if reset < current_reset:
            continue
        if reset > current_reset:
            canonical.append(event)
            current_reset = reset
            current_used = used
            continue
        if used > current_used:
            canonical.append(event)
            current_used = used
    return canonical


def _burn_rate_window(samples: List[TokenCountEvent], key: str, label: str, minutes: int) -> Dict[str, object]:
    end = samples[-1]
    cutoff = end.timestamp - timedelta(minutes=minutes)
    window = [event for event in samples if event.timestamp >= cutoff]
    previous = [event for event in samples if event.timestamp < cutoff]
    if previous:
        window.insert(0, previous[-1])

    if len(window) < 2:
        observed_minutes = 0
        sample_count = len(window)
        return {
            "key": key,
            "label": label,
            "minutes": minutes,
            "percent_per_hour": None,
            "percent_delta": None,
            "observed_minutes": observed_minutes,
            "sample_count": sample_count,
            "coverage_percent": 0.0,
        }

    delta = 0.0
    sample_count = 0
    for previous_event, current_event in zip(window, window[1:]):
        if current_event.timestamp <= cutoff:
            continue
        previous_used = float(previous_event.primary.used_percent or 0)
        current_used = float(current_event.primary.used_percent or 0)
        if current_event.primary.resets_at == previous_event.primary.resets_at:
            movement = current_used - previous_used
            if movement > 0:
                delta += movement
        else:
            cycle_start = _primary_cycle_start(current_event)
            if cycle_start is None or cycle_start >= cutoff:
                # New primary window: count observed consumption in the new reset cycle.
                delta += max(0.0, current_used)
        sample_count += 1

    observed_start = max(cutoff, window[0].timestamp)
    observed_minutes = max(0, int(round((end.timestamp - observed_start).total_seconds() / 60.0)))
    observed_hours = observed_minutes / 60.0
    percent_per_hour = delta / observed_hours if observed_hours > 0 and sample_count > 0 else None
    coverage_percent = min(100.0, observed_minutes * 100.0 / max(1, minutes))
    return {
        "key": key,
        "label": label,
        "minutes": minutes,
        "percent_per_hour": percent_per_hour,
        "percent_delta": delta,
        "observed_minutes": observed_minutes,
        "sample_count": sample_count,
        "coverage_percent": coverage_percent,
    }


def _primary_cycle_start(event: TokenCountEvent) -> Optional[datetime]:
    if not event.primary.resets_at or not event.primary.window_minutes:
        return None
    return datetime.fromtimestamp(
        int(event.primary.resets_at) - int(event.primary.window_minutes) * 60,
        tz=timezone.utc,
    )


def format_percent(value: Optional[float]) -> str:
    return "--" if value is None else f"{value:.1f}%"


def format_tokens(value: int) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)
