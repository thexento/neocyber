#!/usr/bin/env python3
"""
lib/engine.py — High-Performance Streaming Execution Engine for NeoCyber
Connects directly to local Ollama API, streaming tokens word-by-word in real time
with live command execution, diff display, and output normalization.
Zero third-party dependencies (pure standard library).
"""

import sys
import os
import json
import time
import subprocess
import urllib.request
import urllib.error

# ANSI Color Codes
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
DIM = "\033[2m"
GRAY = "\033[90m"
RESET = "\033[0m"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

def timestamp():
    return time.strftime("%H:%M:%S")

def activity(icon, color, msg):
    print(f"{GRAY}{timestamp()}{RESET} {color}{icon}{RESET}  {BOLD}{msg}{RESET}", flush=True)

def render_box(title, lines, status=""):
    width = 78
    print(f"\n{CYAN}╭─ {BOLD}{title}{RESET}{CYAN} " + "─" * max(0, width - len(title) - 5) + f"╮{RESET}")
    for line in lines:
        print(f"{CYAN}│{RESET} {line}")
    if status:
        print(f"{CYAN}│{RESET} {status}")
    print(f"{CYAN}╰" + "─" * (width - 2) + f"╯{RESET}\n", flush=True)

def execute_command_live(cmd):
    activity("▶", YELLOW, f"Executing security command: {cmd}")
    print(f"\n{CYAN}╭─ {BOLD}COMMAND EXECUTION{RESET}{CYAN} " + "─" * 57 + f"╮{RESET}")
    print(f"{CYAN}│{RESET} {GREEN}$ {cmd}{RESET}")
    print(f"{CYAN}│{RESET} {CYAN}◉ Running live...{RESET}")
    print(f"{CYAN}│{RESET}")

    start_time = time.time()
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        output_lines = []
        for line in proc.stdout:
            clean_line = line.rstrip()
            output_lines.append(clean_line)
            # Display live lines inside box
            if len(output_lines) <= 25:
                print(f"{CYAN}│{RESET}   {DIM}{clean_line}{RESET}", flush=True)

        proc.wait()
        duration = round(time.time() - start_time, 2)
        exit_code = proc.returncode

        if len(output_lines) > 25:
            print(f"{CYAN}│{RESET}   {GRAY}... [{len(output_lines) - 25} lines summarized for context efficiency]{RESET}")

        status_msg = f"{GREEN}✓ Completed · Exit code: {exit_code} · {duration}s{RESET}" if exit_code == 0 else f"{RED}✗ Failed · Exit code: {exit_code} · {duration}s{RESET}"
        print(f"{CYAN}│{RESET}")
        print(f"{CYAN}│{RESET} {status_msg}")
        print(f"{CYAN}╰" + "─" * 76 + f"╯{RESET}\n", flush=True)

        activity("✓" if exit_code == 0 else "✗", GREEN if exit_code == 0 else RED, f"Command completed ({duration}s)")
        return "\n".join(output_lines)
    except Exception as e:
        print(f"{CYAN}│{RESET} {RED}Error: {e}{RESET}")
        print(f"{CYAN}╰" + "─" * 76 + f"╯{RESET}\n", flush=True)
        return str(e)

def stream_chat(model_name, system_prompt, user_prompt):
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": True,
        "options": {
            "temperature": 0.2
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    activity("◉", CYAN, f"Analyzing security context with local model ({model_name})...")
    print(f"\n{CYAN}╭─ {BOLD}AGENT STREAMING OUTPUT{RESET}{CYAN} " + "─" * 52 + f"╮{RESET}\n")

    full_response = ""
    command_to_run = None
    in_code_block = False
    current_code_lang = ""
    current_code_lines = []

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                if not line:
                    continue
                data = json.loads(line.decode("utf-8"))
                chunk = data.get("message", {}).get("content", "")
                if chunk:
                    # Stream chunk immediately to terminal without any buffer delay
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                    full_response += chunk

                if data.get("done", False):
                    break
    except urllib.error.URLError as e:
        print(f"\n{RED}Error connecting to Ollama: {e}{RESET}\n")
        return

    print(f"\n\n{CYAN}╰" + "─" * 76 + f"╯{RESET}\n", flush=True)
    activity("✓", GREEN, "Generation finished")

    # Inspect for executable shell blocks inside the response
    lines = full_response.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```bash") or line.startswith("```sh") or line.startswith("```shell"):
            cmd_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                cmd_lines.append(lines[i].strip())
                i += 1
            potential_cmd = " && ".join([c for c in cmd_lines if c and not c.startswith("#")])
            if potential_cmd:
                # Execute the identified security command live
                execute_command_live(potential_cmd)
        i += 1

def main():
    if len(sys.argv) < 3:
        print("Usage: engine.py <model> <agent_prompt_file> <user_prompt>")
        sys.exit(1)

    model = sys.argv[1]
    agent_file = sys.argv[2]
    user_prompt = " ".join(sys.argv[3:])

    system_prompt = "You are CYBER, a security operator. State Objective, Action, Result, Next. Output bash commands in ```bash blocks."
    if os.path.exists(agent_file):
        with open(agent_file, "r") as f:
            content = f.read()
            # If frontmatter present, strip it
            parts = content.split("---")
            if len(parts) >= 3:
                system_prompt = parts[2].strip()
            else:
                system_prompt = content.strip()

    stream_chat(model, system_prompt, user_prompt)

if __name__ == "__main__":
    main()
