"""Command palette modal dialog for searching and launching commands."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option


class CommandPalette(ModalScreen[str | None]):
    """Command palette dialog triggered by Ctrl+P or /."""

    DEFAULT_CSS = """
    CommandPalette {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #palette-container {
        width: 76;
        max-width: 92%;
        height: auto;
        max-height: 24;
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
        height: 14;
        border: none;
    }
    #palette-hint {
        color: #71717a;
        margin-top: 1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close"),
    ]

    def __init__(self, profiles: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.commands: List[Tuple[str, str, str, str]] = [
            ("switch_model", "⚙ Switch Model...", "Browse & select active Ollama model (Ctrl+M)", "switch model settings change ollama provider select"),
            ("/cyber", "Switch to Cyber Operator Mode", "Full operator: shell, diagnostics, tools (Tab)", "agent mode cyber execute operator"),
            ("/plan", "Switch to Plan Mode", "Threat modeler & architecture planner (read-only) (Tab)", "agent mode plan planner threat"),
            ("/findings", "Security Findings Dashboard", "Inspect discovered vulnerabilities and evidence", "findings vulns security evidence report"),
            ("/clear", "Clear Screen", "Reset conversation transcript", "clear reset wipe screen"),
            ("/help", "Keyboard Shortcuts & Guide", "View complete key reference and features (?)", "help shortcuts docs info"),
            ("/quit", "Exit NeoCyber", "Close terminal session", "quit exit close stop"),
        ]
        if profiles:
            for pname, pdata in profiles.items():
                self.commands.append(
                    (f"/model {pname}", f"Model: {pname}", f"Quickly activate {pname} ({getattr(pdata, 'param_size', 'Local')})", f"model switch {pname} ollama settings"),
                )

        self._current_filtered: List[Tuple[str, str, str, str]] = list(self.commands)

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-container"):
            yield Static("❯ COMMAND PALETTE & SETTINGS", id="palette-title")
            yield Input(placeholder="Type command (e.g. 'switch model', 'settings', 'cyber')...", id="palette-input")
            yield OptionList(id="palette-list")
            yield Static("Enter: Select · Up/Down: Navigate · Esc: Close", id="palette-hint")

    def on_mount(self) -> None:
        self._populate_list(self.commands)
        self.query_one("#palette-input", Input).focus()

    def _populate_list(self, items: List[Tuple[str, str, str, str]]) -> None:
        self._current_filtered = items
        opt_list = self.query_one("#palette-list", OptionList)
        opt_list.clear_options()
        for cmd, title, desc, _ in items:
            label = Text.assemble(
                (f"{title:<30}", "bold #22d3ee"),
                (f" {desc}", "dim #a1a1aa"),
            )
            opt_list.add_option(Option(prompt=label, id=cmd))
        if items:
            opt_list.highlighted = 0

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip().lower()
        if not query:
            self._populate_list(self.commands)
            return

        filtered = [
            (c, t, d, tags)
            for c, t, d, tags in self.commands
            if query in c.lower() or query in t.lower() or query in d.lower() or query in tags.lower()
        ]
        self._populate_list(filtered)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        opt_list = self.query_one("#palette-list", OptionList)
        if opt_list.highlighted is not None and 0 <= opt_list.highlighted < len(self._current_filtered):
            selected_cmd = self._current_filtered[opt_list.highlighted][0]
            self.dismiss(selected_cmd)
        elif self._current_filtered:
            self.dismiss(self._current_filtered[0][0])
        else:
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        opt_list = self.query_one("#palette-list", OptionList)
        if event.key == "down":
            event.stop()
            event.prevent_default()
            if opt_list.highlighted is not None and opt_list.highlighted < len(self._current_filtered) - 1:
                opt_list.highlighted += 1
            return
        elif event.key == "up":
            event.stop()
            event.prevent_default()
            if opt_list.highlighted is not None and opt_list.highlighted > 0:
                opt_list.highlighted -= 1
            return

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option_id))

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)
