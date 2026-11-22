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
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from neocyber.components.chat import ChatArea
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
        Binding("pageup", "scroll_chat_pageup", "Scroll Up", show=False),
        Binding("pagedown", "scroll_chat_pagedown", "Scroll Down", show=False),
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

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_scroll_chat_pageup(self) -> None:
        self.query_one(ChatArea).scroll_page_up(animate=False)

    def action_scroll_chat_pagedown(self) -> None:
        self.query_one(ChatArea).scroll_page_down(animate=False)

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

    def action_copy_last_response(self) -> None:
        """Copies the text of the latest assistant message to system clipboard."""
        for m in reversed(self.history):
            if m.role == Role.ASSISTANT and m.content:
                copied = False
                for cmd in [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
                    try:
                        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                        p.communicate(m.content.encode("utf-8"))
                        if p.returncode == 0:
                            copied = True
                            break
                    except Exception:
                        continue
                if copied:
                    self.notify("Copied last response to clipboard!")
                else:
                    self.notify("Hold Shift to select and copy text with mouse", title="Tip")
                return
        self.notify("No response to copy", severity="warning")

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
            chat.scroll_up(animate=False)
        elif event.direction == "down":
            chat.scroll_down(animate=False)

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
        elif base in ("/models", "/model", "models", "model", "/settings", "settings"):
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

        current_prompt = prompt
        accumulated_history = list(self.history)
        max_agent_loops = 5
        loop_count = 0

        try:
            while loop_count < max_agent_loops and self._is_busy:
                loop_count += 1
                status_bar.status_text = "THINKING" if loop_count == 1 else "ANALYZING"

                # Mount assistant message block for this turn
                assistant_view = chat.start_assistant_message(agent=self.agent_mode)
                streamed_tokens = [""]

                def _on_token(token: str) -> None:
                    streamed_tokens[0] += token
                    assistant_view.update_content(streamed_tokens[0])
                    status_bar.status_text = "STREAMING"

                full_resp, _ = await self.agent_runner.execute_turn(
                    agent_name=self.agent_mode,
                    profile=profile,
                    history=accumulated_history,
                    user_prompt=current_prompt,
                    on_token=_on_token,
                    on_tool_start=None,
                    on_tool_chunk=None,
                    on_tool_complete=None,
                )

                # Record turn to accumulated context
                accumulated_history.append(Message(role=Role.USER, content=current_prompt))
                accumulated_history.append(Message(role=Role.ASSISTANT, content=full_resp, agent=self.agent_mode))

                # Check if cyber operator proposed commands
                commands = self.agent_runner.extract_commands(full_resp) if self.agent_mode == "cyber" else []
                if not commands or not self._is_busy:
                    # No commands or completed -> agent finished task!
                    break

                # Execute proposed commands
                tool_results = []
                for idx, cmd in enumerate(commands):
                    if not self._is_busy:
                        break

                    # Only ask permission if command is sensitive (sudo / destructive)
                    is_sensitive = SecurityValidator.is_sensitive_command(cmd)
                    approved = True
                    if is_sensitive:
                        status_bar.status_text = "CONFIRMATION"
                        approved = await self.push_screen_wait(ConfirmCommandModal(cmd))

                    tool_uid = f"tool-{loop_count}-{idx+1}"
                    if approved:
                        status_bar.status_text = f"RUNNING: {cmd.split()[0]}"
                        card = chat.add_tool_card(tool_uid, "bash", cmd)

                        def _chunk_cb(chunk: str):
                            card.append_chunk(chunk)

                        code, output, duration = await asyncio.to_thread(
                            self.agent_runner.tools.execute_shell, cmd, _chunk_cb
                        )
                        card.set_completed(code, output, duration)
                        tool_results.append(f"Command '{cmd}' exit code {code}:\n{output}")
                    else:
                        card = chat.add_tool_card(tool_uid, "bash", cmd)
                        card.set_completed(1, "(Skipped by user)", 0.0)
                        tool_results.append(f"Command '{cmd}' was skipped by the user.")

                # Feed command results back into the agentic loop for next iteration
                if tool_results:
                    combined_results = "\n\n".join(tool_results)
                    current_prompt = (
                        f"[System: Command Output from your execution]:\n{combined_results}\n\n"
                        "Analyze these real output results. If additional commands are needed to complete the user's objective, output the next bash command. "
                        "Otherwise, explain the findings and provide the final answer."
                    )
                else:
                    break

            # Update master conversation history
            self.history = accumulated_history[-12:]

        except Exception as e:
            chat.start_assistant_message(agent=self.agent_mode).update_content(f"Error: {e}")
        finally:
            self._is_busy = False
            status_bar.status_text = "READY"
