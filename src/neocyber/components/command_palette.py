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
        width: 72;
        max-width: 90%;
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
            ("/models", "⚙ Switch Model...", "Browse & select active Ollama model", "settings switch model ollama provider change"),
            ("/cyber", "Switch to Cyber Operator Mode", "Full operator: shell, tools, read/write", "agent mode cyber execute operator"),
            ("/plan", "Switch to Plan Mode", "Threat modeler & attack chain planner (read-only)", "agent mode plan planner threat"),
            ("/findings", "Security Findings Dashboard", "Inspect discovered vulnerabilities and evidence", "findings vulns security evidence report"),
            ("/clear", "Clear Screen", "Reset current conversation transcript", "clear reset wipe screen"),
            ("/help", "Keyboard Shortcuts & Help", "View complete reference of keys and features", "help shortcuts docs info"),
            ("/quit", "Exit NeoCyber", "Close terminal session", "quit exit close stop"),
        ]
        # Include all locally discovered Ollama models directly in list
        if profiles:
            for pname, pdata in profiles.items():
                self.commands.insert(
                    1,
                    (f"/model {pname}", f"Model: {pname}", f"Switch active LLM ({getattr(pdata, 'param_size', 'Local')})", f"model switch {pname} ollama settings"),
                )

        self._current_filtered: List[Tuple[str, str, str, str]] = list(self.commands)

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-container"):
            yield Static("❯ COMMAND PALETTE & SETTINGS", id="palette-title")
            yield Input(placeholder="Type command (e.g. 'models', 'settings', 'cyber')...", id="palette-input")
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
                (f"{cmd:<20}", "bold #22d3ee"),
                (f"{title} ", "bold #f4f4f5"),
                (f"— {desc}", "dim #71717a"),
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
        """When Enter is pressed inside the search input, select the highlighted option."""
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
