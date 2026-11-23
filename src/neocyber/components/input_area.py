"""Input area widget for multiline prompt input with history and shortcuts."""
from __future__ import annotations

from typing import List, Optional

from textual import events
from textual.app import ComposeResult
from textual.containers import Container
from textual.message import Message as TextualMessage
from textual.widget import Widget
from textual.widgets import TextArea


class PromptTextArea(TextArea):
    """Custom TextArea that intercepts Enter for submission, Shift+Enter for newlines, and PageUp/PageDown for chat scrolling."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.prompt_history: List[str] = []
        self.prompt_history_index: int = -1

    async def _on_key(self, event: events.Key) -> None:
        # Shift+Enter -> Insert newline
        if event.key == "shift+enter":
            event.stop()
            event.prevent_default()
            start, end = self.selection
            self._replace_via_keyboard("\n", start, end)
            return

        # Enter / Return -> Submit prompt
        if event.key in ("enter", "return"):
            event.stop()
            event.prevent_default()
            val = self.text.strip()
            if val:
                self.prompt_history.append(val)
                self.prompt_history_index = -1
                self.text = ""
                self.post_message(InputArea.Submitted(val))
            return

        # Tab -> Dispatch TabPressed to switch agent mode
        if event.key == "tab":
            event.stop()
            event.prevent_default()
            self.post_message(InputArea.TabPressed())
            return

        # Scrolling shortcuts to navigate chat while typing
        if event.key in ("pageup", "shift+pageup"):
            event.stop()
            event.prevent_default()
            self.post_message(InputArea.ScrollChat("pageup"))
            return

        if event.key in ("pagedown", "shift+pagedown"):
            event.stop()
            event.prevent_default()
            self.post_message(InputArea.ScrollChat("pagedown"))
            return

        if event.key in ("ctrl+up", "ctrl+k", "shift+up", "alt+up"):
            event.stop()
            event.prevent_default()
            self.post_message(InputArea.ScrollChat("up"))
            return

        if event.key in ("ctrl+down", "ctrl+j", "shift+down", "alt+down"):
            event.stop()
            event.prevent_default()
            self.post_message(InputArea.ScrollChat("down"))
            return

        if event.key in ("ctrl+home", "alt+home"):
            event.stop()
            event.prevent_default()
            self.post_message(InputArea.ScrollChat("home"))
            return

        if event.key in ("ctrl+end", "alt+end"):
            event.stop()
            event.prevent_default()
            self.post_message(InputArea.ScrollChat("end"))
            return

        # Up arrow at the very top line cycles history backwards
        if event.key == "up" and self.cursor_location[0] == 0:
            if self.prompt_history:
                event.stop()
                event.prevent_default()
                if self.prompt_history_index == -1:
                    self.prompt_history_index = len(self.prompt_history) - 1
                elif self.prompt_history_index > 0:
                    self.prompt_history_index -= 1
                self.text = self.prompt_history[self.prompt_history_index]
                self.cursor_location = (0, len(self.text))
            return

        # Down arrow at the bottom line cycles history forwards
        if event.key == "down" and self.cursor_location[0] >= self.document.line_count - 1:
            if self.prompt_history and self.prompt_history_index != -1:
                event.stop()
                event.prevent_default()
                if self.prompt_history_index < len(self.prompt_history) - 1:
                    self.prompt_history_index += 1
                    self.text = self.prompt_history[self.prompt_history_index]
                    self.cursor_location = (0, len(self.text))
                else:
                    self.prompt_history_index = -1
                    self.text = ""
            return

        # Default TextArea key handling (typing, arrows, backspace, selection, etc.)
        await super()._on_key(event)


class InputArea(Widget):
    """Multiline prompt input area matching OpenCode's terminal input experience."""

    DEFAULT_CSS = """
    InputArea {
        dock: bottom;
        height: auto;
        min-height: 3;
        max-height: 8;
        background: #121214;
        padding: 0 1;
        margin-bottom: 0;
    }
    .input-frame {
        border: round #3f3f46;
        background: #18181b;
        height: auto;
        min-height: 3;
        max-height: 8;
        padding: 0;
    }
    .input-frame:focus-within {
        border: round #22d3ee;
    }
    #prompt-textarea {
        width: 100%;
        height: auto;
        min-height: 2;
        max-height: 6;
        background: #18181b;
        border: none;
        padding: 0 1;
    }
    """

    class Submitted(TextualMessage):
        """Dispatched when the user submits a prompt."""

        def __init__(self, value: str) -> None:
            self.value = value
            super().__init__()

    class TabPressed(TextualMessage):
        """Dispatched when Tab is pressed to cycle agent modes."""

    class ScrollChat(TextualMessage):
        """Dispatched when PageUp/PageDown is pressed to scroll chat history."""

        def __init__(self, direction: str) -> None:
            self.direction = direction
            super().__init__()

    def compose(self) -> ComposeResult:
        with Container(classes="input-frame"):
            yield PromptTextArea(
                id="prompt-textarea",
                show_line_numbers=False,
            )

    def on_mount(self) -> None:
        self.focus_input()

    def focus_input(self) -> None:
        self.query_one("#prompt-textarea", PromptTextArea).focus()

    def get_text(self) -> str:
        return self.query_one("#prompt-textarea", PromptTextArea).text

    def set_text(self, text: str) -> None:
        textarea = self.query_one("#prompt-textarea", PromptTextArea)
        textarea.text = text
        textarea.cursor_location = (0, len(text))

    def clear(self) -> None:
        textarea = self.query_one("#prompt-textarea", PromptTextArea)
        textarea.text = ""
        textarea.prompt_history_index = -1
