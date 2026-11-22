# neocyber

A cybersecurity-focused AI harness around a **local** model
(`Qwen2.5-Coder-7B-Instruct-abliterated`, Q4_K_M) served by Ollama and
OpenCode. Features a **real-time streaming TUI** with live event display.

## Modes

| Mode | Tools | Use |
|------|-------|-----|
| `cyber` | shell, read/write, grep/glob, web | recon, exploitation, analysis, reports |
| `plan`  | read/grep/glob/web only | scope mapping, attack chains, no execution |

Both modes deny `subagent` and `skill` tools to keep the 7B model focused and
prompt size minimal.

## Run

```bash
./cyber                           # mode picker → interactive TUI (live streaming)
./cyber cyber                     # jump to operator mode TUI
./cyber plan                      # jump to planner mode TUI
./cyber cyber --run "task..."     # non-interactive: stream events + response live
./cyber plan  --run "audit..."    # non-interactive planner run
./cyber --sessions                # list previous sessions
./cyber cyber --session ID        # continue a previous session
```

### Non-interactive streaming (--run)

`--run` mode uses `opencode run --format json` which emits **NDJSON events** as
they happen. The `cyber` launcher renders them live:

```
20:45:59 ◉  Initializing security assessment...
20:46:02 ◉  Analyzing request...
20:46:04 ▶  Executing tool: bash
╭─ TOOL · bash ──────────────────────────────────────────────────────────────────╮
│ $ nmap -sV 127.0.0.1
│ ● Running...
╰────────────────────────────────────────────────────────────────────────────────╯
╭─ RESULT · bash ────────────────────────────────────────────────────────────────╮
│ Starting Nmap...
│ ✓ Exit code: 0
╰────────────────────────────────────────────────────────────────────────────────╯
20:46:12 ✓  Tool complete: bash
20:46:14 ✓  Response complete · 2300ms

## Objective
...
```

### Interactive TUI (no --run)

Hands off directly to `opencode mini` — the native OpenCode TUI where you can
type tasks, see tools execute in real time, and click tool calls to expand them.

## GPU setup (required for speed)

Without GPU offload, Ollama runs on CPU (~8 tok/s).

```bash
sudo pacman -S ollama-cuda
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf <<'EOF'
[Service]
Environment="OLLAMA_CONTEXT_LENGTH=16384"
Environment="OLLAMA_KEEP_ALIVE=30m"
EOF
sudo systemctl daemon-reload && sudo systemctl restart ollama
ollama ps   # PROCESSOR should show partial GPU offload
```

`opencode.jsonc` `limit.context` must match `OLLAMA_CONTEXT_LENGTH`. On the
RTX 4050 (6 GB), 16384 context offloads ~18/29 layers to GPU.

## Files

```
cyber                        launcher + streaming TUI
opencode.jsonc               model alias ollama/cyber + limits
.opencode/agents/cyber.md    elite operator agent prompt
.opencode/agents/plan.md     read-only planner agent prompt
```

## Safety

`cyber` auto-approves shell commands — deliberate for local lab work.
To require confirmation before each shell command:

```yaml
# .opencode/agents/cyber.md
  - action: shell
    resource: "*"
    effect: ask   # was: allow
```
