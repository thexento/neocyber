"""Typed event system for NeoCyber TUI.

The agent engine publishes these events; the TUI renders them.
Events use Textual's Message system for thread-safe posting.
"""
from __future__ import annotations

from textual.message import Message


class SessionStarted(Message):
    """A new session has been created or loaded."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__()


class UserMessageSubmitted(Message):
    """The user submitted a prompt."""

    def __init__(self, content: str) -> None:
        self.content = content
        super().__init__()


class ModelRequestStarted(Message):
    """A request to the model has been initiated."""

    def __init__(self, model: str) -> None:
        self.model = model
        super().__init__()


class ModelTokenReceived(Message):
    """A single token arrived from the streaming model."""

    def __init__(self, token: str) -> None:
        self.token = token
        super().__init__()


class ModelRequestCompleted(Message):
    """The model finished generating its response."""

    def __init__(self, full_response: str) -> None:
        self.full_response = full_response
        super().__init__()


class ModelRequestFailed(Message):
    """The model request failed."""

    def __init__(self, error: str) -> None:
        self.error = error
        super().__init__()


class ToolCallRequested(Message):
    """The model requested a tool call."""

    def __init__(self, tool_id: str, name: str, arguments: dict) -> None:
        self.tool_id = tool_id
        self.name = name
        self.arguments = arguments
        super().__init__()


class ToolExecutionStarted(Message):
    """A tool has begun executing."""

    def __init__(self, tool_id: str, name: str, description: str = "") -> None:
        self.tool_id = tool_id
        self.name = name
        self.description = description
        super().__init__()


class ToolOutputReceived(Message):
    """Incremental output from a running tool."""

    def __init__(self, tool_id: str, chunk: str) -> None:
        self.tool_id = tool_id
        self.chunk = chunk
        super().__init__()


class ToolExecutionCompleted(Message):
    """A tool finished executing."""

    def __init__(
        self,
        tool_id: str,
        output: str,
        duration: float,
        exit_code: int = 0,
    ) -> None:
        self.tool_id = tool_id
        self.output = output
        self.duration = duration
        self.exit_code = exit_code
        super().__init__()


class ToolExecutionFailed(Message):
    """A tool execution failed."""

    def __init__(self, tool_id: str, error: str) -> None:
        self.tool_id = tool_id
        self.error = error
        super().__init__()


class AgentError(Message):
    """A general agent-level error occurred."""

    def __init__(self, error: str) -> None:
        self.error = error
        super().__init__()
