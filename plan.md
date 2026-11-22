# NeoCyber — Architecture & Implementation Plan: Small Local Model Optimization & Native Bash TUI

Target workspace: `/home/xento7z/xento/test/neocyber`
Architecture: Native Bash TUI Harness around local LLMs (1B–8B parameters served via Ollama / OpenCode).
Core Principle: **Harness handles reliability and orchestration; small model handles intent and decision-making.**

---

## 1. System Overview & Core Tenets

Small local models (Qwen 2.5 Coder 7B, Gemma 2, Llama 3.2 1B/3B, etc.) struggle when:
- Complex system prompts overload their limited attention window.
- Multi-step, verbose tool outputs are dumped raw into prompt context.
- Arbitrary unconstrained shell commands are hallucinated.
- Retries enter infinite loops due to parse errors.

**NeoCyber solves this through:**
1. **Harness-Driven Intelligence & Step Decomposition**: Breaks high-level user tasks into phased security milestones (Recon -> Target Scope -> Port Discovery -> Service Inspection -> Vulnerability Evaluation -> Verified Reporting).
2. **Deterministic Typed Security Tools**: Exposes validated typed commands (e.g. `nmap` with safe defaults, `curl`, `ffuf`, file inspection) rather than forcing the model to remember complex syntax.
3. **Context Optimization & Output Normalization**: Raw tool output (e.g. 1000 lines of nmap scan or logs) is saved to disk (`reports/`, `evidence/`), and only a structured, concise summary is passed back to the model context.
4. **Structured JSON / Native Tool Layer with Validation & Guardrails**: Validates tool arguments against strict schemas, catches errors, provides bounded retries, and protects against scope escapes.
5. **Real-time Native Bash TUI with Live Event Streaming**: Responsive terminal UI displaying live activities, real-time command execution boxes, progressive model output, diff viewer, and structured security findings.
6. **Configurable Model Profiles**: Pre-tuned context limits, temperature, output token budgets, and prompt templates for small models (1B–8B).

---

## 2. Directory & Module Architecture

```text
/home/xento7z/xento/test/neocyber/
├── cyber                       # Primary executable entrypoint (Bash TUI + Orchestrator)
├── opencode.jsonc              # OpenCode model alias & provider configuration
├── prompt.txt                  # Baseline project contract & handoff reference
├── README.md                   # Quickstart, keyboard shortcuts & operator guide
├── plan.md                     # Full architectural roadmap and execution plan
│
├── lib/                        # Modular Bash harness libraries
│   ├── tui.sh                  # Terminal UI: ANSI boxes, timeline, streaming, findings pane, diffs
│   ├── orchestrator.sh         # Stage decomposer & multi-step execution loop
│   ├── context.sh              # Context budgeter, output truncator & normalizer
│   ├── tools.sh                # Deterministic security tool wrappers (nmap, curl, ffuf, grep, read)
│   ├── profiles.sh             # Model profiles (Qwen 7B, Llama 3B, Gemma 2B, Custom)
│   └── validator.sh            # Action & argument schema validator, boundary/scope guard
│
├── .opencode/
│   └── agents/
│       ├── cyber.md            # Operator agent: concise prompt, strict tool schemas
│       └── plan.md             # Read-only planner agent: scoping & attack chains
│
├── config/
│   └── profiles.json           # Profiles configuration for local models
│
└── reports/                    # Persisted raw tool outputs, findings, and evidence
```

---

## 3. Implementation Phases

### Phase 1: Modular Engine & Profiles Layer
- Create `lib/profiles.sh` and `config/profiles.json`:
  - Profile definitions:
    - `qwen2.5-coder:7b`: context 16384, max output 4096, native tool calling, temperature 0.2
    - `llama3.2:3b`: context 8192, max output 2048, prompt-guided tool calling, temperature 0.1
    - `gemma2:2b`: context 8192, max output 1500, structured JSON actions, temperature 0.2
- Allow profile switching via CLI flag (`--profile <name>` or `./cyber --profile qwen`).

