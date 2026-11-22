"""Tool execution display card showing command/tool details and live outputs."""
from __future__ import annotations

from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class ToolExecutionCard(Widget):
    """OpenCode-style tool execution card with status badges, timer, and output display."""

    DEFAULT_CSS = """
    ToolExecutionCard {
        width: 100%;
        height: auto;
        margin: 1 0;
        background: #141416;
        border: round #3f3f46;
        padding: 0 1;
    }
    ToolExecutionCard.status-running {
        border: round #22d3ee;
    }
    ToolExecutionCard.status-completed {
        border: round #10b981;
    }
    ToolExecutionCard.status-failed {
        border: round #ef4444;
    }

    .tool-header-row {
        height: 1;
        width: 100%;
        layout: horizontal;
    }
    .tool-title-static {
        color: #f4f4f5;
        text-style: bold;
        width: 1fr;
    }
    .tool-status-badge {
        width: auto;
        text-style: bold;
    }
    .tool-output-scroll {
        color: #d4d4d8;
        background: #0d0d0f;
        padding: 0 1;
        margin-top: 1;
        height: auto;
        max-height: 14;
        overflow-y: auto;
    }
    """

    status = reactive("running")
    output_text = reactive("")

    def __init__(
        self,
        tool_id: str,
        name: str,
        description: str,
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id or f"card-{tool_id}")
        self.tool_id = tool_id
        self.tool_name = name
        self.tool_description = description
        self.duration: float = 0.0
        self.exit_code: int = 0

    def compose(self) -> ComposeResult:
        with Horizontal(classes="tool-header-row"):
            yield Static(
                f"▶ {self.tool_name.upper()}  {self.tool_description}",
                classes="tool-title-static",
                id=f"{self.id}-title",
            )
            yield Static(
                "[ RUNNING... ]",
                classes="tool-status-badge",
                id=f"{self.id}-badge",
            )
        yield Static(
            "",
            classes="tool-output-scroll",
            id=f"{self.id}-output",
        )

    def on_mount(self) -> None:
        self.add_class("status-running")

    def append_chunk(self, chunk: str) -> None:
        self.output_text += chunk
        output_widget = self.query_one(f"#{self.id}-output", Static)
        output_widget.update(self.output_text)

    def set_completed(self, exit_code: int, output: str, duration: float) -> None:
        self.exit_code = exit_code
        self.duration = duration
        self.output_text = output

        self.remove_class("status-running")
        badge = self.query_one(f"#{self.id}-badge", Static)
        output_widget = self.query_one(f"#{self.id}-output", Static)

        if exit_code == 0:
            self.add_class("status-completed")
            badge.update(f"[ ✓ SUCCESS · {duration}s ]")
        else:
            self.add_class("status-failed")
            badge.update(f"[ ✗ FAILED · Exit {exit_code} · {duration}s ]")

        # Format output
        if not output.strip():
            output_widget.update(Text("(No output generated)", style="dim italic"))
        else:
            output_widget.update(output)
