from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def parse_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def unix_to_iso(value: Optional[int]) -> Optional[str]:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenUsage":
        return cls(
            input_tokens=int(data.get("input_tokens") or 0),
            cached_input_tokens=int(data.get("cached_input_tokens") or 0),
            output_tokens=int(data.get("output_tokens") or 0),
            reasoning_output_tokens=int(data.get("reasoning_output_tokens") or 0),
            total_tokens=int(data.get("total_tokens") or 0),
        )

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class LimitWindow:
    used_percent: Optional[float] = None
    window_minutes: Optional[int] = None
    resets_at: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "LimitWindow":
        data = data or {}
        used = data.get("used_percent")
        minutes = data.get("window_minutes")
        reset = data.get("resets_at")
        return cls(
            used_percent=float(used) if used is not None else None,
            window_minutes=int(minutes) if minutes is not None else None,
            resets_at=int(reset) if reset is not None else None,
        )

    def remaining_percent(self) -> Optional[float]:
        if self.used_percent is None:
            return None
        return max(0.0, 100.0 - self.used_percent)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["remaining_percent"] = self.remaining_percent()
        data["resets_at_iso"] = unix_to_iso(self.resets_at)
        return data


@dataclass(frozen=True)
class TokenCountEvent:
    event_id: str
    timestamp: datetime
    source_file: str
    session_id: str
    cwd: str
    originator: str
    total_usage: TokenUsage
    last_usage: TokenUsage
    model_context_window: Optional[int]
    primary: LimitWindow
    secondary: LimitWindow
    plan_type: Optional[str]
    limit_id: Optional[str]
    rate_limit_reached_type: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenCountEvent":
        return cls(
            event_id=data["event_id"],
            timestamp=parse_timestamp(data["timestamp"]),
            source_file=data["source_file"],
            session_id=data["session_id"],
            cwd=data.get("cwd") or "",
            originator=data.get("originator") or "",
            total_usage=TokenUsage.from_dict(data.get("total_usage") or {}),
            last_usage=TokenUsage.from_dict(data.get("last_usage") or {}),
            model_context_window=data.get("model_context_window"),
            primary=LimitWindow.from_dict(data.get("primary")),
            secondary=LimitWindow.from_dict(data.get("secondary")),
            plan_type=data.get("plan_type"),
            limit_id=data.get("limit_id"),
            rate_limit_reached_type=data.get("rate_limit_reached_type"),
        )

    @property
    def context_used_percent(self) -> Optional[float]:
        if not self.model_context_window:
            return None
        # total_usage is cumulative for the session and can exceed the active
        # context window. last_usage is the safest local proxy for turn pressure.
        return min(100.0, (self.last_usage.total_tokens / self.model_context_window) * 100.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source_file": self.source_file,
            "session_id": self.session_id,
            "cwd": self.cwd,
            "originator": self.originator,
            "total_usage": self.total_usage.to_dict(),
            "last_usage": self.last_usage.to_dict(),
            "model_context_window": self.model_context_window,
            "context_used_percent": self.context_used_percent,
            "primary": self.primary.to_dict(),
            "secondary": self.secondary.to_dict(),
            "plan_type": self.plan_type,
            "limit_id": self.limit_id,
            "rate_limit_reached_type": self.rate_limit_reached_type,
        }


@dataclass(frozen=True)
class SessionSummary:
    session_id: str
    cwd: str
    originator: str
    start_time: Optional[datetime]
    last_update: datetime
    latest_total_tokens: int
    latest_upload_tokens: int
    latest_input_tokens: int
    latest_cached_input_tokens: int
    latest_output_tokens: int
    latest_reasoning_tokens: int
    latest_contextual_tokens: int
    event_count: int
    active: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "cwd": self.cwd,
            "originator": self.originator,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_update": self.last_update.isoformat(),
            "latest_total_tokens": self.latest_total_tokens,
            "latest_upload_tokens": self.latest_upload_tokens,
            "latest_input_tokens": self.latest_input_tokens,
            "latest_cached_input_tokens": self.latest_cached_input_tokens,
            "latest_output_tokens": self.latest_output_tokens,
            "latest_reasoning_tokens": self.latest_reasoning_tokens,
            "latest_contextual_tokens": self.latest_contextual_tokens,
            "event_count": self.event_count,
            "active": self.active,
        }


@dataclass(frozen=True)
class Alert:
    severity: str
    name: str
    message: str
    value: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Snapshot:
    generated_at: datetime
    latest_event: Optional[TokenCountEvent]
    sessions: List[SessionSummary]
    alerts: List[Alert]
    burn_rate_primary_percent_per_hour: Optional[float]
    realtime_burn_rate_primary_percent_per_hour: Optional[float]
    average_burn_rate_primary_percent_per_hour: Optional[float]
    average_burn_rate_interval_minutes: int
    burn_rate_windows: List[Dict[str, Any]]
    trend_points: List[Dict[str, Any]]
    token_timeline_points: List[Dict[str, Any]]
    daily: List[Dict[str, Any]]
    top_projects: List[Dict[str, Any]]
    period_comparisons: Dict[str, Any]
    behavior_patterns: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    totals: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "latest_event": self.latest_event.to_dict() if self.latest_event else None,
            "sessions": [session.to_dict() for session in self.sessions],
            "alerts": [alert.to_dict() for alert in self.alerts],
            "burn_rate_primary_percent_per_hour": self.burn_rate_primary_percent_per_hour,
            "realtime_burn_rate_primary_percent_per_hour": self.realtime_burn_rate_primary_percent_per_hour,
            "average_burn_rate_primary_percent_per_hour": self.average_burn_rate_primary_percent_per_hour,
            "average_burn_rate_interval_minutes": self.average_burn_rate_interval_minutes,
            "burn_rate_windows": self.burn_rate_windows,
            "trend_points": self.trend_points,
            "token_timeline_points": self.token_timeline_points,
            "daily": self.daily,
            "top_projects": self.top_projects,
            "period_comparisons": self.period_comparisons,
            "behavior_patterns": self.behavior_patterns,
            "recommendations": self.recommendations,
            "totals": self.totals,
        }
