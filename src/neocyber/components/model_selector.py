"""Model selector modal dialog for switching Ollama model profiles."""
from __future__ import annotations

from typing import Dict, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
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
            yield Input(placeholder="Search local models…", id="selector-search")
            yield OptionList(id="selector-list")
            yield Static("Enter: Select Model · Up/Down: Navigate · Esc: Cancel", id="selector-hint")

    def on_mount(self) -> None:
        self._populate()
        self.query_one("#selector-search", Input).focus()

    def _all_models(self):
        """Profiles are capability metadata; discovered models remain selectable."""
        models = []
        configured_names = {p.ollama_name for p in self.profiles.values()}
        for name, profile in self.profiles.items():
            models.append((name, profile.param_size, f"ctx: {profile.context_budget}t · Ollama", name == self.active_profile))
        for local in self.local_models:
            name = local.get("name", "")
            if name and name not in configured_names and name not in self.profiles:
                models.append((name, local.get("size", "?"), "Ollama · capabilities unknown", name == self.active_profile))
        return models

    def _populate(self, query: str = "") -> None:
        opt_list = self.query_one("#selector-list", OptionList)
        opt_list.clear_options()
        active_idx = 0
        idx = 0
        for name, size, details, is_active in self._all_models():
            if query and query.lower() not in f"{name} {size} {details}".lower():
                continue
            if is_active:
                active_idx = idx
            badge = "  [ACTIVE]" if is_active else ""
            label = Text.assemble(
                (f"{name:<20}", "bold #38bdf8" if is_active else "bold #f4f4f5"),
                (f" ({size})", "dim #a1a1aa"),
                (f"  {details}", "dim #71717a"),
                (badge, "bold #10b981" if is_active else ""),
            )
            opt_list.add_option(Option(prompt=label, id=name))
            idx += 1
        if idx:
            opt_list.highlighted = active_idx

    def on_input_changed(self, event: Input.Changed) -> None:
        self._populate(event.value.strip())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        options = self.query_one("#selector-list", OptionList)
        if options.highlighted is not None:
            option = options.get_option_at_index(options.highlighted)
            self.dismiss(str(option.id))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option_id))

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)
