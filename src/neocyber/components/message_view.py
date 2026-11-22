"""Message view widget for rendering user and assistant messages."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from rich.markdown import Markdown
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from neocyber.models.message import Message, Role


class MessageView(Widget):
    """Renders a single chat message (user or assistant) with rich formatting."""

    DEFAULT_CSS = """
    MessageView {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    .msg-header-row {
        height: 1;
        width: 100%;
        layout: horizontal;
        margin-bottom: 0;
    }
    .msg-author {
        text-style: bold;
        width: auto;
    }
    .msg-author.user {
        color: #22d3ee;
    }
    .msg-author.cyber {
        color: #38bdf8;
    }
    .msg-author.plan {
        color: #f59e0b;
    }
    .msg-time {
        color: #52525b;
        text-style: italic;
        margin-left: 2;
        width: auto;
    }
    .msg-body {
        width: 100%;
        height: auto;
        padding-left: 2;
        margin-top: 0;
    }
    .user-block {
        border-left: wide #22d3ee;
        background: #18181b;
        padding: 0 1;
    }
    .assistant-block {
        border-left: wide #0284c7;
        background: #141416;
        padding: 0 1;
    }
    .plan-block {
        border-left: wide #d97706;
        background: #161514;
        padding: 0 1;
    }
    """

    content = reactive("")

    def __init__(
        self,
        role: Role,
        initial_content: str,
        agent: str = "cyber",
        timestamp: Optional[datetime] = None,
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id)
        self.role = role
        self.initial_content = initial_content
        self.agent = agent
        self.msg_timestamp = timestamp or datetime.now()

    def compose(self) -> ComposeResult:
        ts_str = self.msg_timestamp.strftime("%H:%M:%S")

        if self.role == Role.USER:
            container_class = "user-block"
            author_title = "❯ YOU"
            author_style = "bold #22d3ee"
        elif self.agent == "plan":
            container_class = "plan-block"
            author_title = "◆ PLAN [planner]"
            author_style = "bold #f59e0b"
        else:
            container_class = "assistant-block"
            author_title = "◆ CYBER [operator]"
            author_style = "bold #38bdf8"

        with Vertical(classes=container_class):
            yield Static(
                Text.assemble(
                    (author_title, author_style),
                    ("  " + ts_str, "dim #52525b"),
                ),
                classes="msg-header-row",
            )
            yield Static(
                self._format_content(self.initial_content),
                classes="msg-body",
                id=f"{self.id}-content" if self.id else None,
            )

    def _format_content(self, text: str):
        if self.role == Role.USER:
            return Text(text, style="#f4f4f5")
        # For assistant, render rich markdown
        try:
            return Markdown(text)
        except Exception:
            return Text(text, style="#f4f4f5")

    def update_content(self, new_content: str) -> None:
        self.content = new_content
        content_id = f"#{self.id}-content" if self.id else ".msg-body"
        try:
            body = self.query_one(content_id, Static)
            body.update(self._format_content(new_content))
        except Exception:
            pass
