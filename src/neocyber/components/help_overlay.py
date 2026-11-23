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

  Ctrl+P          Command Palette & Settings (type 'switch model', 'cyber', etc.)
  Ctrl+M / F2     Switch AI Model Profile directly
  Tab             Toggle Agent Mode (CYBER operator ⟷ PLAN threat modeler)
  Escape          Cancel ongoing model stream or tool execution
  Enter           Submit prompt (Shift+Enter for multi-line)
  Up / Down       Navigate prompt history
  PageUp/PageDn   Scroll conversation transcript
  Shift+Up/Down   Scroll conversation transcript
  Ctrl+Shift+C    Native terminal copy (highlight any text across screen)
  Right-click     Native terminal context menu (Copy / Paste)

── INPUT COMMANDS & TRIGGERS ───────────────────────────────────

  ! <command>     Direct shell passthrough (e.g. !uname -a, !curl -I localhost)
  /models         Open model picker dialog
  /cyber          Switch to full cybersecurity operator mode
  /plan           Switch to architecture & threat modeler mode
  /findings       Open security findings dashboard
  /clear          Clear conversation transcript
  /help           Show this reference overlay
  /quit           Exit NeoCyber session

── FEATURES & DESIGN ───────────────────────────────────────────

  • Host-aware agent: automatically knows your distro, kernel, and package manager
  • Native terminal mouse: full text highlighting across user & AI messages
  • Two-phase synthesis: tool executions are grounded and analyzed without looping
  • Local Ollama: zero telemetry, fast private streaming
"""


class HelpOverlay(ModalScreen[None]):
    """Modal displaying keybindings and command reference."""

    DEFAULT_CSS = """
    HelpOverlay {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #help-container {
        width: 74;
        max-width: 92%;
        height: auto;
        max-height: 26;
        background: #141416;
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
