#!/usr/bin/env python3
"""
lib/engine.py — High-Performance Streaming Execution Engine & Interactive REPL for NeoCyber
Connects directly to local Ollama API, streaming tokens word-by-word in real time
with live command execution, polished cyberpunk box styling, and history.
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
BRIGHT_CYAN = "\033[96m"
GREEN = "\033[32m"
BRIGHT_GREEN = "\033[92m"
YELLOW = "\033[33m"
BRIGHT_YELLOW = "\033[93m"
RED = "\033[31m"
BRIGHT_RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
GRAY = "\033[90m"
WHITE = "\033[97m"
RESET = "\033[0m"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

def timestamp():
    return time.strftime("%H:%M:%S")

def type_writer(text, delay=0.015):
    """Types out a string character-by-character for live status feel."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()

def activity(icon, color, msg):
    print(f"{GRAY}{timestamp()}{RESET} {color}{icon}{RESET}  {WHITE}{msg}{RESET}", flush=True)

def execute_command_live(cmd):
    # Live animated typing status
    sys.stdout.write(f"\n{GRAY}{timestamp()}{RESET} {BRIGHT_YELLOW}▶{RESET}  ")
    type_writer(f"Executing command: {cmd}...", delay=0.01)

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

        proc.wait()
        duration = round(time.time() - start_time, 2)
        exit_code = proc.returncode

        # Draw a high-end terminal result box
        width = 82
        border_col = BRIGHT_CYAN if exit_code == 0 else BRIGHT_RED
        status_col = BRIGHT_GREEN if exit_code == 0 else BRIGHT_RED
        status_text = f"SUCCESS · Exit 0 · {duration}s" if exit_code == 0 else f"FAILED · Exit {exit_code} · {duration}s"

        print(f"\n{border_col}╭── {BOLD}SECURITY TOOL OUTPUT{RESET}{border_col} ──" + "─" * (width - 27) + f"╮{RESET}")
        print(f"{border_col}│{RESET}  {GRAY}Command :{RESET} {BOLD}{WHITE}{cmd}{RESET}")
        print(f"{border_col}│{RESET}  {GRAY}Status  :{RESET} {status_col}{status_text}{RESET}")
        print(f"{border_col}├" + "─" * (width - 2) + f"┤{RESET}")

        if not output_lines:
            print(f"{border_col}│{RESET}  {DIM}(No output generated){RESET}")
        else:
            display_count = min(len(output_lines), 20)
            for i in range(display_count):
                line_str = output_lines[i]
                # truncate line width if overly long
                if len(line_str) > width - 6:
                    line_str = line_str[:width - 9] + "..."
                print(f"{border_col}│{RESET}  {BRIGHT_GREEN if exit_code == 0 else YELLOW}{line_str}{RESET}")
            
            if len(output_lines) > 20:
                print(f"{border_col}│{RESET}  {GRAY}... [{len(output_lines) - 20} lines omitted for context efficiency]{RESET}")

        print(f"{border_col}╰" + "─" * (width - 2) + f"╯{RESET}\n", flush=True)
        activity("✓" if exit_code == 0 else "✗", BRIGHT_GREEN if exit_code == 0 else BRIGHT_RED, f"Command execution completed ({duration}s)")
        return "\n".join(output_lines)
    except Exception as e:
        print(f"{RED}Error executing command: {e}{RESET}")
        return str(e)

def stream_chat(model_name, system_prompt, user_prompt, conversation_history=None):
    if conversation_history is None:
        conversation_history = []

    url = f"{OLLAMA_HOST}/api/chat"
    messages = [{"role": "system", "content": system_prompt}] + conversation_history + [
        {"role": "user", "content": user_prompt}
    ]

    payload = {
        "model": model_name,
        "messages": messages,
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

    sys.stdout.write(f"{GRAY}{timestamp()}{RESET} {BRIGHT_CYAN}◉{RESET}  ")
    type_writer(f"Analyzing security context with {model_name}...", delay=0.012)
    print(f"\n{BRIGHT_CYAN}╭── {BOLD}AGENT STREAMING RESPONSE{RESET}{BRIGHT_CYAN} ──" + "─" * 51 + f"╮{RESET}\n")

    full_response = ""
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                if not line:
                    continue
                data = json.loads(line.decode("utf-8"))
                chunk = data.get("message", {}).get("content", "")
                if chunk:
                    # Stream chunk word-by-word instantly to terminal
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                    full_response += chunk

                if data.get("done", False):
                    break
    except urllib.error.URLError as e:
        print(f"\n{RED}Error connecting to Ollama: {e}{RESET}\n")
        return full_response

    print(f"\n\n{BRIGHT_CYAN}╰" + "─" * 78 + f"╯{RESET}\n", flush=True)
    activity("✓", BRIGHT_GREEN, "Response stream complete")

    # Inspect for executable shell blocks inside the response
    lines = full_response.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("```bash") or line.startswith("```sh") or line.startswith("```shell"):
            cmd_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                cmd_lines.append(lines[i].strip())
                i += 1
            potential_cmd = " && ".join([c for c in cmd_lines if c and not c.startswith("#")])
            if potential_cmd:
                execute_command_live(potential_cmd)
        i += 1

    return full_response

def interactive_loop(model, agent_file, mode_name):
    system_prompt = "You are CYBER, an offensive/defensive security operator. State Objective, Action, Result, Next. Output executable bash commands inside ```bash blocks."
    if os.path.exists(agent_file):
        with open(agent_file, "r") as f:
            content = f.read()
            parts = content.split("---")
            if len(parts) >= 3:
                system_prompt = parts[2].strip()
            else:
                system_prompt = content.strip()

    print(f"{GRAY}──────────────────────────────────────────────────────────────────────────────{RESET}")
    print(f" {BOLD}{BRIGHT_CYAN}NEOCYBER REPL{RESET} · {WHITE}{mode_name.upper()} MODE{RESET} · {GRAY}Type your security task or 'exit' to quit{RESET}")
    print(f"{GRAY}──────────────────────────────────────────────────────────────────────────────{RESET}\n")

    history = []
    while True:
        try:
            prompt = input(f"{BRIGHT_CYAN}neocyber ({mode_name}) › {RESET}").strip()
            if not prompt:
                continue
            if prompt.lower() in ["exit", "quit", "q"]:
                print(f"{DIM}Exiting NeoCyber session. Stay secure.{RESET}")
                break

            response = stream_chat(model, system_prompt, prompt, history)
            history.append({"role": "user", "content": prompt})
            history.append({"role": "assistant", "content": response})
            # Keep history bounded for small models
            if len(history) > 6:
                history = history[-6:]
            print()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM}Session interrupted.{RESET}")
            break

def main():
    if len(sys.argv) < 3:
        print("Usage: engine.py <model> <agent_prompt_file> [--interactive <mode> | <user_prompt>]")
        sys.exit(1)

    model = sys.argv[1]
    agent_file = sys.argv[2]

    if sys.argv[3] == "--interactive":
        mode_name = sys.argv[4] if len(sys.argv) > 4 else "cyber"
        interactive_loop(model, agent_file, mode_name)
    else:
        user_prompt = " ".join(sys.argv[3:])
        system_prompt = "You are CYBER, a security operator. State Objective, Action, Result, Next. Output bash commands in ```bash blocks."
        if os.path.exists(agent_file):
            with open(agent_file, "r") as f:
                content = f.read()
                parts = content.split("---")
                if len(parts) >= 3:
                    system_prompt = parts[2].strip()
                else:
                    system_prompt = content.strip()
        stream_chat(model, system_prompt, user_prompt)

if __name__ == "__main__":
    main()
