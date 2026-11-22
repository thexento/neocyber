"""Model selector modal dialog for switching Ollama model profiles."""
from __future__ import annotations

from typing import Dict, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from neocyber.models.profile import ModelProfile


class ModelSelector(ModalScreen[str | None]):
    """Interactive model picker matching OpenCode's leader+M dialog."""

    DEFAULT_CSS = """
    ModelSelector {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #selector-container {
        width: 70;
        max-width: 90%;
        height: auto;
        max-height: 22;
        background: #18181b;
        border: round #38bdf8;
        padding: 1 2;
    }
    #selector-title {
        color: #38bdf8;
        text-style: bold;
        margin-bottom: 1;
    }
    #selector-list {
        background: #111113;
        border: round #27272a;
        height: 12;
        margin-bottom: 1;
    }
    #selector-hint {
        color: #71717a;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close"),
    ]

    def __init__(
        self,
        profiles: Dict[str, ModelProfile],
        active_profile: str,
        local_models: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        super().__init__()
        self.profiles = profiles
        self.active_profile = active_profile
        self.local_models = local_models or []

    def compose(self) -> ComposeResult:
        with Vertical(id="selector-container"):
            yield Static("❯ SETTINGS: SELECT LOCAL MODEL", id="selector-title")
            yield OptionList(id="selector-list")
            yield Static("Enter: Select Model · Up/Down: Navigate · Esc: Cancel", id="selector-hint")

    def on_mount(self) -> None:
        opt_list = self.query_one("#selector-list", OptionList)
        opt_list.clear_options()

        active_idx = 0
        idx = 0
        for name, p in self.profiles.items():
            is_active = (name == self.active_profile)
            if is_active:
                active_idx = idx
            badge = "  [ACTIVE]" if is_active else ""
            label = Text.assemble(
                (f"{name:<20}", "bold #38bdf8" if is_active else "bold #f4f4f5"),
                (f" ({p.param_size})", "dim #a1a1aa"),
                (f"  ctx: {p.context_budget}t", "dim #71717a"),
                (badge, "bold #10b981" if is_active else ""),
            )
            opt_list.add_option(Option(prompt=label, id=name))
            idx += 1

        # Add detected unconfigured Ollama models if any
        configured_names = {p.ollama_name for p in self.profiles.values()}
        for lm in self.local_models:
            mname = lm.get("name", "")
            if mname and mname not in configured_names and mname not in self.profiles:
                label = Text.assemble(
                    (f"{mname:<20}", "#a1a1aa"),
                    (f" (Ollama: {lm.get('size', '?')})", "dim #71717a"),
                )
                opt_list.add_option(Option(prompt=label, id=mname))

        opt_list.highlighted = active_idx
        opt_list.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option_id))

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)
