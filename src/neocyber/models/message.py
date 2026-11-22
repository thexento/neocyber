"""Chat message and tool-call data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict = field(default_factory=dict)
    status: str = "pending"  # pending | running | completed | failed
    output: Optional[str] = None
    duration: Optional[float] = None
    exit_code: Optional[int] = None


@dataclass
class Message:
    role: Role
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: List[ToolCall] = field(default_factory=list)
    is_streaming: bool = False
    is_error: bool = False
    agent: str = "cyber"
