"""Clean, borderless message view widget matching Antigravity / Claude Code stream formatting."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from rich.markdown import Markdown
from rich.text import Text
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from neocyber.models.message import Message, Role


class MessageView(Widget):
    """Renders a single chat message cleanly without bulky cards or thick borders."""

    DEFAULT_CSS = """
    MessageView {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
        padding: 0;
        layout: vertical;
    }
    .msg-user-row {
        height: auto;
        width: 100%;
        margin-top: 0;
        margin-bottom: 0;
        padding: 0;
    }
    .msg-assistant-row {
        height: auto;
        width: 100%;
        margin-top: 0;
        padding-left: 2;
    }
    .assistant-author-badge {
        color: #38bdf8;
        text-style: bold;
        margin-bottom: 0;
        height: 1;
    }
    .plan-author-badge {
        color: #f59e0b;
        text-style: bold;
        margin-bottom: 0;
        height: 1;
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
            # Clean prompt line right above agent response
            prompt_text = Text.assemble(
                ("❯ ", "bold #22d3ee"),
                (self.initial_content, "bold #f4f4f5"),
                (f"  {ts_str}", "dim #52525b"),
            )
            yield Static(prompt_text, classes="msg-user-row", id=f"{self.id}-content" if self.id else None)
        else:
            badge_class = "plan-author-badge" if self.agent == "plan" else "assistant-author-badge"
            badge_text = "✦ PLAN" if self.agent == "plan" else "✦ CYBER"
            badge_style = "bold #f59e0b" if self.agent == "plan" else "bold #38bdf8"

            yield Static(
                Text.assemble(
                    (badge_text, badge_style),
                    (f"  {ts_str}", "dim #52525b"),
                ),
                classes=badge_class,
            )
            yield Static(
                self._format_content(self.initial_content),
                classes="msg-assistant-row",
                id=f"{self.id}-content" if self.id else None,
            )

    def _format_content(self, text: str):
        if not text:
            return Text("")
        try:
            return Markdown(text)
        except Exception:
            return Text(text, style="#f4f4f5")

    def update_content(self, new_content: str) -> None:
        self.content = new_content
        content_id = f"#{self.id}-content" if self.id else ".msg-assistant-row"
        try:
            body = self.query_one(content_id, Static)
            body.update(self._format_content(new_content))
        except Exception:
            pass
