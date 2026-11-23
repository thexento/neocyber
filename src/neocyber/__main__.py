"""Entrypoint for NeoCyber TUI and CLI."""
from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys

from neocyber.app import NeoCyberApp
from neocyber.engine.agent import AgentRunner
from neocyber.engine.ollama import OllamaClient
from neocyber.models.profile import ModelProfile, load_profiles


def run_headless(agent_name: str, task: str, profile_name: str, workspace: str) -> None:
    """Headless streaming execution for direct tasks (--run)."""
    config_dir = os.path.join(workspace, "config")
    profiles, default_p = load_profiles(config_dir)
    profile = profiles.get(profile_name, profiles.get(default_p))
    if not profile:
        profile = ModelProfile(name=profile_name, model_id=f"ollama/{profile_name}", ollama_name=profile_name)

    runner = AgentRunner(workspace)
    print(f"\n[NEOCYBER] Running task with {agent_name} ({profile.name})...\n")

    def _on_token(tok: str) -> None:
        sys.stdout.write(tok)
        sys.stdout.flush()

    def _on_tool_start(tid: str, cmd: str) -> None:
        width = min(shutil.get_terminal_size((80, 24)).columns - 4, 82)
        print(f"\n  {'─' * width}")
        print(f"  ▶ Executing: {cmd} ...")
        print(f"  {'─' * width}")

    def _on_tool_chunk(tid: str, chunk: str) -> None:
        sys.stdout.write(chunk)
        sys.stdout.flush()

    def _on_tool_complete(tid: str, code: int, out: str, dur: float) -> None:
        status = "SUCCESS" if code == 0 else f"FAILED (exit {code})"
        print(f"\n  [{status} · {dur}s]")
        if out.strip():
            print(out.rstrip())
        print()

    async def _run():
        await runner.execute_turn(
            agent_name=agent_name,
            profile=profile,
            history=[],
            user_prompt=task,
            on_token=_on_token,
            on_tool_start=_on_tool_start,
            on_tool_chunk=_on_tool_chunk,
            on_tool_complete=_on_tool_complete,
        )

    asyncio.run(_run())
    print("\n[NEOCYBER] Completed.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cyber",
        description="NeoCyber — Cybersecurity AI Harness (OpenCode TUI experience for local models)",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["cyber", "plan"],
        default="cyber",
        help="Agent mode: cyber (operator) or plan (threat modeler)",
    )
    parser.add_argument(
        "--profile",
        "-p",
        type=str,
        default=None,
        help="Model profile name from config/profiles.json",
    )
    parser.add_argument(
        "--run",
        "-r",
        type=str,
        default=None,
        help="Direct streaming task execution (non-interactive)",
    )
    parser.add_argument(
        "--profiles",
        action="store_true",
        help="List all supported model profiles",
    )
    parser.add_argument(
        "--findings",
        "-f",
        action="store_true",
        help="Show security findings dashboard",
    )
    parser.add_argument(
        "--no-mouse",
        action="store_true",
        default=False,
        help="Disable mouse capture in the terminal (by default mouse is enabled for natural mouse-wheel chat scrolling)",
    )

    args = parser.parse_args()
    workspace = os.getcwd()
    config_dir = os.path.join(workspace, "config")
    profiles, default_p = load_profiles(config_dir)

    if args.profiles:
        print("\nAvailable NeoCyber Model Profiles:")
        for name, p in profiles.items():
            active_marker = " (default)" if name == default_p else ""
            print(f"  - {name:<20} {p.param_size:<5} ctx: {p.context_budget}t{active_marker}")
        print()
        sys.exit(0)

    if args.findings:
        findings_file = os.path.join(workspace, "reports", "findings.json")
        if os.path.isfile(findings_file):
            import json
            with open(findings_file, "r") as f:
                data = json.load(f)
            print(f"\nSecurity Findings ({len(data)} recorded):")
            for item in data:
                print(f"  [{item.get('severity', 'INFO')}] {item.get('title')} ({item.get('asset')})")
            print()
        else:
            print("\nNo findings recorded.\n")
        sys.exit(0)

    chosen_profile = args.profile or default_p

    if args.run:
        run_headless(args.mode, args.run, chosen_profile, workspace)
        sys.exit(0)

    # Launch full interactive OpenCode-style TUI
    app = NeoCyberApp(
        workspace_dir=workspace,
        initial_agent=args.mode,
        initial_profile=chosen_profile,
    )
    app.run(mouse=not args.no_mouse)


if __name__ == "__main__":
    main()
