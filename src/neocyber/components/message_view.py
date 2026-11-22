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
        margin: 0 0 1 0;
        padding: 0;
    }
    .msg-header-row {
        height: 1;
        width: 100%;
        layout: horizontal;
        margin-bottom: 0;
        padding: 0;
    }
    .msg-body {
        width: 100%;
        height: auto;
        padding-left: 1;
        margin-top: 0;
    }
    .user-block {
        border-left: solid #22d3ee;
        background: #18181b;
        padding: 0 1;
        margin: 0;
    }
    .assistant-block {
        border-left: solid #38bdf8;
        background: #141416;
        padding: 0 1;
        margin: 0;
    }
    .plan-block {
        border-left: solid #f59e0b;
        background: #151517;
        padding: 0 1;
        margin: 0;
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
            author_title = "✦ PLAN"
            author_style = "bold #f59e0b"
        else:
            container_class = "assistant-block"
            author_title = "✦ CYBER"
            author_style = "bold #38bdf8"

        with Vertical(classes=container_class):
            yield Static(
                Text.assemble(
                    (author_title, author_style),
                    (f"  {ts_str}", "dim #52525b"),
                ),
                classes="msg-header-row",
            )
            yield Static(
                self._format_content(self.initial_content),
                classes="msg-body",
                id=f"{self.id}-content" if self.id else None,
            )

    def _format_content(self, text: str):
        if not text:
            return Text("")
        if self.role == Role.USER:
            return Text(text, style="#f4f4f5")
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
