"""Status bar widget displaying agent mode, active model, and shortcuts."""
from __future__ import annotations

from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class StatusBar(Widget):
    """Bottom persistent status bar matching OpenCode's sleek footer."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: #18181b;
        color: #71717a;
        padding: 0 1;
        layout: horizontal;
    }
    .status-left {
        width: auto;
        height: 1;
    }
    .status-middle {
        width: auto;
        height: 1;
        margin-left: 2;
    }
    .status-right {
        width: 1fr;
        height: 1;
        text-align: right;
    }
    """

    agent_mode = reactive("cyber")
    model_name = reactive("qwen2.5-coder:7b")
    status_text = reactive("READY")

    def __init__(
        self,
        initial_agent: str = "cyber",
        initial_model: str = "qwen2.5-coder:7b",
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id)
        self.agent_mode = initial_agent
        self.model_name = initial_model

    def compose(self) -> ComposeResult:
        yield Static("", classes="status-left", id="status-left-static")
        yield Static("", classes="status-middle", id="status-middle-static")
        yield Static(
            Text.assemble(
                ("^P", "bold #22d3ee"),
                (" commands  ", "dim #71717a"),
                ("Tab", "bold #f59e0b"),
                (" switch agent  ", "dim #71717a"),
                ("Esc", "bold #ef4444"),
                (" stop  ", "dim #71717a"),
                ("? /help", "dim #a1a1aa"),
            ),
            classes="status-right",
        )

    def on_mount(self) -> None:
        self._update_display()

    def watch_agent_mode(self, new_mode: str) -> None:
        self._update_display()

    def watch_model_name(self, new_model: str) -> None:
        self._update_display()

    def watch_status_text(self, new_status: str) -> None:
        self._update_display()

    def _update_display(self) -> None:
        try:
            left = self.query_one("#status-left-static", Static)
            middle = self.query_one("#status-middle-static", Static)

            if self.agent_mode == "cyber":
                badge = Text(" CYBER [operator] ", style="bold #ffffff on #0891b2")
            else:
                badge = Text(" PLAN [planner] ", style="bold #ffffff on #d97706")

            left.update(badge)

            middle_text = Text.assemble(
                ("  model: ", "dim #71717a"),
                (f"{self.model_name}", "bold #f4f4f5"),
                (f"  [{self.status_text}]", "dim #38bdf8" if self.status_text == "READY" else "bold #22d3ee"),
            )
            middle.update(middle_text)
        except Exception:
            pass
