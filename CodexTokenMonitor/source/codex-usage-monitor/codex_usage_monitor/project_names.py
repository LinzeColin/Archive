from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_ALIAS_PATH = Path.home() / ".codex_usage_monitor" / "project_aliases.json"
DEFAULT_SESSION_INDEX_PATH = Path.home() / ".codex" / "session_index.jsonl"


def _parse_time(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def load_project_aliases(path: Path | None = None) -> Dict[str, str]:
    alias_path = path or DEFAULT_ALIAS_PATH
    if not alias_path.exists():
        return {}
    try:
        data = json.loads(alias_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(data, dict) and isinstance(data.get("projects"), dict):
        data = data["projects"]
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if str(value).strip()}


def load_thread_names(path: Path | None = None) -> Dict[str, Dict[str, str]]:
    index_path = path or DEFAULT_SESSION_INDEX_PATH
    if not index_path.exists():
        return {}
    names: Dict[str, Dict[str, str]] = {}
    try:
        lines = index_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return names
    for line in lines:
        if not line.strip():
            continue
        try:
            item: Dict[str, Any] = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = str(item.get("id") or "")
        thread_name = str(item.get("thread_name") or "").strip()
        updated_at = str(item.get("updated_at") or "")
        if not session_id or not thread_name:
            continue
        previous = names.get(session_id)
        if previous and _parse_time(previous.get("updated_at", "")) > _parse_time(updated_at):
            continue
        names[session_id] = {"thread_name": thread_name, "updated_at": updated_at}
    return names


@dataclass(frozen=True)
class ProjectNameResolver:
    aliases: Dict[str, str]
    thread_names: Dict[str, Dict[str, str]]

    def alias_for(self, cwd: str) -> Optional[str]:
        if cwd in self.aliases:
            return self.aliases[cwd]
        normalized = str(Path(cwd).expanduser()) if cwd else cwd
        return self.aliases.get(normalized)

    def thread_name_for(self, session_id: str) -> Optional[str]:
        item = self.thread_names.get(session_id) or {}
        value = str(item.get("thread_name") or "").strip()
        return value or None


def load_project_name_resolver(
    alias_path: Path | None = None,
    session_index_path: Path | None = None,
) -> ProjectNameResolver:
    return ProjectNameResolver(
        aliases=load_project_aliases(alias_path),
        thread_names=load_thread_names(session_index_path),
    )
