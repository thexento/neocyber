"""Deterministic cybersecurity tools, shell runner, and file operations with validation."""
from __future__ import annotations

import difflib
import json
import os
import re
import shlex
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple


class SecurityValidator:
    """Validates targets and commands against safety guardrails."""

    def __init__(self, workspace_dir: Optional[str] = None, allowed_targets: Optional[List[str]] = None) -> None:
        self.allowed_targets = allowed_targets or [
            "127.0.0.1",
            "localhost",
            "10.",
            "192.168.",
            "172.16.",
            "172.17.",
            "172.18.",
            "172.19.",
            "172.20.",
            "172.21.",
            "172.22.",
            "172.23.",
            "172.24.",
            "172.25.",
            "172.26.",
            "172.27.",
            "172.28.",
            "172.29.",
            "172.30.",
            "172.31.",
        ]
        self.workspace_dir = workspace_dir
        self._extra_targets: List[str] = []
        if workspace_dir:
            target_file = os.path.join(workspace_dir, "target.txt")
            if os.path.isfile(target_file):
                try:
                    with open(target_file, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                self._extra_targets.append(line)
                except OSError:
                    pass

    def validate_target(self, target: str) -> bool:
        if not target:
            return False
        cleaned = re.sub(r"^[a-zA-Z]+://", "", target)
        cleaned = re.sub(r":[0-9]+/?$", "", cleaned)
        cleaned = cleaned.split("/")[0]

        if "unauthorized" in cleaned.lower():
            return False

        # Allow localhost and valid IPv4 target addresses
        if cleaned in ("localhost", "127.0.0.1") or re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", cleaned):
            return True

        for allowed in self.allowed_targets:
            if cleaned.startswith(allowed) or cleaned == allowed:
                return True

        # Workspace target.txt — user-authorized targets (e.g. a target they own)
        for extra in self._extra_targets:
            if cleaned == extra or cleaned.startswith(extra):
                return True
        return False

    @staticmethod
    def is_sensitive_command(cmd: str) -> bool:
        """Check if command requires explicit user confirmation (sudo, destructive, or denial-of-service tooling)."""
        stripped = cmd.strip()
        # Sudo or root elevation
        if re.search(r"(?:^|[;&|\s])sudo(?:\s|$)|(?:^|[;&|\s])doas(?:\s|$)|(?:^|[;&|\s])su(?:\s|$)", stripped):
            return True
        # Destructive file/disk commands
        if re.search(r"rm\s+-(?:r|f|rf|fr)\s+|mkfs|dd\s+if=|fdisk|parted", stripped):
            return True
        # Dangerous system control
        if re.search(r"(?:shutdown|reboot|poweroff|init\s+0|systemctl\s+(?:stop|disable|poweroff))", stripped):
            return True
        # Denial-of-service / flood tooling — never run autonomously
        if re.search(r"\b(hping3|nping|goldeneye|slowloris|--flood)\b", stripped):
            return True
        return False

    def validate_command(self, cmd: str) -> Tuple[bool, Optional[str]]:
        # Destructive system commands
        if re.search(r"rm\s+-(r|f|rf|fr)\s+/(?:\s|$)|mkfs|dd\s+if=|:()\s*{\s*:|:&\s*};\s*:", cmd):
            return False, "Destructive system command rejected by security policy."
        # Full internet scan
        if re.search(r"nmap\s+-[A-Za-z0-9]*\s+0\.0\.0\.0/0", cmd):
            return False, "Full internet range scan prohibited."
        return True, None


class ToolExecutor:
    """Executes tools with context management, diff generation, and evidence capture."""

    def __init__(
        self,
        workspace_dir: str,
        evidence_dir: Optional[str] = None,
        findings_file: Optional[str] = None,
        summarize_threshold: int = 30,
        command_timeout: int = 60,
        output_limit: int = 100_000,
    ) -> None:
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.evidence_dir = evidence_dir or os.path.join(self.workspace_dir, "reports", "evidence")
        self.findings_file = findings_file or os.path.join(self.workspace_dir, "reports", "findings.json")
        self.summarize_threshold = summarize_threshold
        self.command_timeout = command_timeout
        self.output_limit = output_limit
        self.validator = SecurityValidator(workspace_dir=workspace_dir)
        os.makedirs(self.evidence_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.findings_file), exist_ok=True)

    def persist_evidence(self, tool_name: str, raw_content: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.evidence_dir, f"{tool_name}_{ts}.log")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(raw_content)
        return filepath

    def execute_shell(
        self,
        cmd: str,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> Tuple[int, str, float]:
        """Runs a shell command in workspace_dir, streaming chunks if callback provided."""
        valid, err_msg = self.validator.validate_command(cmd)
        if not valid:
            return 1, f"ERROR: {err_msg}", 0.0

        start_time = time.time()
        try:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                cwd=self.workspace_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            output_lines = []
            if proc.stdout:
                for line in iter(proc.stdout.readline, ""):
                    if sum(map(len, output_lines)) < self.output_limit:
                        output_lines.append(line)
                    if on_chunk:
                        on_chunk(line)
                proc.stdout.close()
            try:
                proc.wait(timeout=self.command_timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                output_lines.append(f"\nERROR: command timed out after {self.command_timeout}s\n")
            duration = round(time.time() - start_time, 2)
            full_output = "".join(output_lines)
            return proc.returncode, full_output, duration
        except Exception as e:
            duration = round(time.time() - start_time, 2)
            return 1, f"Execution failed: {str(e)}", duration

    def read_file(self, rel_path: str) -> Tuple[bool, str]:
        path = os.path.abspath(os.path.join(self.workspace_dir, rel_path))
        if os.path.commonpath([self.workspace_dir, path]) != self.workspace_dir:
            return False, "Failed to read file: path is outside workspace"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return True, f.read()
        except Exception as e:
            return False, f"Failed to read file: {e}"

    def write_file(self, rel_path: str, content: str) -> Tuple[bool, str]:
        path = os.path.abspath(os.path.join(self.workspace_dir, rel_path))
        if os.path.commonpath([self.workspace_dir, path]) != self.workspace_dir:
            return False, "Failed to write file: path is outside workspace"
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, f"Successfully wrote {len(content)} bytes to {rel_path}"
        except Exception as e:
            return False, f"Failed to write file: {e}"

    def edit_file(self, rel_path: str, target: str, replacement: str) -> Tuple[bool, str, str]:
        """Edits file by replacing target with replacement. Returns (success, diff_or_error, diff)."""
        path = os.path.abspath(os.path.join(self.workspace_dir, rel_path))
        if os.path.commonpath([self.workspace_dir, path]) != self.workspace_dir:
            return False, "File is outside workspace", ""
        if not os.path.isfile(path):
            return False, f"File does not exist: {rel_path}", ""

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                original = f.read()

            if target not in original:
                return False, f"Target string not found in {rel_path}", ""

            new_content = original.replace(target, replacement, 1)

            # Generate unified diff
            orig_lines = original.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)
            diff = "".join(
                difflib.unified_diff(
                    orig_lines,
                    new_lines,
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}",
                )
            )

            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return True, f"Successfully edited {rel_path}", diff
        except Exception as e:
            return False, f"Failed to edit file: {e}", ""

    def execute_nmap(self, target: str, ports: str = "1-1000", scan_type: str = "-sT") -> Tuple[int, str, float]:
        if not self.validator.validate_target(target):
            return 1, f"ERROR: Target '{target}' is outside authorized scope.", 0.0

        cmd = f"nmap {scan_type} -p {ports} -T4 --open {target}"
        code, raw_out, dur = self.execute_shell(cmd)
        evidence_file = self.persist_evidence("nmap", raw_out)

        # Context reduction for small models
        open_services = re.findall(r"^(\d+/(?:tcp|udp)\s+open\s+\S+)", raw_out, re.MULTILINE)
        summary = {
            "tool": "nmap",
            "target": target,
            "status": "completed" if code == 0 else "failed",
            "open_services": open_services if open_services else "No open ports discovered",
            "evidence_file": evidence_file,
            "note": "Raw scan output saved in evidence_file",
        }
        return code, json.dumps(summary, indent=2), dur

    def execute_curl(self, url: str, method: str = "GET") -> Tuple[int, str, float]:
        if not self.validator.validate_target(url):
            return 1, f"ERROR: Target URL '{url}' is outside authorized scope.", 0.0

        # Bounded redirect following is an observation, never a vulnerability claim.
        cmd = f"curl -s -S -i -k -L --max-redirs 5 --connect-timeout 10 --max-time 30 -X {method} {shlex.quote(url)}"
        code, raw_out, dur = self.execute_shell(cmd)
        evidence_file = self.persist_evidence("curl", raw_out)

        lines = raw_out.splitlines()
        status_line = lines[0] if lines else "None"
        server_line = next((l for l in lines if l.lower().startswith("server:")), "None")
        locations = [l for l in lines if l.lower().startswith("location:")]
        summary = {
            "tool": "curl",
            "url": url,
            "status": status_line,
            "server": server_line,
            "redirects": locations,
            "evidence_file": evidence_file,
            "snippet": "\n".join(lines[:10]),
        }
        return code, json.dumps(summary, indent=2), dur

    def record_finding(
        self,
        title: str,
        severity: str,
        asset: str,
        description: str,
        evidence_file: str = "",
        remediation: str = "",
    ) -> Dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        finding_id = f"FIND-{now_utc.strftime('%Y%m%d%H%M%S')}"
        finding = {
            "id": finding_id,
            "title": title,
            "severity": severity.upper(),
            "asset": asset,
            "description": description,
            "evidence_file": evidence_file,
            "remediation": remediation,
            "timestamp": now_utc.isoformat(),
            "verified": True,
        }

        # Update JSON file
        findings: List[dict] = []
        if os.path.isfile(self.findings_file):
            try:
                with open(self.findings_file, "r", encoding="utf-8") as f:
                    findings = json.load(f)
            except Exception:
                findings = []

        findings.append(finding)
        with open(self.findings_file, "w", encoding="utf-8") as f:
            json.dump(findings, f, indent=2)

        return finding
