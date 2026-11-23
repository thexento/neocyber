"""Stateful iterative agent runner with host awareness, Vigil SOC workflows, and live streaming."""
from __future__ import annotations

import asyncio
import hashlib
import os
import platform
import re
import shutil
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from neocyber.engine.ollama import OllamaClient
from neocyber.engine.tools import SecurityValidator, ToolExecutor
from neocyber.models.activity import ActivityEvent, TaskState
from neocyber.models.message import Message, Role, ToolCall
from neocyber.models.profile import ModelProfile


def get_host_environment() -> Dict[str, Any]:
    """Detect local host OS, distro, kernel, package manager, and installed utilities."""
    distro_name = platform.system()
    try:
        if os.path.isfile("/etc/os-release"):
            with open("/etc/os-release", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        distro_name = line.split("=", 1)[1].strip().strip('"')
                        break
    except Exception:
        pass

    pkg_mgr = "unknown"
    for pm in ["pacman", "apt", "dnf", "zypper", "apk", "brew"]:
        if shutil.which(pm):
            pkg_mgr = pm
            break

    known_tools = ["nmap", "curl", "wget", "wl-copy", "xclip", "xsel", "git", "python3", "bash", "ip", "ss", "nc", "dig"]
    installed = [t for t in known_tools if shutil.which(t)]

    return {
        "os": platform.system(),
        "distro": distro_name,
        "release": platform.release(),
        "arch": platform.machine(),
        "pkg_mgr": pkg_mgr,
        "tools": installed,
    }


def build_cyber_system_prompt(workspace_dir: str) -> str:
    env = get_host_environment()
    tools_str = ", ".join(env["tools"]) if env["tools"] else "standard core utilities"
    install_hint = f"sudo {env['pkg_mgr']} -S <pkg>" if env["pkg_mgr"] == "pacman" else f"sudo {env['pkg_mgr']} install -y <pkg>"

    return f"""You are CYBER — an autonomous SOC penetration tester and cybersecurity operator (inspired by Vigil SOC and LocalHarness architectures).

HOST SYSTEM ENVIRONMENT:
- OS / Distribution: {env['distro']} ({env['os']})
- Kernel: {env['release']} ({env['arch']})
- Package Manager: {env['pkg_mgr']}
- Available Security & Diagnostic Tools: {tools_str}
- Working Directory: {workspace_dir}

OPERATIONAL METHODOLOGY — STEP-BY-STEP SECURITY AUDIT:
When asked to audit or assess a target, work in REAL turns — one test at a time:

1. ANNOUNCE, THEN RUN — ONE COMMAND PER TURN
   - Say exactly one sentence about the test you are running RIGHT NOW (e.g. "First, I'll check whether the host is reachable:").
   - Emit exactly ONE bash block with a single non-destructive diagnostic command.
   - STOP. Do not list upcoming tests, do not simulate results, and do not analyze until the command's real output comes back.

2. ANALYZE REAL OUTPUT ONLY
   - Every analysis must be based on the actual output of the command that just ran.
   - If a command fails or a tool is missing (hping3, nmap, etc.), state that fact and pivot to available alternatives (curl, python3, ss, ip).

3. CONTINUE OR FINISH
   - Based on the real output, run your next single test (one bash block), OR deliver the final report.

4. FINAL REPORT — Security Assessment & Remediation Report (NO bash blocks)
   - List each test actually run and its factual outcome.
   - Group findings by severity: [CRITICAL], [HIGH], [MEDIUM], [LOW], [INFO].
   - End with a remediation playbook: exact code/config fixes for each finding.

RULES:
- Non-destructive diagnostics only: curl, nmap (-sT), ping, ss, ip, python3. No DDoS floods, no exploitation, no brute force, no sudo.
- Test only authorized targets (localhost and in-scope ranges; add other targets to target.txt to authorize them).
- Never run sudo autonomously. For installs/root actions, print the exact command for the user to copy and run manually."""


def build_plan_system_prompt(workspace_dir: str) -> str:
    env = get_host_environment()
    return f"""You are NeoCyber Plan, an expert threat modeler, software architect, and defensive security strategist.
Host: {env['distro']} ({env['release']}). Workspace: {workspace_dir}.
You provide architectural blueprints, threat modeling (STRIDE, MITRE ATT&CK), and defense-in-depth strategies.
You are strictly read-only — provide deep architectural analysis and explanations without emitting executable bash blocks."""


class ExecutionLedger:
    """Stops identical no-progress actions before they reach the shell."""
    def __init__(self) -> None:
        self.entries: List[Dict[str, str]] = []

    @staticmethod
    def normalize(command: str) -> str:
        return " ".join(command.strip().split())

    def get_cached_output(self, command: str, cwd: str) -> Optional[str]:
        normalized = self.normalize(command)
        for e in self.entries:
            if e["command"] == normalized and e["cwd"] == cwd:
                return e.get("raw_output", "")
        return None

    def record(self, command: str, cwd: str, output: str) -> None:
        self.entries.append({
            "command": self.normalize(command),
            "cwd": cwd,
            "raw_output": output,
            "result": hashlib.sha256(output.encode("utf-8", "replace")).hexdigest(),
        })


class AgentRunner:
    def __init__(self, workspace_dir: str, ollama_client: Optional[OllamaClient] = None, max_steps: int = 8) -> None:
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.ollama = ollama_client or OllamaClient()
        self.tools = ToolExecutor(self.workspace_dir)
        self.max_steps = max_steps
        self.is_running = False
        self._active_process: Optional[asyncio.subprocess.Process] = None
        self._seen_findings: set[tuple[str, str]] = set()

    def get_system_prompt(self, agent_name: str) -> str:
        base_prompt = ""
        agent_file = os.path.join(self.workspace_dir, ".opencode", "agents", f"{agent_name}.md")
        if os.path.isfile(agent_file):
            try:
                content = open(agent_file, encoding="utf-8").read()
                parts = content.split("---")
                base_prompt = parts[2].strip() if len(parts) >= 3 else content.strip()
            except OSError:
                pass
        if not base_prompt:
            base_prompt = build_cyber_system_prompt(self.workspace_dir) if agent_name == "cyber" else build_plan_system_prompt(self.workspace_dir)

        # Always inject live host environment telemetry
        env = get_host_environment()
        tools_str = ", ".join(env["tools"]) if env["tools"] else "standard utilities"
        install_hint = f"sudo {env['pkg_mgr']} -S <pkg>" if env["pkg_mgr"] == "pacman" else f"sudo {env['pkg_mgr']} install -y <pkg>"

        host_context = (
            f"\n\nCURRENT HOST ENVIRONMENT:\n"
            f"- OS: {env['distro']} ({env['os']})\n"
            f"- Kernel: {env['release']} ({env['arch']})\n"
            f"- Package Manager: {env['pkg_mgr']} (Install command: `{install_hint}`)\n"
            f"- Available Tools: {tools_str}\n"
            f"- Working Directory: {self.workspace_dir}\n"
        )
        return base_prompt + host_context

    def extract_commands(self, text: str) -> List[str]:
        blocks = re.findall(r"```(?:bash|sh|shell)?\s*[\r\n]+(.*?)```", text, re.DOTALL)
        clean = [b.strip() for b in blocks if b.strip() and not b.lstrip().startswith(("{", "<", "["))]
        # Take ONLY the first command to guarantee step-by-step interactive execution
        return clean[:1]

    def _messages(self, agent: str, history: List[Message], prompt: str, task: TaskState) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.get_system_prompt(agent)}]
        for m in history[-8:]:
            messages.append({"role": m.role.value, "content": m.content[-4000:]})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def _generate(self, agent: str, profile: ModelProfile, history: List[Message], prompt: str, task: TaskState, on_token: Optional[Callable[[str], None]]) -> str:
        availability_check = getattr(self.ollama, "is_available", None)
        if callable(availability_check) and not availability_check():
            return "Local Ollama is currently unavailable. Please ensure Ollama is running (`ollama serve`) and try again."

        response = ""
        try:
            async for token in self.ollama.stream_chat(profile.ollama_name, self._messages(agent, history, prompt, task), profile.temperature):
                if not self.is_running:
                    break
                response += token
                if on_token:
                    on_token(token)
        except Exception as e:
            return f"Error communicating with model: {e}"
        return response

    async def _execute_command(self, command: str, on_chunk: Optional[Callable[[str], None]]) -> Tuple[int, str, float]:
        """Async subprocess runner that streams output reliably without stream reader race conditions."""
        valid, error = self.tools.validator.validate_command(command)
        if not valid:
            return 1, f"ERROR: {error}", 0.0

        started = time.monotonic()
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=self.workspace_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self._active_process = process
            chunks: List[str] = []
            assert process.stdout is not None
            deadline = started + self.tools.command_timeout

            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    process.kill()
                    await process.wait()
                    chunks.append(f"\nERROR: command timed out after {self.tools.command_timeout}s\n")
                    return 124, "".join(chunks), round(time.monotonic() - started, 2)

                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=max(0.05, remaining))
                except asyncio.TimeoutError:
                    if process.returncode is not None:
                        break
                    continue

                if not line:
                    break

                chunk = line.decode("utf-8", "replace")
                if sum(map(len, chunks)) < self.tools.output_limit:
                    chunks.append(chunk)
                if on_chunk:
                    on_chunk(chunk)

            await process.wait()
            self._active_process = None
            return process.returncode or 0, "".join(chunks), round(time.monotonic() - started, 2)
        except asyncio.CancelledError:
            if self._active_process and self._active_process.returncode is None:
                self._active_process.terminate()
            raise
        except Exception as exc:
            return 1, f"Execution failed: {exc}", round(time.monotonic() - started, 2)

    async def execute_turn(self, agent_name: str, profile: ModelProfile, history: List[Message], user_prompt: str, on_token: Optional[Callable[[str], None]] = None, on_tool_start: Optional[Callable[[str, str], None]] = None, on_tool_chunk: Optional[Callable[[str, str], None]] = None, on_tool_complete: Optional[Callable[[str, int, str, float], None]] = None, **_callbacks) -> Tuple[str, List[ToolCall]]:
        """Headless single-task entry: runs the same step-by-step loop as the TUI."""
        self.is_running = True
        try:
            final, _events, _task = await self.run_task(
                agent_name,
                profile,
                history,
                user_prompt,
                emit=None,
                on_token=on_token,
                on_tool_start=on_tool_start,
                on_tool_chunk=on_tool_chunk,
                on_tool_complete=on_tool_complete,
            )
            return final, []
        finally:
            self.is_running = False

    def _extract_target(self, command: str) -> str:
        parts = command.strip().split()
        if not parts:
            return "localhost"
        if parts[0] == "curl":
            m = re.search(r"https?://([^:/ ]+)", command)
            if m:
                return m.group(1)
        if parts[0] == "nmap":
            return parts[-1]
        m = re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", command)
        if m:
            return m.group(0)
        return "localhost"

    def _record_command_findings(self, command: str, output: str, code: int) -> None:
        """Derive lightweight, fact-based findings from REAL command output and persist them."""
        asset = self._extract_target(command)
        low = output.lower()
        first = command.strip().split()[0] if command.strip().split() else ""

        candidates: List[tuple[str, str, str, str, str]] = []

        if code == 127 or "command not found" in low:
            missing = command.strip().split()[0] if command.strip().split() else "tool"
            candidates.append((
                f"Tool not installed: {missing}",
                "Informational",
                asset,
                f"`{command}` could not run because `{missing}` is not installed on this host.",
                f"Install `{missing}` and re-run the test.",
            ))

        if first == "nmap":
            for m in re.finditer(r"^(\d+)/(tcp|udp)\s+open\s+(\S+)", output, re.MULTILINE):
                port, proto, service = m.group(1), m.group(2), m.group(3)
                candidates.append((
                    f"Open port {port}/{proto} on {asset}",
                    "Low",
                    asset,
                    f"Port {port}/{proto} is open running {service}.",
                    f"Confirm this service is intended on {asset}; restrict access with firewall rules if it is not.",
                ))

        if first == "curl":
            m = re.search(r"^HTTP/\d\.\d\s+(\d{3})", output, re.MULTILINE)
            if m:
                status = m.group(1)
                severity = "Informational" if status == "200" else "Low"
                candidates.append((
                    f"HTTP {status} on {asset}",
                    severity,
                    asset,
                    f"{command} returned HTTP {status}.",
                    "Review the exposed endpoint; ensure authentication and authorization are enforced where required.",
                ))
            if any(phrase in low for phrase in ("connection refused", "couldn't connect", "failed to connect", "no route to host")):
                candidates.append((
                    f"No reachable service on {asset}",
                    "Informational",
                    asset,
                    f"{command} could not connect to {asset}.",
                    "Confirm the host and port are reachable and the service is running.",
                ))

        for title, severity, finding_asset, description, remediation in candidates:
            if (title, finding_asset) in self._seen_findings:
                continue
            self._seen_findings.add((title, finding_asset))
            try:
                evidence_file = self.tools.persist_evidence("shell", output)
            except Exception:
                evidence_file = ""
            self.tools.record_finding(title, severity, finding_asset, description, evidence_file=evidence_file, remediation=remediation)

    async def run_task(
        self,
        agent: str,
        profile: ModelProfile,
        history: List[Message],
        objective: str,
        emit: Optional[Callable[[ActivityEvent], None]] = None,
        on_token: Optional[Callable[[str], None]] = None,
        on_command_chunk: Optional[Callable[[str, str], None]] = None,
        on_tool_start: Optional[Callable[[str, str], None]] = None,
        on_tool_chunk: Optional[Callable[[str, str], None]] = None,
        on_tool_complete: Optional[Callable[[str, int, str, float], None]] = None,
        on_step_switch: Optional[Callable[[], None]] = None,
    ) -> Tuple[str, List[ActivityEvent], TaskState]:
        self.is_running = True
        task = TaskState(
            objective=objective,
            plan=["Analyze request", "Execute diagnostic tests step-by-step", "Synthesize final findings"],
            pending=["Execute diagnostic tests step-by-step", "Synthesize final findings"],
            current_task="Analyze request",
            completion_criteria=["Factual, complete response delivered"],
        )
        events: List[ActivityEvent] = []
        ledger = ExecutionLedger()
        working_history = list(history)

        def publish(event: ActivityEvent) -> None:
            events.append(event)
            if emit:
                emit(event)

        final_response = ""
        try:
            current_prompt = objective

            for step in range(self.max_steps):
                if not self.is_running:
                    task.completion_reason = "Cancelled by user."
                    return "Operation cancelled by user.", events, task

                started = time.monotonic()
                response = await self._generate(agent, profile, working_history, current_prompt, task, on_token)
                commands = self.extract_commands(response) if agent == "cyber" else []
                prose_summary = re.sub(r"```.*?```", "", response, flags=re.DOTALL).strip()

                # If no commands proposed, the model answered directly or completed its final report!
                if not commands:
                    final_response = response
                    task.completion_reason = "Completed direct response."
                    break

                # Execute the proposed single command
                executed_any = False
                observations: List[str] = []
                duplicates: List[str] = []

                for command in commands:
                    # Filter sudo/destructive/flood commands — do not run unattended
                    if SecurityValidator.is_sensitive_command(command):
                        publish(ActivityEvent("error", f"Requires sudo: {command}", task.task_id, "failed"))
                        final_response = (
                            f"{prose_summary}\n\n"
                            f"This operation requires root privileges. Run this in your terminal:\n"
                            f"```bash\n{command}\n```"
                        )
                        return final_response, events, task

                    # Check if already ran — supply cached output and continue rather than aborting
                    cached_out = ledger.get_cached_output(command, self.workspace_dir)
                    if cached_out is not None:
                        duplicates.append(command)
                        publish(ActivityEvent("warning", "Skipped duplicate command", task.task_id, "skipped", {"command": command}))
                        obs = f"$ {command}\n(already executed — cached output)\n{cached_out[-2500:]}"
                        observations.append(obs)
                        task.observations.append(obs)
                        continue

                    # Execute live command
                    event = ActivityEvent("command", command, task.task_id, "running", {"command": command, "cwd": self.workspace_dir})
                    publish(event)
                    executed_any = True
                    task.tools_used.append("shell")

                    if on_tool_start:
                        on_tool_start(event.event_id, command)

                    def chunk_cb(chunk: str) -> None:
                        if on_tool_chunk:
                            on_tool_chunk(event.event_id, chunk)
                        elif on_command_chunk:
                            on_command_chunk(event.event_id, chunk)

                    code, output, duration = await self._execute_command(command, chunk_cb)
                    event.status = "completed" if code == 0 else "failed"
                    event.duration = duration
                    event.result = output
                    ledger.record(command, self.workspace_dir, output)

                    if on_tool_complete:
                        on_tool_complete(event.event_id, code, output, duration)

                    # Auto-record concrete findings from the REAL tool output
                    self._record_command_findings(command, output, code)

                    obs = f"$ {command}\n(exit {code})\n{output[-2500:]}"
                    observations.append(obs)
                    task.observations.append(obs)
                    if emit:
                        emit(event)

                if not executed_any:
                    # The model repeated earlier commands or could not propose anything new:
                    # close the turn with what we know instead of spinning forever.
                    final_parts: List[str] = []
                    if prose_summary:
                        final_parts.append(prose_summary)
                    if duplicates:
                        final_parts.append("Note: duplicates — already executed, skipped: " + ", ".join(duplicates))
                    if observations:
                        final_parts.append("Observations so far:\n" + "\n".join(observations[-6:]))
                    final_response = "\n\n".join(final_parts) if final_parts else (prose_summary or response)
                    task.completion_reason = "No new commands executed."
                    break

                # Signal UI that tool execution finished and next step will start
                if on_step_switch:
                    on_step_switch()

                working_history.extend([
                    Message(Role.USER, current_prompt),
                    Message(Role.ASSISTANT, response, agent=agent),
                ])

                # Feed observation back and prompt for the next step or final report
                if step < self.max_steps - 2:
                    current_prompt = (
                        f"Result of your last test:\n"
                        f"{''.join(observations)}\n\n"
                        f"INSTRUCTIONS FOR NEXT TURN:\n"
                        f"1. Briefly explain what that output shows.\n"
                        f"2. Run your next single diagnostic test — exactly ONE bash block (e.g. another curl probe, nmap port check, header check, input-validation probe).\n"
                        f"3. If testing is complete, give the final Security Assessment & Remediation Report with severity ratings [CRITICAL/HIGH/MEDIUM/LOW/INFO] and remediation steps. NO bash blocks in the final report."
                    )
                else:
                    current_prompt = (
                        f"Result of your last test:\n"
                        f"{''.join(observations)}\n\n"
                        f"FINAL TURN — give your complete Security Assessment & Remediation Report now:\n"
                        f"- Summarize each test run and its factual outcome.\n"
                        f"- Group findings by severity: [CRITICAL], [HIGH], [MEDIUM], [LOW], [INFO].\n"
                        f"- Provide a remediation playbook with exact code/configuration fixes.\n"
                        f"Do NOT output any bash blocks."
                    )

            if not final_response:
                if task.observations:
                    final_response = f"Findings from executed diagnostic actions:\n\n" + "\n\n".join(task.observations)
                else:
                    final_response = prose_summary or response

            return final_response, events, task

        except Exception as exc:
            task.errors.append(str(exc))
            publish(ActivityEvent("error", f"Agent error: {exc}", task.task_id, "failed"))
            return f"Agent error: {exc}", events, task
        finally:
            self.is_running = False

    def cancel(self) -> None:
        self.is_running = False
        if self._active_process and self._active_process.returncode is None:
            self._active_process.terminate()
