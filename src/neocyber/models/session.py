"""Session data model."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from neocyber.models.message import Message


@dataclass
class Session:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = "New Session"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
    agent: str = "cyber"
    model_profile: str = "qwen2.5-coder:7b"
