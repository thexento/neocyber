"""Persistent, typed records for work performed by an agent turn.

These records are deliberately separate from rendered TUI strings: the same
history can be restored, inspected, or rendered by another client.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ActivityEvent:
    type: str
    summary: str
    task_id: str
    status: str = "completed"
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: str = ""
    parent_id: Optional[str] = None
    duration: Optional[float] = None
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ActivityEvent":
        return cls(**raw)


@dataclass
class TaskState:
    objective: str
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    plan: List[str] = field(default_factory=list)
    completed: List[str] = field(default_factory=list)
    pending: List[str] = field(default_factory=list)
    current_task: str = ""
    hypothesis: str = ""
    completion_criteria: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    files_read: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    verification: List[str] = field(default_factory=list)
    completion_reason: str = ""


class SessionStore:
    """Small JSON session store, intentionally dependency-free for local use."""

    def __init__(self, workspace: str) -> None:
        self.path = Path(workspace) / ".neocyber" / "session.json"

    def save(self, session_id: str, messages: List[Dict[str, Any]], events: List[ActivityEvent], task: Optional[TaskState], model: str, agent: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "session_id": session_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "agent": agent,
            "messages": messages,
            "events": [event.to_dict() for event in events],
            "task": asdict(task) if task else None,
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self) -> Dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
