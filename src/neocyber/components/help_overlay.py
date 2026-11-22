"""Help and keyboard shortcuts reference overlay."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static


HELP_TEXT = """
── KEYBOARD SHORTCUTS ──────────────────────────────────────────

  Ctrl+P          Open Command Palette
  Tab             Toggle Agent Mode (CYBER operator ⟷ PLAN threat modeler)
  Ctrl+X then M   Select / Switch Model Profile
  Ctrl+C          Exit NeoCyber (or Cancel prompt)
  Escape          Cancel ongoing model stream or tool execution
  Enter           Submit prompt (Shift+Enter for multi-line)
  Up / Down       Navigate prompt history

── INPUT COMMANDS & TRIGGERS ───────────────────────────────────

  ! <command>     Directly run shell command without model reasoning
                  Example: !uname -a   or   !nmap -sT 127.0.0.1
  /cyber          Switch to full cyber operator
  /plan           Switch to read-only threat modeler
  /models         Open model picker
  /findings       Open security findings dashboard
  /clear          Clear conversation transcript
  /help           Show this help modal

── ARCHITECTURE & FEATURES ─────────────────────────────────────

  • Real-time token streaming with local Ollama models (Qwen2.5-Coder, etc.)
  • Scope guardrails: prevents destructive operations
  • Evidence persistence: large command outputs saved to reports/evidence/
  • Native unified diffs on file edits
"""


class HelpOverlay(ModalScreen[None]):
    """Modal displaying keybindings and command reference."""

    DEFAULT_CSS = """
    HelpOverlay {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #help-container {
        width: 72;
        max-width: 90%;
        height: auto;
        max-height: 26;
        background: #18181b;
        border: round #22d3ee;
        padding: 1 2;
    }
    #help-title {
        color: #22d3ee;
        text-style: bold;
        margin-bottom: 0;
    }
    #help-content {
        color: #d4d4d8;
        height: auto;
        max-height: 20;
        overflow-y: auto;
    }
    #help-hint {
        color: #71717a;
        margin-top: 1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close"),
        Binding("enter", "dismiss_modal", "Close"),
        Binding("q", "dismiss_modal", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-container"):
            yield Static("❯ NEOCYBER QUICK REFERENCE", id="help-title")
            yield Static(HELP_TEXT, id="help-content")
            yield Static("Press Esc, Enter, or Q to close", id="help-hint")

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)
