# NeoCyber

NeoCyber is a cybersecurity AI agent harness with a terminal user interface, built for small local models served by Ollama. It recreates the interaction style of OpenCode, including real-time token streaming, styled tool execution cards, and an iterative agent loop that runs security diagnostics one step at a time.

## Purpose

NeoCyber helps operators and security engineers perform authorized security audits and diagnostics against targets they own or have explicit permission to assess. The harness works step by step: it announces a single test, runs one command, analyzes the real output, then decides the next test or produces a final remediation report.

## Features

- Terminal user interface built with Textual, with dark surfaces and responsive layout.
- Real-time token streaming from local Ollama endpoints.
- Styled tool execution cards showing command, status, duration, and live output.
- Stateful agent loop with a task plan, observations, bounded step budget, and execution ledger.
- Duplicate command detection to prevent repeated executions.
- Persistent sessions saved in `.neocyber/session.json` and restored on restart.
- Security findings stored in `reports/findings.json` with raw evidence in `reports/evidence/`.
- Direct shell trigger: prefix a prompt with `!` to run a command immediately.
- Two agent modes: `cyber` (operator with shell execution) and `plan` (read-only threat modeler).
- Scope guardrails that restrict scans to authorized targets.
- Refusal to run denial-of-service or flood tooling autonomously.

## Quickstart

Launch the interactive terminal interface:

```
./cyber
```

Launch directly into a specific agent mode:

```
./cyber cyber
./cyber plan
```

Run a single task headlessly with streaming output:

```
./cyber --run "Check system information with uname -a and uptime"
./cyber plan --run "Audit workspace files for sensitive configurations"
```

List available model profiles:

```
./cyber --profiles
```

Show recorded security findings:

```
./cyber --findings
```

## Security Audit Workflow

When you request a security audit or assessment, NeoCyber operates like a real operator, one test per turn:

1. It announces the single test it is running right now, for example "First, I will check whether the host is reachable."
2. It runs exactly one non-destructive diagnostic command and streams the output live.
3. Only after the command finishes does it analyze the actual output.
4. Based on that result, it runs the next single test, or delivers a final Security Assessment and Remediation Report.

The final report lists each test performed and its factual outcome, groups findings by severity (Critical, High, Medium, Low, Informational), and ends with a remediation playbook containing exact code or configuration fixes.

Example:

```
./cyber --run "Perform a security audit of http://127.0.0.1:3000/"
```

## Target Scope and Authorization

By default, NeoCyber only authorizes tests against localhost and private IP ranges (10.x, 192.168.x, 172.16.x through 172.31.x). To test another target that you own or have explicit written permission to assess, add its host or IP address to `target.txt` in the workspace:

```
echo "130.162.198.13" >> target.txt
```

Only run audits against targets you are authorized to test. NeoCyber will not autonomously run denial-of-service or flood tooling such as hping3 floods. Those commands require your explicit manual execution.

## Supported Commands and Shortcuts

Inside the interactive TUI:

- `!<command>`: run a shell command immediately, for example `!ip a` or `!nmap -sT 127.0.0.1`.
- `/cyber`: switch to Operator mode.
- `/plan`: switch to Planner mode.
- `/models` or `/model`: open the model picker dialog.
- `/findings`: open the security findings dashboard.
- `/clear`: clear the conversation transcript.
- `/help`: show the help overlay.
- `/quit` or `/exit`: exit NeoCyber.

Keyboard shortcuts:

- Ctrl+P: open the command palette.
- Tab: switch between Cyber Operator and Plan modes.
- Ctrl+M or F2: open the model selector.
- Escape: cancel the current action or stop execution.
- Enter: submit a prompt. Shift+Enter for multi-line input.
- Up / Down: navigate prompt history.
- ?: open the help overlay.
- Ctrl+C: quit the application.

## Model Profiles

Model profiles are configured in `config/profiles.json`. The default profile is `qwen2.5-coder:7b`.

| Profile | Parameter Size | Context Window | Intended Use |
|---------|----------------|----------------|--------------|
| qwen2.5-coder:7b | 7B | 16384 tokens | Default operator with high tool accuracy |
| llama3.2:3b | 3B | 16384 tokens | Fast lightweight local operator |
| gemma2:2b | 2B | 16384 tokens | Ultra-lightweight local model |

Switch profile from the command line:

```
./cyber --profile llama3.2:3b
```

## Safety and Guardrails

- Destructive system commands such as recursive removal, disk formatting, and raw disk writes are rejected.
- Full internet range scans are prohibited.
- Sudo, doas, and su commands are not run autonomously. The harness prints the exact command for you to run manually if elevation is required.
- Denial-of-service and flood tooling such as hping3 is never run autonomously.
- Targets outside the authorized scope are blocked unless added to `target.txt`.

## Tests

Run the test suite with:

```
.venv/bin/pytest tests/
```

## License

This project is provided for authorized security testing and diagnostics only. Users are responsible for ensuring they have permission to test any target.
