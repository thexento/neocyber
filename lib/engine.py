#!/usr/bin/env python3
"""
lib/engine.py — OpenCode Clone Terminal User Interface & Streaming Engine for NeoCyber
Features:
- Exact OpenCode TUI header, footer, shortcuts, status badges, and input box
- Live word-by-word streaming with real-time Markdown rendering (no raw '#' or backticks)
- In-place security tool execution inside clean OpenCode execution panels
- Dynamic Workspace indicator (~/xento/test/neocyber)
- In-app Model Switcher (:model or Ctrl+M)
- In-app Agent Switcher (:agent or Tab)
- In-app Session Management (:sessions)
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
MAGENTA = "\033[35m"
BOLD = "\033[1m"
DIM = "\033[2m"
GRAY = "\033[90m"
WHITE = "\033[97m"
ITALIC = "\033[3m"
RESET = "\033[0m"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

class OpenCodeTUI:
    def __init__(self, workspace_path, current_agent="cyber", current_model=None):
        self.workspace = workspace_path
        self.agent = current_agent
        self.model = current_model or "hf.co/bartowski/Qwen2.5-Coder-7B-Instruct-abliterated-GGUF:Q4_K_M"
        self.model_display = self.format_model_name(self.model)
        self.history = []
        self.running = True

    def get_term_size(self):
        size = shutil.get_terminal_size((80, 24))
        return size.columns, size.lines

    def format_model_name(self, name):
        if "Qwen2.5-Coder-7B" in name:
            return "Qwen2.5-Coder 7B (local)"
        return name.split("/")[-1].split(":")[0]

    def render_header(self):
        cols, _ = self.get_term_size()
        ws_display = self.workspace.replace(os.path.expanduser("~"), "~")
        
        # OpenCode top bar
        title = f"{BOLD}{WHITE}NeoCyber{RESET} {DIM}v2.3.2{RESET}"
        ws_info = f"{DIM}{ws_display}{RESET}"
        
        spacing = cols - len("NeoCyber v2.3.2") - len(ws_display) - 4
        if spacing < 2:
            spacing = 2
            
        print(f"\n {title}{' ' * spacing}{ws_info}")
        
        # Sub-status badge bar (identical to OpenCode)
        agent_badge = f"{BOLD}{CYAN}{self.agent.capitalize()}{RESET}"
        model_badge = f"{DIM}·{RESET} {WHITE}{self.model_display}{RESET} {GRAY}Ollama{RESET}"
        print(f" ┃ {agent_badge} {model_badge}")
        print(f" {GRAY}" + "─" * (cols - 2) + f"{RESET}\n")

    def render_footer(self):
        cols, _ = self.get_term_size()
        shortcuts = f"{GRAY}tab{RESET} agent  {GRAY}:model{RESET} switch model  {GRAY}:clear{RESET} clear  {GRAY}:help{RESET} commands  {GRAY}ctrl+c{RESET} quit"
        ws_display = self.workspace.replace(os.path.expanduser("~"), "~")
        right_info = f"{DIM}{ws_display}{RESET}"
        
        space = cols - len("tab agent  :model switch model  :clear clear  :help commands  ctrl+c quit") - len(ws_display) - 4
        if space < 2:
            space = 2
        print(f"\n {GRAY}" + "─" * (cols - 2) + f"{RESET}")
        print(f" {shortcuts}{' ' * space}{right_info}\n")

    def format_stream_token(self, token, state):
        """
        Formats raw model output stream dynamically:
        Strips markdown hashes (##), highlights headings, styles bullet points,
        and hides raw code fences while keeping syntax clean.
        """
        # Buffer text for line-based markdown parsing
        state['buffer'] += token
        out = ""
        while "\n" in state['buffer']:
            line, state['buffer'] = state['buffer'].split("\n", 1)
            
            # Check for code fence
            if line.startswith("```"):
                if not state['in_code']:
                    state['in_code'] = True
                    lang = line[3:].strip() or "sh"
                    out += f"\n  {GRAY}┌─ {WHITE}{BOLD}{lang}{RESET}{GRAY} " + "─" * 45 + f"┐{RESET}\n"
                else:
                    state['in_code'] = False
                    out += f"  {GRAY}└" + "─" * 50 + f"┘{RESET}\n\n"
                continue

            if state['in_code']:
                out += f"  {GRAY}│{RESET}  {BRIGHT_GREEN}{line}{RESET}\n"
                continue

            # Clean Headings (removes ##, ###, and formats with clean OpenCode style)
            if re.match(r'^#{1,4}\s+', line):
                clean_heading = re.sub(r'^#{1,4}\s+', '', line).strip()
                out += f"\n{BOLD}{BRIGHT_CYAN}◆ {clean_heading.upper()}{RESET}\n"
                continue

            # Clean list bullet items (- or *)
            if re.match(r'^\s*[-*]\s+', line):
                clean_bullet = re.sub(r'^\s*[-*]\s+', '', line).strip()
                out += f"  {CYAN}·{RESET} {clean_bullet}\n"
                continue

            # Inline bold / code formatting
            clean_line = re.sub(r'\*\*(.*?)\*\*', f'{BOLD}\\1{RESET}', line)
            clean_line = re.sub(r'`(.*?)`', f'{YELLOW}\\1{RESET}', clean_line)

            out += f"  {clean_line}\n"

        return out

    def execute_security_command(self, cmd):
        cols, _ = self.get_term_size()
        box_w = min(cols - 4, 86)
        
        print(f"\n  {GRAY}{time.strftime('%H:%M:%S')}{RESET} {BRIGHT_YELLOW}▶{RESET} {WHITE}Executing tool:{RESET} {BOLD}{WHITE}{cmd}{RESET}")
        print(f"  {CYAN}╭─ {BOLD}TOOL EXECUTION{RESET}{CYAN} " + "─" * (box_w - 18) + f"╮{RESET}")
        print(f"  {CYAN}│{RESET}  {GRAY}$ {cmd}{RESET}")
        print(f"  {CYAN}│{RESET}  {CYAN}◉ Running live...{RESET}")
        print(f"  {CYAN}├" + "─" * (box_w - 2) + f"┤{RESET}")

        start_time = time.time()
        output_lines = []
        try:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in proc.stdout:
                c_line = line.rstrip()
                output_lines.append(c_line)
                if len(output_lines) <= 15:
                    disp = c_line[:box_w - 6]
                    print(f"  {CYAN}│{RESET}  {BRIGHT_GREEN}{disp}{RESET}", flush=True)

            proc.wait()
            duration = round(time.time() - start_time, 2)
            exit_code = proc.returncode

            if len(output_lines) > 15:
                print(f"  {CYAN}│{RESET}  {GRAY}... [{len(output_lines) - 15} lines summarized for context efficiency]{RESET}")

            status_str = f"{BRIGHT_GREEN}✓ Completed · Exit 0 · {duration}s{RESET}" if exit_code == 0 else f"{BRIGHT_RED}✗ Exit {exit_code} · {duration}s{RESET}"
            print(f"  {CYAN}├" + "─" * (box_w - 2) + f"┤{RESET}")
            print(f"  {CYAN}│{RESET}  {status_str}")
            print(f"  {CYAN}╰" + "─" * (box_w - 2) + f"╯{RESET}\n", flush=True)
            return "\n".join(output_lines)
        except Exception as e:
            print(f"  {CYAN}│{RESET}  {RED}Execution failed: {e}{RESET}")
            print(f"  {CYAN}╰" + "─" * (box_w - 2) + f"╯{RESET}\n", flush=True)
            return str(e)

    def stream_prompt(self, user_prompt):
        agent_file = os.path.join(self.workspace, f".opencode/agents/{self.agent}.md")
        system_prompt = f"You are {self.agent.upper()}, a security specialist in {self.workspace}. State Objective, Action, Result, Next. Enclose commands in ```bash blocks."
        if os.path.exists(agent_file):
            with open(agent_file, "r") as f:
                content = f.read()
                parts = content.split("---")
                if len(parts) >= 3:
                    system_prompt = parts[2].strip()

        messages = [{"role": "system", "content": system_prompt}] + self.history + [
            {"role": "user", "content": user_prompt}
        ]

        url = f"{OLLAMA_HOST}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.2}
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        print(f"  {GRAY}{time.strftime('%H:%M:%S')}{RESET} {BRIGHT_CYAN}◉{RESET} {WHITE}Thinking...{RESET}\n")

        full_raw = ""
        stream_state = {'buffer': '', 'in_code': False}
        commands_to_run = []

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                for chunk_line in resp:
                    if not chunk_line:
                        continue
                    data = json.loads(chunk_line.decode("utf-8"))
                    token = data.get("message", {}).get("content", "")
                    if token:
                        full_raw += token
                        formatted = self.format_stream_token(token, stream_state)
                        if formatted:
                            sys.stdout.write(formatted)
                            sys.stdout.flush()

                    if data.get("done", False):
                        break

            # Flush remaining buffer
            if stream_state['buffer']:
                clean = stream_state['buffer'].strip()
                if clean and not clean.startswith("```"):
                    sys.stdout.write(f"  {clean}\n")
                    sys.stdout.flush()

        except Exception as e:
            print(f"\n{RED}Error contacting model: {e}{RESET}")
            return

        # Extract commands from full_raw
        lines = full_raw.splitlines()
        i = 0
        while i < len(lines):
            l = lines[i].strip()
            if l.startswith("```bash") or l.startswith("```sh") or l.startswith("```shell"):
                c_block = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    c_block.append(lines[i].strip())
                    i += 1
                cmd = " && ".join([c for c in c_block if c and not c.startswith("#")])
                if cmd:
                    commands_to_run.append(cmd)
            i += 1

        for cmd in commands_to_run:
            self.execute_security_command(cmd)

        self.history.append({"role": "user", "content": user_prompt})
        self.history.append({"role": "assistant", "content": full_raw})
        if len(self.history) > 6:
            self.history = self.history[-6:]

    def list_models(self):
        try:
            req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m['name'] for m in data.get('models', [])]
                return models
        except Exception:
            return ["hf.co/bartowski/Qwen2.5-Coder-7B-Instruct-abliterated-GGUF:Q4_K_M", "qwen2.5-coder:7b"]

    def model_switch_prompt(self):
        models = self.list_models()
        print(f"\n{BOLD}{BRIGHT_CYAN}Available Models:{RESET}")
        for idx, m in enumerate(models, 1):
            active = f" {GREEN}● active{RESET}" if m == self.model else ""
            print(f"  [{idx}] {m}{active}")
        print()
        choice = input(f"{CYAN}Select model (1-{len(models)}) or press Enter to cancel › {RESET}").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(models):
            self.model = models[int(choice) - 1]
            self.model_display = self.format_model_name(self.model)
            print(f"{GREEN}✓ Switched active model to: {self.model}{RESET}\n")

    def run_repl(self):
        os.system('clear' if os.name == 'posix' else 'cls')
        self.render_header()
        
        while self.running:
            try:
                prompt = input(f"{BOLD}{WHITE}Ask anything… {RESET}").strip()
                if not prompt:
                    continue

                if prompt in [":q", ":quit", "exit"]:
                    print(f"{DIM}Goodbye!{RESET}")
                    break

                if prompt == ":clear":
                    os.system('clear' if os.name == 'posix' else 'cls')
                    self.render_header()
                    continue

                if prompt in [":model", ":models"]:
                    self.model_switch_prompt()
                    continue

                if prompt in [":agent", "tab"]:
                    self.agent = "plan" if self.agent == "cyber" else "cyber"
                    print(f"{GREEN}✓ Switched agent to: {self.agent}{RESET}\n")
                    continue

                if prompt in [":help", ":h"]:
                    print(f"\n{BOLD}Available Commands:{RESET}")
                    print(f"  {CYAN}:model{RESET}   Switch active Ollama model")
                    print(f"  {CYAN}:agent{RESET}   Switch between cyber (operator) and plan (planner)")
                    print(f"  {CYAN}:clear{RESET}   Clear terminal screen")
                    print(f"  {CYAN}:quit{RESET}    Exit session\n")
                    continue

                self.stream_prompt(prompt)
                self.render_footer()

            except (KeyboardInterrupt, EOFError):
                print(f"\n{DIM}Session closed.{RESET}")
                break

def main():
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agent = "cyber"
    if len(sys.argv) > 1 and sys.argv[1] in ["cyber", "plan"]:
        agent = sys.argv[1]

    tui = OpenCodeTUI(workspace, current_agent=agent)
    
    if len(sys.argv) > 2 and sys.argv[2] == "--run":
        user_prompt = " ".join(sys.argv[3:])
        tui.render_header()
        tui.stream_prompt(user_prompt)
        tui.render_footer()
    else:
        tui.run_repl()

if __name__ == "__main__":
    main()
