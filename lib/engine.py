#!/usr/bin/env python3
"""
lib/engine.py — High-Performance Streaming Execution Engine & Interactive REPL for NeoCyber
- Real-time word-by-word streaming from local Ollama
- Strips raw markdown hashes (##) and formats into clean OpenCode-style headers
- Strips raw backticks and formats code blocks into clean terminal boxes
- Executes commands live with real-time output and professional styled boxes
"""

import sys
import os
import json
import time
import shutil
import re
import subprocess
import urllib.request
import urllib.error

# ANSI Color & Style Codes
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

def get_term_width():
    return shutil.get_terminal_size((80, 24)).columns

def type_writer(text, delay=0.012):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()

def format_token_stream(token, state):
    """
    Format token stream on the fly:
    - Buffers lines to detect and strip raw markdown '##' headings
    - Formats code fences neatly
    - Prevents raw clutter while maintaining true streaming latency
    """
    state['buffer'] += token
    out = ""
    while "\n" in state['buffer']:
        line, state['buffer'] = state['buffer'].split("\n", 1)

        # Code fences
        if line.startswith("```"):
            if not state['in_code']:
                state['in_code'] = True
                lang = line[3:].strip() or "command"
                out += f"\n  {GRAY}┌─ {BOLD}{WHITE}{lang}{RESET}{GRAY} " + "─" * 45 + f"┐{RESET}\n"
            else:
                state['in_code'] = False
                out += f"  {GRAY}└" + "─" * 50 + f"┘{RESET}\n\n"
            continue

        if state['in_code']:
            out += f"  {GRAY}│{RESET}  {BRIGHT_GREEN}{line}{RESET}\n"
            continue

        # Convert raw '## Heading' into clean OpenCode-style section banner
        if re.match(r'^#{1,4}\s+', line):
            clean_heading = re.sub(r'^#{1,4}\s+', '', line).strip()
            out += f"\n{BOLD}{BRIGHT_CYAN}◆ {clean_heading.upper()}{RESET}\n"
            continue

        # Bullet items
        if re.match(r'^\s*[-*]\s+', line):
            clean_bullet = re.sub(r'^\s*[-*]\s+', '', line).strip()
            out += f"  {CYAN}·{RESET} {clean_bullet}\n"
            continue

        # Inline code backticks to yellow
        clean_line = re.sub(r'`(.*?)`', f'{YELLOW}\\1{RESET}', line)
        out += f"  {clean_line}\n"

    return out

def execute_command_live(cmd):
    width = min(get_term_width() - 4, 82)
    sys.stdout.write(f"\n  {GRAY}{timestamp()}{RESET} {BRIGHT_YELLOW}▶{RESET}  ")
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

        border_col = BRIGHT_CYAN if exit_code == 0 else BRIGHT_RED
        status_col = BRIGHT_GREEN if exit_code == 0 else BRIGHT_RED
        status_text = f"SUCCESS · Exit 0 · {duration}s" if exit_code == 0 else f"FAILED · Exit {exit_code} · {duration}s"

        print(f"\n  {border_col}╭── {BOLD}SECURITY TOOL OUTPUT{RESET}{border_col} ──" + "─" * (width - 27) + f"╮{RESET}")
        print(f"  {border_col}│{RESET}  {GRAY}Command :{RESET} {BOLD}{WHITE}{cmd}{RESET}")
        print(f"  {border_col}│{RESET}  {GRAY}Status  :{RESET} {status_col}{status_text}{RESET}")
        print(f"  {border_col}├" + "─" * (width - 2) + f"┤{RESET}")

        if not output_lines:
            print(f"  {border_col}│{RESET}  {DIM}(No output generated){RESET}")
        else:
            display_count = min(len(output_lines), 20)
            for i in range(display_count):
                line_str = output_lines[i]
                if len(line_str) > width - 6:
                    line_str = line_str[:width - 9] + "..."
                print(f"  {border_col}│{RESET}  {BRIGHT_GREEN if exit_code == 0 else YELLOW}{line_str}{RESET}")
            
            if len(output_lines) > 20:
                print(f"  {border_col}│{RESET}  {GRAY}... [{len(output_lines) - 20} lines omitted for context efficiency]{RESET}")

        print(f"  {border_col}╰" + "─" * (width - 2) + f"╯{RESET}\n", flush=True)
        return "\n".join(output_lines)
    except Exception as e:
        print(f"  {RED}Execution failed: {e}{RESET}")
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
        "options": {"temperature": 0.2}
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    sys.stdout.write(f"  {GRAY}{timestamp()}{RESET} {BRIGHT_CYAN}◉{RESET}  ")
    type_writer(f"Analyzing security context with {model_name}...", delay=0.012)
    print()

    full_response = ""
    stream_state = {'buffer': '', 'in_code': False}
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                if not line:
                    continue
                data = json.loads(line.decode("utf-8"))
                chunk = data.get("message", {}).get("content", "")
                if chunk:
                    full_response += chunk
                    formatted = format_token_stream(chunk, stream_state)
                    if formatted:
                        sys.stdout.write(formatted)
                        sys.stdout.flush()

                if data.get("done", False):
                    break

        if stream_state['buffer']:
            clean = stream_state['buffer'].strip()
            if clean and not clean.startswith("```"):
                sys.stdout.write(f"  {clean}\n")
                sys.stdout.flush()

    except urllib.error.URLError as e:
        print(f"\n  {RED}Error connecting to Ollama: {e}{RESET}\n")
        return full_response

    # Inspect for executable shell blocks inside the response
    lines = full_response.splitlines()
    i = 0
    commands = []
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
                commands.append(potential_cmd)
        i += 1

    for cmd in commands:
        execute_command_live(cmd)

    return full_response

def interactive_loop(model, agent_file, mode_name, workspace):
    system_prompt = f"You are {mode_name.upper()}, a security operator in {workspace}. State Objective, Action, Result, Next. Output bash commands inside ```bash blocks."
    if os.path.exists(agent_file):
        with open(agent_file, "r") as f:
            content = f.read()
            parts = content.split("---")
            if len(parts) >= 3:
                system_prompt = parts[2].strip()
            else:
                system_prompt = content.strip()

    history = []
    while True:
        try:
            prompt = input(f"{BOLD}{WHITE}Ask anything… {RESET}").strip()
            if not prompt:
                continue
            if prompt.lower() in [":q", ":quit", "exit"]:
                print(f"{DIM}Session closed.{RESET}")
                break

            response = stream_chat(model, system_prompt, prompt, history)
            history.append({"role": "user", "content": prompt})
            history.append({"role": "assistant", "content": response})
            if len(history) > 6:
                history = history[-6:]
            print()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM}Session interrupted.{RESET}")
            break

def main():
    if len(sys.argv) < 3:
        print("Usage: engine.py <model> <agent_prompt_file> [--interactive <mode> <workspace> | <user_prompt>]")
        sys.exit(1)

    model = sys.argv[1]
    agent_file = sys.argv[2]

    if len(sys.argv) > 3 and sys.argv[3] == "--interactive":
        mode_name = sys.argv[4] if len(sys.argv) > 4 else "cyber"
        workspace = sys.argv[5] if len(sys.argv) > 5 else os.getcwd()
        interactive_loop(model, agent_file, mode_name, workspace)
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
