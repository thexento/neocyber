"""Main NeoCyber Textual Application matching OpenCode's visual and UX design."""
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
from textual.widgets import Static

from neocyber.components.chat import ChatArea
from neocyber.components.command_palette import CommandPalette
from neocyber.components.findings_view import FindingsOverlay
from neocyber.components.help_overlay import HelpOverlay
from neocyber.components.input_area import InputArea
from neocyber.components.model_selector import ModelSelector
from neocyber.components.status_bar import StatusBar
from neocyber.engine.agent import AgentRunner
from neocyber.engine.ollama import OllamaClient
from neocyber.models.message import Message, Role
from neocyber.models.profile import ModelProfile, load_profiles


class NeoCyberApp(App[None]):
    """NeoCyber Terminal Application."""

    CSS_PATH = "app.tcss"
    TITLE = "NeoCyber"
    SUB_TITLE = "Cybersecurity AI Harness"

    BINDINGS = [
        Binding("ctrl+p", "open_command_palette", "Commands", show=True),
        Binding("tab", "toggle_agent", "Switch Agent", show=True),
        Binding("escape", "cancel_action", "Cancel / Stop", show=True),
        Binding("f2", "cycle_model", "Cycle Model", show=False),
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
        self._is_busy = False

    def compose(self) -> ComposeResult:
        # Header bar
        with Horizontal(id="header-bar"):
            yield Static("NEOCYBER", id="header-title")
            yield Static(self._get_header_context(), id="header-context")

        # Chat conversation area
        ws_display = self.workspace_dir.replace(os.path.expanduser("~"), "~")
        yield ChatArea(workspace_name=ws_display, id="chat-area")

        # Prompt input area
        yield InputArea(id="prompt-input")

        # Bottom status bar
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

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_open_command_palette(self) -> None:
        def _handle_choice(choice: str | None) -> None:
            if not choice:
                return
            self._handle_command(choice)

        self.push_screen(CommandPalette(self.profiles), _handle_choice)

    def action_toggle_agent(self) -> None:
        new_mode = "plan" if self.agent_mode == "cyber" else "cyber"
        self.agent_mode = new_mode
        self.query_one(StatusBar).agent_mode = new_mode

    def action_open_help(self) -> None:
        self.push_screen(HelpOverlay())

    def action_cycle_model(self) -> None:
        keys = list(self.profiles.keys())
        if not keys:
            return
        idx = keys.index(self.active_profile_name) if self.active_profile_name in keys else -1
        next_idx = (idx + 1) % len(keys)
        self.active_profile_name = keys[next_idx]
        self.query_one(StatusBar).model_name = self.active_profile_name

    def action_cancel_action(self) -> None:
        if self._is_busy:
            self.agent_runner.cancel()
            self._is_busy = False
            self.query_one(StatusBar).status_text = "CANCELLED"
            self.notify("Operation stopped by user", title="Cancelled")

    def action_quit_app(self) -> None:
        self.exit()

    # ── Event Handlers ────────────────────────────────────────────────────────

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
        elif base in ("/models", "/model", "models", "model"):
            if arg:
                self.active_profile_name = arg
                self.query_one(StatusBar).model_name = arg
                self.notify(f"Active model profile set to: {arg}")
            else:
                local_models = self.ollama.list_local_models()

                def _on_model_selected(selected: str | None) -> None:
                    if selected:
                        self.active_profile_name = selected
                        self.query_one(StatusBar).model_name = selected
                        self.notify(f"Active model profile set to: {selected}")

                self.push_screen(
                    ModelSelector(self.profiles, self.active_profile_name, local_models),
                    _on_model_selected,
                )
        elif clean in ("/findings", "findings"):
            findings_file = os.path.join(self.workspace_dir, "reports", "findings.json")
            self.push_screen(FindingsOverlay(findings_file))
        elif clean in ("/clear", "clear"):
            self.query_one(ChatArea).clear_chat()
            self.history.clear()
            self.notify("Conversation cleared")
        elif clean in ("/help", "help", "?"):
            self.action_open_help()
        elif clean in ("/quit", "/exit", "quit", "exit"):
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
            "direct-1",
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

        # 1. Mount user message
        chat.add_user_message(prompt)
        status_bar.status_text = "THINKING"
        self._is_busy = True

        # 2. Mount assistant message
        assistant_view = chat.start_assistant_message(agent=self.agent_mode)

        profile = self.profiles.get(
            self.active_profile_name,
            ModelProfile(
                name=self.active_profile_name,
                model_id=f"ollama/{self.active_profile_name}",
                ollama_name=self.active_profile_name,
            ),
        )

        streamed_response = [""]
        tool_cards: Dict[str, Any] = {}

        def _on_token(token: str) -> None:
            streamed_response[0] += token
            assistant_view.update_content(streamed_response[0])
            status_bar.status_text = "STREAMING"

        def _on_tool_start(tool_id: str, cmd: str) -> None:
            status_bar.status_text = "RUNNING TOOL"
            card = chat.add_tool_card(tool_id, "bash", cmd)
            tool_cards[tool_id] = card

        def _on_tool_chunk(tool_id: str, chunk: str) -> None:
            card = tool_cards.get(tool_id)
            if card:
                card.append_chunk(chunk)

        def _on_tool_complete(tool_id: str, code: int, output: str, dur: float) -> None:
            card = tool_cards.get(tool_id)
            if card:
                card.set_completed(code, output, dur)

        try:
            full_resp, tool_calls = await self.agent_runner.execute_turn(
                agent_name=self.agent_mode,
                profile=profile,
                history=self.history,
                user_prompt=prompt,
                on_token=_on_token,
                on_tool_start=_on_tool_start,
                on_tool_chunk=_on_tool_chunk,
                on_tool_complete=_on_tool_complete,
            )

            # Record to history
            self.history.append(Message(role=Role.USER, content=prompt))
            self.history.append(
                Message(
                    role=Role.ASSISTANT,
                    content=full_resp,
                    agent=self.agent_mode,
                    tool_calls=tool_calls,
                )
            )
            # Cap history window
            if len(self.history) > 10:
                self.history = self.history[-10:]

        except Exception as e:
            assistant_view.update_content(f"Error executing agent: {e}")
        finally:
            self._is_busy = False
            status_bar.status_text = "READY"
