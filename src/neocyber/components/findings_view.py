"""Security findings dashboard modal."""
from __future__ import annotations

import json
import os
from typing import List

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static


class FindingsOverlay(ModalScreen[None]):
    """Displays identified security findings from reports/findings.json."""

    DEFAULT_CSS = """
    FindingsOverlay {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #findings-container {
        width: 74;
        max-width: 90%;
        height: auto;
        max-height: 24;
        background: #18181b;
        border: round #f59e0b;
        padding: 1 2;
    }
    #findings-title {
        color: #f59e0b;
        text-style: bold;
        margin-bottom: 1;
    }
    #findings-content {
        height: 16;
        overflow-y: auto;
    }
    #findings-hint {
        color: #71717a;
        margin-top: 1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close"),
        Binding("enter", "dismiss_modal", "Close"),
        Binding("q", "dismiss_modal", "Close"),
    ]

    def __init__(self, findings_path: str) -> None:
        super().__init__()
        self.findings_path = findings_path

    def compose(self) -> ComposeResult:
        with Vertical(id="findings-container"):
            yield Static("❯ SECURITY FINDINGS DASHBOARD", id="findings-title")
            yield Static(self._render_findings(), id="findings-content")
            yield Static("Press Esc, Enter, or Q to close", id="findings-hint")

    def _render_findings(self) -> Text:
        if not os.path.isfile(self.findings_path):
            return Text("No findings recorded yet. Run security scans to discover vulnerabilities.", style="dim")

        try:
            with open(self.findings_path, "r", encoding="utf-8") as f:
                findings: List[dict] = json.load(f)
        except Exception as e:
            return Text(f"Failed to read findings: {e}", style="#ef4444")

        if not findings:
            return Text("No security findings recorded in current workspace.", style="dim")

        rich_text = Text()
        rich_text.append(f"Discovered {len(findings)} Security Finding(s):\n\n", style="bold #f4f4f5")

        for f in findings:
            sev = f.get("severity", "INFO").upper()
            title = f.get("title", "Untitled Finding")
            asset = f.get("asset", "unknown")
            desc = f.get("description", "")
            evidence = f.get("evidence_file", "")

            sev_style = "bold #ef4444" if sev in ("CRITICAL", "HIGH") else ("bold #f59e0b" if sev == "MEDIUM" else "bold #10b981")

            rich_text.append(f"[{sev:<8}] ", style=sev_style)
            rich_text.append(f"{title} ", style="bold #f4f4f5")
            rich_text.append(f"({asset})\n", style="dim #71717a")
            if desc:
                rich_text.append(f"  Description: {desc}\n", style="#a1a1aa")
            if evidence:
                rich_text.append(f"  Evidence: {evidence}\n", style="dim #38bdf8")
            rich_text.append("\n")

        return rich_text

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)
