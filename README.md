# neocyber

A cybersecurity-focused AI harness around local language models
(`Qwen2.5-Coder-7B-Instruct-abliterated`, `Llama 3.2 3B`, `Gemma 2 2B`) served by Ollama.

Features true **word-by-word real-time streaming**, an authentic terminal wrapper design, in-place tool execution inside styled panels, and clean Markdown rendering without raw hashes or backticks.

---

## Modes

| Mode | Tools | Description |
|---|---|---|
| `cyber` | shell, read/write, grep/glob, web | Full security operator for recon, exploitation, source audit, reports |
| `plan` | read/grep/glob/web only | Read-only planner for threat models and structured attack chains |

---

## Quickstart

Run the interactive launcher:
```bash
./cyber
```
Select `[1] cyber` for operator mode or `[2] plan` for planner mode.

Or launch directly:
```bash
./cyber cyber      # Operator mode interactive REPL
./cyber plan       # Planner mode interactive REPL
```

### Direct Task Streaming (`--run`)
Stream execution directly for a specific security task:
```bash
./cyber cyber --run "Check system info with uname -a and uptime"
./cyber plan  --run "Audit current workspace for sensitive configs"
```

---

## Model Profiles

Small local models (1B–8B) require tailored context budgets and parameters. NeoCyber includes built-in profiles:

```bash
./cyber --profiles
```

Switch active profile:
```bash
./cyber --profile qwen2.5-coder:7b
./cyber --profile llama3.2:3b
./cyber --profile gemma2:2b
```

---

## Security Findings Dashboard

Inspect recorded vulnerabilities and verification evidence:
```bash
./cyber --findings
```

---

## Terminal UI Features

- **Iconic Cyan ASCII Banner & Status Line**: Always displays the active agent, profile, parameters, and current workspace (`~/xento/test/neocyber`).
- **Clean Stream Rendering**: Automatically formats raw `##` headings into cyan section headers (`◆ OBJECTIVE`, `◆ ACTION`, `◆ RESULT`, `◆ NEXT`).
- **Live Tool Execution**: When the agent issues a command, it displays the command execution in real-time inside a styled security box with duration and exit codes.
- **Context Optimization**: Large scan results (e.g. `nmap`, `curl`, directory scans) are saved to `reports/evidence/` and summarized to preserve the small model's limited context window.
