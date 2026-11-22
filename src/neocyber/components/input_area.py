"""Input area widget for multiline prompt input with history and shortcuts."""
from __future__ import annotations

from typing import List, Optional

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.message import Message as TextualMessage
from textual.widget import Widget
from textual.widgets import TextArea


class InputArea(Widget):
    """Multiline prompt input area matching OpenCode's terminal input experience."""

    DEFAULT_CSS = """
    InputArea {
        dock: bottom;
        height: auto;
        min-height: 3;
        max-height: 8;
        background: #141416;
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

    def __init__(self, id: Optional[str] = None) -> None:
        super().__init__(id=id)
        self.history: List[str] = []
        self.history_index: int = -1

    def compose(self) -> ComposeResult:
        with Container(classes="input-frame"):
            yield TextArea(
                id="prompt-textarea",
                show_line_numbers=False,
            )

    def on_mount(self) -> None:
        textarea = self.query_one("#prompt-textarea", TextArea)
        textarea.focus()

    def focus_input(self) -> None:
        self.query_one("#prompt-textarea", TextArea).focus()

    def get_text(self) -> str:
        return self.query_one("#prompt-textarea", TextArea).text

    def set_text(self, text: str) -> None:
        textarea = self.query_one("#prompt-textarea", TextArea)
        textarea.text = text
        textarea.cursor_location = (0, len(text))

    def clear(self) -> None:
        self.query_one("#prompt-textarea", TextArea).text = ""
        self.history_index = -1

    def on_key(self, event: events.Key) -> None:
        textarea = self.query_one("#prompt-textarea", TextArea)

        if event.key == "enter" and not event.shift:
            event.prevent_default()
            event.stop()
            val = textarea.text.strip()
            if val:
                self.history.append(val)
                self.history_index = -1
                self.clear()
                self.post_message(self.Submitted(val))
            return

        if event.key == "tab":
            event.prevent_default()
            event.stop()
            self.post_message(self.TabPressed())
            return

        # Up arrow at the very top line cycles history backwards
        if event.key == "up" and textarea.cursor_location[0] == 0:
            if self.history:
                event.prevent_default()
                event.stop()
                if self.history_index == -1:
                    self.history_index = len(self.history) - 1
                elif self.history_index > 0:
                    self.history_index -= 1
                self.set_text(self.history[self.history_index])
            return

        # Down arrow at the bottom line cycles history forwards
        if event.key == "down" and textarea.cursor_location[0] >= textarea.document.line_count - 1:
            if self.history and self.history_index != -1:
                event.prevent_default()
                event.stop()
                if self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    self.set_text(self.history[self.history_index])
                else:
                    self.history_index = -1
                    self.clear()
            return
