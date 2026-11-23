"""Main NeoCyber Textual Application matching Antigravity and OpenCode UX design."""
from __future__ import annotations

import asyncio
import os
import subprocess
from typing import Dict, List, Optional

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual import events
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from neocyber.components.chat import ChatArea
from neocyber.components.activity import ActivityCard, ActivityGroup
from neocyber.components.command_palette import CommandPalette
from neocyber.components.findings_view import FindingsOverlay
from neocyber.components.help_overlay import HelpOverlay
from neocyber.components.input_area import InputArea
from neocyber.components.model_selector import ModelSelector
from neocyber.components.status_bar import StatusBar
from neocyber.engine.agent import AgentRunner
from neocyber.engine.ollama import OllamaClient
from neocyber.engine.tools import SecurityValidator
from neocyber.models.message import Message, Role, ToolCall
from neocyber.models.activity import ActivityEvent, SessionStore, TaskState
from neocyber.models.profile import ModelProfile, load_profiles


class ConfirmCommandModal(ModalScreen[bool]):
    """Clean, subtle confirmation prompt only for sensitive/sudo commands."""

    DEFAULT_CSS = """
    ConfirmCommandModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #confirm-box {
        width: 68;
        max-width: 90%;
        height: auto;
        background: #18181b;
        border: round #f59e0b;
        padding: 1 2;
    }
    #confirm-title {
        color: #f59e0b;
        text-style: bold;
        margin-bottom: 1;
    }
    #confirm-cmd {
        background: #0d0d0f;
        color: #38bdf8;
        padding: 1;
        border: round #27272a;
        margin-bottom: 1;
    }
    #confirm-buttons {
        height: 3;
        width: 100%;
        align: center middle;
        layout: horizontal;
    }
    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("enter", "confirm_run", "Run"),
        Binding("y", "confirm_run", "Run"),
        Binding("escape", "confirm_skip", "Skip"),
        Binding("n", "confirm_skip", "Skip"),
    ]

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command

    def compose(self) -> ComposeResult:
        with Container(id="confirm-box"):
            yield Static("⚡ ELEVATED PRIVILEGES REQUIRED", id="confirm-title")
            yield Static(f"$ {self.command}", id="confirm-cmd")
            with Horizontal(id="confirm-buttons"):
                yield Button("Approve (Enter / Y)", variant="success", id="btn-approve")
                yield Button("Skip (Esc / N)", variant="error", id="btn-skip")

    def on_mount(self) -> None:
        self.query_one("#btn-approve", Button).focus()

    @on(Button.Pressed, "#btn-approve")
    def action_confirm_run(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-skip")
    def action_confirm_skip(self) -> None:
        self.dismiss(False)


class NeoCyberApp(App[None]):
    """NeoCyber Terminal Application."""

    CSS_PATH = "app.tcss"
    TITLE = "NeoCyber"
    SUB_TITLE = "Cybersecurity AI Harness"

    BINDINGS = [
        Binding("ctrl+p", "open_command_palette", "Commands", show=True),
        Binding("tab", "toggle_agent", "Switch Agent", show=True),
        Binding("ctrl+m", "open_model_selector", "Models", show=True),
        Binding("f2", "open_model_selector", "Models", show=False),
        Binding("ctrl+y", "copy_last_response", "Copy Response", show=True),
        Binding("ctrl+shift+c", "copy_last_exchange", "Copy Exchange", show=True),
        Binding("pageup", "scroll_chat_pageup", "Scroll Up", show=False),
        Binding("pagedown", "scroll_chat_pagedown", "Scroll Down", show=False),
        Binding("shift+up", "scroll_chat_up", "Scroll Up", show=False),
        Binding("shift+down", "scroll_chat_down", "Scroll Down", show=False),
        Binding("escape", "cancel_action", "Cancel / Stop", show=True),
        Binding("ctrl+c", "quit_app", "Quit", show=True),
        Binding("question_mark", "open_help", "Help", show=False),
    ]

    def __init__(
        self,
        workspace_dir: Optional[str] = None,
        initial_agent: str = "cyber",
        initial_profile: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.workspace_dir = os.path.abspath(workspace_dir or os.getcwd())
        config_dir = os.path.join(self.workspace_dir, "config")
        self.profiles, default_prof = load_profiles(config_dir)
        self.active_profile_name = initial_profile or default_prof
        if self.active_profile_name not in self.profiles:
            self.active_profile_name = default_prof

        self.agent_mode = initial_agent if initial_agent in ("cyber", "plan") else "cyber"
        self.ollama = OllamaClient()
        self.agent_runner = AgentRunner(self.workspace_dir, self.ollama)
        self.history: List[Message] = []
        self.activity_events: List[ActivityEvent] = []
        self.task_state: Optional[TaskState] = None
        self.session_id = "default"
        self.session_store = SessionStore(self.workspace_dir)
        self._activity_cards: Dict[str, ActivityCard] = {}
        self._activity_groups: Dict[str, ActivityGroup] = {}
        self._is_busy = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="header-bar"):
            yield Static("NEOCYBER", id="header-title")
            yield Static(self._get_header_context(), id="header-context")

        ws_display = self.workspace_dir.replace(os.path.expanduser("~"), "~")
        yield ChatArea(workspace_name=ws_display, id="chat-area")
        yield InputArea(id="prompt-input")
        yield StatusBar(
            initial_agent=self.agent_mode,
            initial_model=self.active_profile_name,
            id="status-bar",
        )

    def _get_header_context(self) -> str:
        ws_disp = self.workspace_dir.replace(os.path.expanduser("~"), "~")
        branch = ""
        try:
            res = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=1,
            )
            if res.returncode == 0 and res.stdout.strip():
                branch = f"  ({res.stdout.strip()})"
        except Exception:
            pass
        return f"{ws_disp}{branch}"

    def on_mount(self) -> None:
        self.query_one(InputArea).focus_input()
        self._restore_session()

    def on_unmount(self) -> None:
        """Never leave a model/tool worker alive when the TUI closes."""
        self.agent_runner.cancel()
        self._is_busy = False

    def _restore_session(self) -> None:
        """Restore inspectable history without replaying commands or model calls."""
        data = self.session_store.load()
        if not data:
            return
        self.session_id = data.get("session_id", self.session_id)
        self.active_profile_name = data.get("model", self.active_profile_name)
        self.agent_mode = data.get("agent", self.agent_mode)
        self.query_one(StatusBar).model_name = self.active_profile_name
        self.query_one(StatusBar).agent_mode = self.agent_mode
        for raw in data.get("messages", []):
            try:
                msg = Message(role=Role(raw["role"]), content=raw["content"], agent=raw.get("agent", "cyber"))
                self.history.append(msg)
                if msg.role == Role.USER:
                    self.query_one(ChatArea).add_user_message(msg.content)
                elif msg.role == Role.ASSISTANT:
                    self.query_one(ChatArea).start_assistant_message(msg.agent).update_content(msg.content)
            except (KeyError, ValueError):
                continue
        for raw in data.get("events", []):
            try:
                event = ActivityEvent.from_dict(raw)
                self.activity_events.append(event)
                self._render_activity(event)
            except TypeError:
                continue

    def _persist_session(self) -> None:
        messages = [{"role": m.role.value, "content": m.content, "agent": m.agent} for m in self.history]
        self.session_store.save(self.session_id, messages, self.activity_events, self.task_state, self.active_profile_name, self.agent_mode)

    def _render_activity(self, event: ActivityEvent) -> None:
        group = self._activity_groups.get(event.task_id)
        if not group:
            group = ActivityGroup(event.task_id, id=f"activity-group-{event.task_id[:10]}")
            self._activity_groups[event.task_id] = group
            self.query_one(ChatArea).mount(group)
        group.upsert(event)
        self.query_one(ChatArea).scroll_end(animate=False)

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_scroll_chat_pageup(self) -> None:
        self.query_one(ChatArea).scroll_page_up(animate=False)

    def action_scroll_chat_pagedown(self) -> None:
        self.query_one(ChatArea).scroll_page_down(animate=False)

    def action_scroll_chat_up(self) -> None:
        self.query_one(ChatArea).scroll_relative(y=-8, animate=False)

    def action_scroll_chat_down(self) -> None:
        self.query_one(ChatArea).scroll_relative(y=8, animate=False)

    def action_scroll_chat_home(self) -> None:
        self.query_one(ChatArea).scroll_home(animate=False)

    def action_scroll_chat_end(self) -> None:
        self.query_one(ChatArea).scroll_end(animate=False)

    def action_open_command_palette(self) -> None:
        def _handle_choice(choice: str | None) -> None:
            if not choice:
                return
            self.call_after_refresh(self._handle_command, choice)

        self.push_screen(CommandPalette(self.profiles), _handle_choice)

    def action_open_model_selector(self) -> None:
        local_models = self.ollama.list_local_models()

        def _on_model_selected(selected: str | None) -> None:
            if selected:
                self.active_profile_name = selected
                self.query_one(StatusBar).model_name = selected
                self.notify(f"Active model set to: {selected}")

        self.push_screen(
            ModelSelector(self.profiles, self.active_profile_name, local_models),
            _on_model_selected,
        )

    def _copy_to_clipboard(self, text: str) -> bool:
        """Try system clipboard tools; return True on success."""
        for cmd in [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
            try:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                p.communicate(text.encode("utf-8"))
                if p.returncode == 0:
                    return True
            except Exception:
                continue
        return False

    def action_copy_last_response(self) -> None:
        """Copies the text of the latest assistant message to system clipboard."""
        for m in reversed(self.history):
            if m.role == Role.ASSISTANT and m.content:
                if self._copy_to_clipboard(m.content):
                    self.notify("Copied last response to clipboard!")
                else:
                    self.notify("Hold Shift to select and copy text with mouse", title="Tip")
                return
        self.notify("No response to copy", severity="warning")

    def action_copy_last_exchange(self) -> None:
        """Ctrl+Shift+C — copies the last user prompt AND AI response together."""
        last_user: Optional[str] = None
        last_ai: Optional[str] = None
        for m in reversed(self.history):
            if last_ai is None and m.role == Role.ASSISTANT and m.content:
                last_ai = m.content
            elif last_user is None and m.role == Role.USER and m.content:
                last_user = m.content
            if last_user is not None and last_ai is not None:
                break
        if last_ai is None:
            self.notify("No conversation to copy", severity="warning")
            return
        parts = []
        if last_user:
            parts.append(f"You:\n{last_user}")
        parts.append(f"NeoCyber:\n{last_ai}")
        combined = "\n\n".join(parts)
        if self._copy_to_clipboard(combined):
            self.notify("Copied last exchange to clipboard! (Ctrl+Shift+C)")
        else:
            self.notify("Clipboard tool not found. Install wl-copy or xclip.", title="Copy failed")

    def action_copy_all_chat(self) -> None:
        """Copy the full conversation history to clipboard."""
        if not self.history:
            self.notify("No conversation to copy", severity="warning")
            return
        lines = []
        for m in self.history:
            prefix = "You" if m.role == Role.USER else f"NeoCyber ({m.agent})"
            lines.append(f"{prefix}:\n{m.content}")
        combined = "\n\n".join(lines)
        if self._copy_to_clipboard(combined):
            self.notify(f"Copied full chat ({len(self.history)} messages) to clipboard!")
        else:
            self.notify("Clipboard tool not found. Install wl-copy or xclip.", title="Copy failed")

    def action_toggle_agent(self) -> None:
        new_mode = "plan" if self.agent_mode == "cyber" else "cyber"
        self.agent_mode = new_mode
        self.query_one(StatusBar).agent_mode = new_mode

    def action_open_help(self) -> None:
        self.push_screen(HelpOverlay())

    def action_cancel_action(self) -> None:
        if self._is_busy:
            self.agent_runner.cancel()
            self._is_busy = False
            self.query_one(StatusBar).status_text = "CANCELLED"
            self.notify("Operation stopped by user", title="Cancelled")

    def action_quit_app(self) -> None:
        self.exit()

    # ── Event Handlers ────────────────────────────────────────────────────────

    @on(InputArea.ScrollChat)
    def handle_scroll_chat(self, event: InputArea.ScrollChat) -> None:
        chat = self.query_one(ChatArea)
        if event.direction == "pageup":
            chat.scroll_page_up(animate=False)
        elif event.direction == "pagedown":
            chat.scroll_page_down(animate=False)
        elif event.direction == "up":
            chat.scroll_relative(y=-8, animate=False)
        elif event.direction == "down":
            chat.scroll_relative(y=8, animate=False)
        elif event.direction == "home":
            chat.scroll_home(animate=False)
        elif event.direction == "end":
            chat.scroll_end(animate=False)

    @on(InputArea.TabPressed)
    def handle_tab_pressed(self) -> None:
        self.action_toggle_agent()

    @on(InputArea.Submitted)
    def handle_prompt_submitted(self, event: InputArea.Submitted) -> None:
        raw_text = event.value.strip()
        if not raw_text:
            return

        # Direct shell command trigger: ! command
        if raw_text.startswith("!"):
            cmd = raw_text[1:].strip()
            self._execute_direct_command(cmd)
            return

        # Slash command
        if raw_text.startswith("/"):
            self._handle_command(raw_text)
            return

        # Regular agent prompt
        self._run_turn(raw_text)

    def _handle_command(self, cmd: str) -> None:
        clean = cmd.strip()
        parts = clean.split(maxsplit=1)
        base = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if base in ("/cyber", "cyber"):
            self.agent_mode = "cyber"
            self.query_one(StatusBar).agent_mode = "cyber"
            self.notify("Switched to Cyber Operator Mode")
        elif base in ("/plan", "plan"):
            self.agent_mode = "plan"
            self.query_one(StatusBar).agent_mode = "plan"
            self.notify("Switched to Plan Mode (Read-Only Threat Modeler)")
        elif base in ("/models", "/model", "models", "model", "/settings", "settings", "switch_model", "switch-model"):
            if arg:
                self.active_profile_name = arg
                self.query_one(StatusBar).model_name = arg
                self.notify(f"Active model set to: {arg}")
            else:
                self.action_open_model_selector()
        elif base in ("/findings", "findings"):
            findings_file = os.path.join(self.workspace_dir, "reports", "findings.json")
            self.push_screen(FindingsOverlay(findings_file))
        elif base in ("/clear", "clear"):
            self.query_one(ChatArea).clear_chat()
            self.history.clear()
            self.notify("Conversation cleared")
        elif base in ("/help", "help", "?"):
            self.action_open_help()
        elif base in ("/quit", "/exit", "quit", "exit"):
            self.exit()
        else:
            self.notify(f"Unknown command: {cmd}", severity="warning")

    # ── Execution Workers ─────────────────────────────────────────────────────

    @work(exclusive=True, thread=True)
    def _execute_direct_command(self, cmd: str) -> None:
        chat = self.query_one(ChatArea)
        status_bar = self.query_one(StatusBar)

        self.call_from_thread(chat.add_user_message, f"! {cmd}")
        self.call_from_thread(setattr, status_bar, "status_text", "EXECUTING")

        card = self.call_from_thread(
            chat.add_tool_card,
            "direct-shell",
            "bash",
            cmd,
        )

        def _on_chunk(chunk: str) -> None:
            self.call_from_thread(card.append_chunk, chunk)

        code, output, duration = self.agent_runner.tools.execute_shell(cmd, on_chunk=_on_chunk)
        self.call_from_thread(card.set_completed, code, output, duration)
        self.call_from_thread(setattr, status_bar, "status_text", "READY")

    @work(exclusive=True)
    async def _run_turn(self, prompt: str) -> None:
        chat = self.query_one(ChatArea)
        status_bar = self.query_one(StatusBar)

        # 1. Mount user prompt line
        chat.add_user_message(prompt)
        status_bar.status_text = "THINKING"
        self._is_busy = True

        profile = self.profiles.get(
            self.active_profile_name,
            ModelProfile(
                name=self.active_profile_name,
                model_id=f"ollama/{self.active_profile_name}",
                ollama_name=self.active_profile_name,
            ),
        )

        current_assistant_msg: Optional[MessageView] = None
        accumulated_text = [""]
        active_card: Optional[ToolExecutionCard] = None

        def _token(token: str) -> None:
            nonlocal current_assistant_msg
            if current_assistant_msg is None:
                current_assistant_msg = chat.start_assistant_message(agent=self.agent_mode)
                status_bar.status_text = "STREAMING"
            accumulated_text[0] += token
            current_assistant_msg.update_content(accumulated_text[0])
            chat.scroll_end(animate=False)

        def _on_tool_start(tool_id: str, cmd: str) -> None:
            nonlocal active_card
            status_bar.status_text = "EXECUTING"
            active_card = chat.add_tool_card(tool_id, "bash", cmd)

        def _on_tool_chunk(tool_id: str, chunk: str) -> None:
            nonlocal active_card
            if active_card is not None:
                active_card.append_chunk(chunk)
                chat.scroll_end(animate=False)

        def _on_tool_complete(tool_id: str, code: int, out: str, dur: float) -> None:
            nonlocal active_card
            status_bar.status_text = "ANALYZING"
            if active_card is not None:
                active_card.set_completed(code, out, dur)
                active_card = None
                chat.scroll_end(animate=False)

        def _on_step_switch() -> None:
            nonlocal current_assistant_msg
            current_assistant_msg = None
            accumulated_text[0] = ""

        try:
            final, events, task = await self.agent_runner.run_task(
                self.agent_mode,
                profile,
                self.history,
                prompt,
                emit=lambda ev: None,
                on_token=_token,
                on_tool_start=_on_tool_start,
                on_tool_chunk=_on_tool_chunk,
                on_tool_complete=_on_tool_complete,
                on_step_switch=_on_step_switch,
            )
            self.task_state = task
            if current_assistant_msg is not None:
                current_assistant_msg.update_content(final)
            else:
                chat.start_assistant_message(agent=self.agent_mode).update_content(final)
            chat.scroll_end(animate=False)
            self.history.extend([Message(Role.USER, prompt), Message(Role.ASSISTANT, final, agent=self.agent_mode)])
            self.history = self.history[-24:]
            self._persist_session()

        except Exception as e:
            if current_assistant_msg is not None:
                current_assistant_msg.update_content(f"Error: {e}")
            else:
                chat.start_assistant_message(agent=self.agent_mode).update_content(f"Error: {e}")
        finally:
            self._is_busy = False
            status_bar.status_text = "READY"
