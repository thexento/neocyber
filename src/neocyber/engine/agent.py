"""Agent runner for NeoCyber (Cyber & Plan personas) with autonomous execution."""
from __future__ import annotations

import os
import re
import uuid
from typing import AsyncGenerator, Callable, Dict, List, Optional, Tuple

from neocyber.engine.ollama import OllamaClient
from neocyber.engine.tools import ToolExecutor
from neocyber.models.message import Message, Role, ToolCall
from neocyber.models.profile import ModelProfile


CYBER_SYSTEM_PROMPT = """You are CYBER — an elite, autonomous cybersecurity operator and agent with direct terminal execution access.

CRITICAL RULES OF ENGAGEMENT:
1. YOU ARE THE OPERATOR, NOT A TUTORIAL CHATBOT.
   - When the user gives you a task, objective, or instruction (e.g. find proxies, test a service, fetch an API, scan ports, audit a file, inspect system info):
     DO NOT explain how the user can do it.
     DO NOT output tutorial text or pseudo-code with fake placeholders like 'example.com' or 'proxy1.example.com'.
     DO NOT say "Here is a script you can run".
   - YOU MUST EXECUTE IT YOURSELF IMMEDIATELY.
2. EXECUTION VIA BASH:
   - Output real, working bash commands inside a ```bash code block.
   - Think silently or in 1 brief sentence (e.g. "Fetching public proxy list to test connectivity..."), then immediately output the executable ```bash block.
   - Use real public endpoints or real local tools (e.g. fetch from real public proxy lists, test connectivity with curl, fetch the target API).
3. MULTI-STEP REASONING:
   - You act in an automated agent loop:
     1. Run discovery / initial execution command.
     2. You will receive the actual command output from the terminal.
     3. Analyze the real output and immediately output the next command to proceed.
     4. Repeat until the user's objective is completed, then report the final working result.
4. CASUAL CONVERSATION:
   - Only if the user is merely greeting you ("hey", "hello", "what can you do?") should you reply conversationally without executing tools.
   - For ANY technical request, task, or action: EXECUTE IT.
"""

PLAN_SYSTEM_PROMPT = """You are PLAN — an elite cybersecurity architect and threat modeler.

Behavior Guidelines:
1. Converse naturally, intelligently, and concisely.
2. Focus on architecture analysis, attack surface mapping, threat modeling, and defensive engineering.
3. You are read-only: discuss strategies and write proposed commands for the user to review, but never execute them.
4. Use clean standard Markdown without rigid repetitive headers.
"""


class AgentRunner:
    """Manages agent conversations, streaming, and tool execution."""

    def __init__(self, workspace_dir: str, ollama_client: Optional[OllamaClient] = None) -> None:
        self.workspace_dir = workspace_dir
        self.ollama = ollama_client or OllamaClient()
        self.tools = ToolExecutor(workspace_dir)
        self.is_running = False

    def get_system_prompt(self, agent_name: str) -> str:
        agent_file = os.path.join(self.workspace_dir, ".opencode", "agents", f"{agent_name}.md")
        if os.path.isfile(agent_file):
            try:
                with open(agent_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    parts = content.split("---")
                    if len(parts) >= 3:
                        return parts[2].strip()
                    return content.strip()
            except Exception:
                pass
        return CYBER_SYSTEM_PROMPT if agent_name == "cyber" else PLAN_SYSTEM_PROMPT

    def extract_commands(self, text: str) -> List[str]:
        """Extracts executable bash/sh command blocks from markdown."""
        commands = []
        pattern = r"```(?:bash|sh|shell)?\s*[\r\n]+(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        for block in matches:
            clean = block.strip()
            # Filter out non-bash or empty blocks (like json or html snippets)
            if clean and not clean.startswith(("{", "<", "[")):
                commands.append(clean)
        return commands

    async def execute_turn(
        self,
        agent_name: str,
        profile: ModelProfile,
        history: List[Message],
        user_prompt: str,
        on_token: Optional[Callable[[str], None]] = None,
        on_tool_start: Optional[Callable[[str, str], None]] = None,
        on_tool_chunk: Optional[Callable[[str, str], None]] = None,
        on_tool_complete: Optional[Callable[[str, int, str, float], None]] = None,
    ) -> Tuple[str, List[ToolCall]]:
        """Executes one full conversation turn with token streaming and tool runs."""
        self.is_running = True
        system_prompt = self.get_system_prompt(agent_name)

        messages = [{"role": "system", "content": system_prompt}]
        for m in history:
            messages.append({"role": m.role.value, "content": m.content})
        messages.append({"role": "user", "content": user_prompt})

        full_response = ""
        try:
            async for token in self.ollama.stream_chat(
                model=profile.ollama_name,
                messages=messages,
                temperature=profile.temperature,
            ):
                if not self.is_running:
                    break
                full_response += token
                if on_token:
                    on_token(token)
        except Exception as e:
            full_response = f"Error during model generation: {e}"
            if on_token:
                on_token(f"\n[Error: {e}]")

        tool_calls: List[ToolCall] = []

        # If agent is CYBER, extract commands and execute them with globally unique tool IDs
        if agent_name == "cyber" and self.is_running:
            commands = self.extract_commands(full_response)
            for cmd in commands:
                tool_uid = f"tool-{uuid.uuid4().hex[:8]}"
                tc = ToolCall(
                    id=tool_uid,
                    name="bash",
                    arguments={"command": cmd},
                    status="running",
                )
                tool_calls.append(tc)
                if on_tool_start:
                    on_tool_start(tool_uid, cmd)

                def _chunk_cb(chunk: str):
                    if on_tool_chunk:
                        on_tool_chunk(tool_uid, chunk)

                code, output, duration = self.tools.execute_shell(cmd, on_chunk=_chunk_cb)
                tc.status = "completed" if code == 0 else "failed"
                tc.output = output
                tc.duration = duration
                tc.exit_code = code

                if on_tool_complete:
                    on_tool_complete(tool_uid, code, output, duration)

        self.is_running = False
        return full_response, tool_calls

    def cancel(self) -> None:
        self.is_running = False
