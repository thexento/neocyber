"""Chat conversation area handling message rendering and streaming viewports."""
from __future__ import annotations

from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from neocyber.components.diff_view import DiffView
from neocyber.components.message_view import MessageView
from neocyber.components.tool_display import ToolExecutionCard
from neocyber.models.message import Role


class ChatArea(VerticalScroll):
    """Scrollable conversation container maintaining message history and tool cards."""

    DEFAULT_CSS = """
    ChatArea {
        height: 1fr;
        background: #141416;
        padding: 0 1;
        scrollbar-size-vertical: 1;
        scrollbar-color: #27272a #141416;
    }
    .welcome-banner {
        width: 100%;
        margin: 1 0;
        padding: 1;
        background: #18181b;
        border: round #27272a;
    }
    """

    def __init__(self, workspace_name: str = "neocyber", id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.workspace_name = workspace_name
        self._msg_counter = 0

    def compose(self) -> ComposeResult:
        welcome_text = Text.assemble(
            ("NEOCYBER", "bold #22d3ee"),
            (" · Cybersecurity AI Harness for Local Models\n", "bold #f4f4f5"),
            ("Workspace: ", "dim #71717a"),
            (f"{self.workspace_name}\n", "bold #a1a1aa"),
            ("Modes: ", "dim #71717a"),
            ("cyber", "bold #38bdf8"),
            (" (full operator) · ", "dim #71717a"),
            ("plan", "bold #f59e0b"),
            (" (threat modeler)\n", "dim #71717a"),
            ("Type a prompt or ", "dim #71717a"),
            ("!", "#38bdf8"),
            (" for direct shell command. Press ", "dim #71717a"),
            ("Ctrl+P", "bold #22d3ee"),
            (" for commands, ", "dim #71717a"),
            ("Tab", "bold #f59e0b"),
            (" to toggle mode.", "dim #71717a"),
        )
        yield Static(welcome_text, classes="welcome-banner", id="welcome-msg")

    def add_user_message(self, content: str) -> MessageView:
        self._msg_counter += 1
        msg = MessageView(
            role=Role.USER,
            initial_content=content,
            id=f"msg-{self._msg_counter}",
        )
        self.mount(msg)
        self.scroll_end(animate=False)
        return msg

    def start_assistant_message(self, agent: str = "cyber") -> MessageView:
        self._msg_counter += 1
        msg = MessageView(
            role=Role.ASSISTANT,
            initial_content="",
            agent=agent,
            id=f"msg-{self._msg_counter}",
        )
        self.mount(msg)
        self.scroll_end(animate=False)
        return msg

    def add_tool_card(self, tool_id: str, name: str, description: str) -> ToolExecutionCard:
        card = ToolExecutionCard(
            tool_id=tool_id,
            name=name,
            description=description,
        )
        self.mount(card)
        self.scroll_end(animate=False)
        return card

    def add_diff_view(self, filename: str, diff_text: str) -> DiffView:
        diff_widget = DiffView(filename=filename, diff_text=diff_text)
        self.mount(diff_widget)
        self.scroll_end(animate=False)
        return diff_widget

    def clear_chat(self) -> None:
        for child in list(self.children):
            if child.id != "welcome-msg":
                child.remove()
