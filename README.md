# NeoCyber

> Elite Cybersecurity AI Agent Harness with an authentic OpenCode-grade Terminal User Interface (TUI), built specifically for small local models (1B–8B) served by Ollama.

NeoCyber recreates the visual language, interaction patterns, and responsiveness of **OpenCode** — including full-screen terminal rendering, real-time token streaming without raw markdown clutter, styled tool execution cards, color-coded unified diffs, and an interactive command palette.

---

## ⚡ Key Highlights

- **OpenCode TUI Experience**: Built with Textual (Python's Bubble Tea equivalent) featuring deep dark surfaces, crisp typography, responsive layout adaptation, and zero terminal flickering.
- **Genuine Live Streaming**: Token-by-token streaming from local Ollama endpoints with incremental markdown rendering and auto-scroll pinning.
- **In-Place Tool Execution**: Shell commands, recon scanners, and scripts run inside styled cards with live status badges (`[RUNNING]`, `[SUCCESS]`, `[FAILED]`), duration timers, and output viewports.
- **Color-Coded Diffs**: File modifications generate unified diffs with green additions (`+`) and red deletions (`-`).
- **Cybersecurity Operator Focus**:
  - `cyber`: Full operator with shell execution, tool chaining, file read/write/edit, and vulnerability verification.
  - `plan`: Read-only threat modeler for attack surface mapping and exploit chains without execution.
- **Small Model Optimized**: Context normalization for 1B–8B models (Qwen2.5-Coder 7B, Llama 3.2 3B, Gemma 2 2B) automatically truncates large scan outputs and archives raw logs to `reports/evidence/`.
- **Scope & Guardrails**: Prevents destructive commands and restricts scans to authorized targets.
- **Direct Shell Triggers**: Prefix any prompt with `!` to immediately run shell commands in an execution card without model inference (e.g. `!uname -a`, `!nmap localhost`).

---

## 🚀 Quickstart

Launch the interactive TUI:
```bash
./cyber
```

Launch directly into a specific agent persona:
```bash
./cyber cyber      # Operator mode
./cyber plan       # Threat modeler mode
```

### Direct Headless Execution (`--run`)
Stream execution directly in your terminal for single tasks:
```bash
./cyber --run "Check system info with uname -a and uptime"
./cyber plan --run "Audit workspace files for sensitive configs"
```

---

## ⌨️ Keyboard Shortcuts & Controls

| Shortcut | Action | Description |
|---|---|---|
| `Ctrl+P` | **Command Palette** | Search and trigger commands (`/cyber`, `/plan`, `/models`, `/findings`, `/clear`, `/help`, `/quit`) |
| `Tab` | **Switch Agent** | Toggle between **CYBER** (operator) and **PLAN** (planner) |
| `Ctrl+X` then `M` | **Model Selector** | Browse local Ollama models and switch active model profile |
| `F2` | **Cycle Models** | Quickly cycle through configured model profiles |
| `Escape` | **Cancel / Stop** | Stop ongoing model generation or running tool execution |
| `Enter` | **Submit Prompt** | Send message to agent (`Shift+Enter` for multi-line) |
| `Up` / `Down` | **History** | Navigate previous prompt history at top/bottom of input |
| `?` | **Help Overlay** | View complete quick reference modal |
| `Ctrl+C` | **Exit** | Gracefully quit NeoCyber |

---

## 🎯 Special Commands & Prefixes

Type directly in the prompt input:

- **`!<command>`**: Run direct shell command immediately.
  ```text
  !ip a
  !nmap -sT 127.0.0.1
  !cat /etc/os-release
  ```
- **`/cyber`**: Switch to Operator mode.
- **`/plan`**: Switch to Planner mode.
- **`/models`**: Open model picker dialog.
- **`/findings`**: Open security findings dashboard.
- **`/clear`**: Clear conversation transcript.
- **`/help`**: Show help modal.
- **`/quit`**: Exit NeoCyber.

---

## 🤖 Supported Local Models & Profiles

Configured in `config/profiles.json`:

| Profile | Parameter Size | Context Window | Default For |
|---|---|---|---|
| `qwen2.5-coder:7b` | 7B | 16,384 tokens | Default Operator (high tool accuracy) |
| `llama3.2:3b` | 3B | 8,192 tokens | Fast lightweight local operator |
| `gemma2:2b` | 2B | 8,192 tokens | Ultra-lightweight local model |

List all profiles:
```bash
./cyber --profiles
```

Switch profile from CLI:
```bash
./cyber --profile llama3.2:3b
```

---

## 🛡️ Security Findings & Evidence

Recorded findings are stored in `reports/findings.json` and raw scan outputs are saved in `reports/evidence/`.

Inspect findings via CLI:
```bash
./cyber --findings
```
Or use the `/findings` command inside the interactive TUI.

---

## 🧪 Running Tests

Run the comprehensive unit and integration test suite:
```bash
.venv/bin/pytest tests/
```