### Phase 2: Context Management & Normalization Layer (`lib/context.sh`)
- Implement automatic stdout capture and file persistence:
  - Raw command output written to `reports/evidence/<tool>_<timestamp>.log`.
  - Normalization filters:
    - Nmap parser: parses open ports, services, versions into a clean JSON/key-value summary (< 200 tokens).
    - Curl/HTTP header parser: extracts status, headers, server fingerprint.
    - Ffuf/Dirb parser: extracts 200/301/403 discovered paths only.
  - Ensures tool feedback returned to the model never exceeds a strict budget (default 300 tokens per action).

### Phase 3: Deterministic Security Tool Wrappers & Validator (`lib/tools.sh`, `lib/validator.sh`)
- Define typed security operations:
  - `tool_scan_target [target] [port_range] [scan_type]`
  - `tool_probe_http [url] [method] [headers]`
  - `tool_enum_paths [url] [wordlist]`
  - `tool_inspect_file [path] [pattern]`
  - `tool_write_finding [title] [severity] [evidence_file] [remediation]`
- Scope validation:
  - Enforce target CIDR / domain boundaries. Reject attempts to target unlisted hosts.
  - Prevent destructive flags (`rm -rf`, format commands, broad denial-of-service).
- Validation and bounded retry:
  - Max 3 retries on malformed JSON / argument syntax with explicit one-line error feedback.

### Phase 4: Stage Decomposition & Orchestrator (`lib/orchestrator.sh`)
- Automatic task breakdown:
  - When user submits a high-level security goal (e.g., "Assess local service on port 8080"):
    - Step 1: Recon & Scope Confirmation
    - Step 2: Port & Service Fingerprinting
    - Step 3: Attack Surface & Config Review
    - Step 4: Verification of Specific Vectors
    - Step 5: Report Generation
- Feeds only the *current step* to the model, avoiding multi-page distraction and drift.

### Phase 5: Native Bash TUI Redesign (`lib/tui.sh` & `cyber`)
- Terminal layout & visual design:
  - Dark, minimalist technical aesthetic (Cyan/Green/Amber/Red, monospaced, UTF-8 box drawing with ASCII fallback).
  - Top status bar: Model, Active Profile, Context Budget, Target Scope, State (IDLE/RUNNING/ANALYZING).
  - Main display panels:
    - **Live Activity Timeline**: Real-time progress markers (`◉ Active`, `✓ Completed`, `✗ Error`).
    - **Live Command Execution Box**: Progressive stdout/stderr streaming, duration, exit code.
    - **Streaming Assistant Text**: Token streaming with live Markdown formatting.
    - **File Diff Viewer**: Native unified diff viewer with added/removed color highlights for file changes.
    - **Structured Findings Panel**: Visual severity badges (CRITICAL, HIGH, MEDIUM, LOW, INFO) with expandable details.
- Keyboard navigation:
  - `Ctrl+C`: Gracefully cancel current task / subprocess without terminating the session.
  - `Ctrl+N`: Start new session.
  - `Ctrl+E`: Toggle inspector / findings overlay.
  - `Tab`: Cycle modes / sections.

### Phase 6: Agent Prompts & OpenCode Optimization
- Update `.opencode/agents/cyber.md` and `plan.md`:
  - Optimize for 1B–8B attention limits: eliminate verbose prose, enforce strict JSON / tool format.
  - Include deterministic action schemas and clear scope boundaries.
- Keep token footprint of prompt under 500 tokens.

### Phase 7: Verification & Acceptance Testing
- Run end-to-end security workflows:
  1. Profile loading & switching test (`./cyber --profile qwen2.5-coder:7b`).
  2. Scope guardrail test (ensure out-of-scope targets are blocked by the validator).
  3. Output normalization test (verify large scan outputs are stored to disk and summarized to <300 tokens).
  4. Real-time TUI streaming and tool box test with live commands.
  5. File modification and diff viewer test.
  6. Structured finding persistence test (`reports/findings.json`).

---

## 4. Backout & Safety Strategy
- Maintain backward compatibility: `./cyber cyber --run "<prompt>"` continues to work.
- Modular library structure ensures scripts can be tested individually with unit shell tests.
- All persistent data confined to `reports/`, `config/`, and `.opencode/`.
