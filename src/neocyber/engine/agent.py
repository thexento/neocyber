"""Agent runner for NeoCyber (Cyber & Plan personas) with tool coordination."""
from __future__ import annotations

import os
import re
from typing import AsyncGenerator, Callable, Dict, List, Optional, Tuple

from neocyber.engine.ollama import OllamaClient
from neocyber.engine.tools import ToolExecutor
from neocyber.models.message import Message, Role, ToolCall
from neocyber.models.profile import ModelProfile


CYBER_SYSTEM_PROMPT = """You are CYBER — an elite offensive/defensive cybersecurity operator.
Scope: Authorized targets only (CTFs, lab targets, owned infrastructure, audits).
Mindset: Respond with precise, actionable commands. No theory walls or padding.

Format every response as:
## Objective
[One clear line defining current task]

## Action
[Explain action and execute bash/tools inside ```bash code blocks]

## Result
[Summary of output or findings]

## Next
[Immediate next step in the attack/audit chain]
"""

PLAN_SYSTEM_PROMPT = """You are PLAN — an elite read-only cybersecurity planner.
Scope: Threat modeling, attack surface mapping, exploit chains.
Rule: You NEVER execute commands or modify files. Read and plan only.

Format every response as:
## Objective
[Planning goal]

## Threat Model / Attack Chain
[Structured steps: Recon -> Enum -> Exploit -> Escalation]

## Action Plan for CYBER
[Exact commands and payloads for the operator to run]
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
        """Extracts bash/sh commands from markdown code blocks."""
        commands = []
        pattern = r"```(?:bash|sh|shell)\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        for block in matches:
            lines = [l.strip() for l in block.splitlines() if l.strip() and not l.strip().startswith("#")]
            if lines:
                commands.append(" && ".join(lines))
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

        # If agent is CYBER, extract commands and execute them
        if agent_name == "cyber" and self.is_running:
            commands = self.extract_commands(full_response)
            for idx, cmd in enumerate(commands):
                tool_id = f"tool-{idx+1}"
                tc = ToolCall(
                    id=tool_id,
                    name="bash",
                    arguments={"command": cmd},
                    status="running",
                )
                tool_calls.append(tc)
                if on_tool_start:
                    on_tool_start(tool_id, cmd)

                def _chunk_cb(chunk: str):
                    if on_tool_chunk:
                        on_tool_chunk(tool_id, chunk)

                code, output, duration = self.tools.execute_shell(cmd, on_chunk=_chunk_cb)
                tc.status = "completed" if code == 0 else "failed"
                tc.output = output
                tc.duration = duration
                tc.exit_code = code

                if on_tool_complete:
                    on_tool_complete(tool_id, code, output, duration)

        self.is_running = False
        return full_response, tool_calls

    def cancel(self) -> None:
        self.is_running = False
