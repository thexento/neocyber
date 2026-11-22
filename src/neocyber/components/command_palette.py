"""Command palette modal dialog for searching and launching commands."""
from __future__ import annotations

from typing import Callable, List, Tuple

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option


COMMANDS: List[Tuple[str, str, str]] = [
    ("/cyber", "Switch to Cyber Operator Mode", "Shell, tools, read/write active execution"),
    ("/plan", "Switch to Plan Mode", "Threat modeler & attack chain planner (read-only)"),
    ("/models", "Select Model Profile", "Browse local Ollama models and change active LLM"),
    ("/findings", "Security Findings Dashboard", "Inspect discovered vulnerabilities and evidence"),
    ("/clear", "Clear Screen", "Reset current conversation transcript"),
    ("/help", "Keyboard Shortcuts & Help", "View complete reference of keys and features"),
    ("/quit", "Exit NeoCyber", "Close terminal session"),
]


class CommandPalette(ModalScreen[str | None]):
    """Command palette dialog triggered by Ctrl+P or /."""

    DEFAULT_CSS = """
    CommandPalette {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #palette-container {
        width: 68;
        max-width: 90%;
        height: auto;
        max-height: 22;
        background: #18181b;
        border: round #22d3ee;
        padding: 1;
    }
    #palette-title {
        color: #22d3ee;
        text-style: bold;
        margin-bottom: 1;
    }
    #palette-input {
        background: #111113;
        border: round #3f3f46;
        color: #f4f4f5;
        margin-bottom: 1;
    }
    #palette-input:focus {
        border: round #22d3ee;
    }
    #palette-list {
        background: #18181b;
        height: 12;
        border: none;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-container"):
            yield Static("❯ COMMAND PALETTE", id="palette-title")
            yield Input(placeholder="Type command name...", id="palette-input")
            yield OptionList(id="palette-list")

    def on_mount(self) -> None:
        self._populate_list(COMMANDS)
        self.query_one("#palette-input", Input).focus()

    def _populate_list(self, items: List[Tuple[str, str, str]]) -> None:
        opt_list = self.query_one("#palette-list", OptionList)
        opt_list.clear_options()
        for cmd, title, desc in items:
            label = Text.assemble(
                (f"{cmd:<12}", "bold #22d3ee"),
                (f"{title} ", "bold #f4f4f5"),
                (f"— {desc}", "dim #71717a"),
            )
            opt_list.add_option(Option(prompt=label, id=cmd))

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip().lower()
        filtered = [
            (c, t, d)
            for c, t, d in COMMANDS
            if query in c.lower() or query in t.lower() or query in d.lower()
        ]
        self._populate_list(filtered)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option_id)

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)
