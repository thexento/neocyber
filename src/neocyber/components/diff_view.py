"""Diff viewer widget rendering color-coded git-style unified diffs."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static


class DiffView(Widget):
    """Renders a unified diff with green additions and red deletions."""

    DEFAULT_CSS = """
    DiffView {
        width: 100%;
        height: auto;
        margin: 1 0;
        background: #0d0d0f;
        border: round #27272a;
        padding: 0 1;
    }
    .diff-title {
        color: #38bdf8;
        text-style: bold;
        margin-bottom: 0;
    }
    .diff-body {
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, filename: str, diff_text: str, id: str | None = None) -> None:
        super().__init__(id=id)
        self.filename = filename
        self.diff_text = diff_text

    def compose(self) -> ComposeResult:
        yield Static(f"⚡ DIFF: {self.filename}", classes="diff-title")
        yield Static(self._render_diff(), classes="diff-body")

    def _render_diff(self) -> Text:
        rich_text = Text()
        for line in self.diff_text.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                rich_text.append(f"{line}\n", style="bold #94a3b8")
            elif line.startswith("@@"):
                rich_text.append(f"{line}\n", style="bold #38bdf8")
            elif line.startswith("+"):
                rich_text.append(f"{line}\n", style="#34d399 on #064e3b")
            elif line.startswith("-"):
                rich_text.append(f"{line}\n", style="#f87171 on #7f1d1d")
            else:
                rich_text.append(f"{line}\n", style="#a1a1aa")
        return rich_text
