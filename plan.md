# NeoCyber — UI & Architecture Overhaul Plan

Target workspace: `/home/xento7z/xento/test/neocyber`
Goal: Restore the clean, robust OpenCode Bash wrapper layout with true live streaming and polished visual rendering.

---

## 1. Problem Diagnosis

1. **Why the previous OpenCode wrapper felt better**:
   - The native Bash launcher (`cfb7cd3`) used clean, authentic ANSI terminal primitives, the iconic NeoCyber cyan ASCII banner, status bars, and properly wrapped OpenCode.
   - The recent Python REPL replacement (`61be887`) lacked the rich terminal wrapper feel, session listing, profile selection, and native launcher ergonomics.
2. **The Markdown Glitch**:
   - Small models output raw markdown (`## Objective`, ````bash`, etc.). When printed directly, raw hashes (`##`) and raw triple-backticks clutter the terminal.
   - We need an unbuffered stream formatter that strips the raw markdown characters and styles them into terminal borders, clean section titles, and highlighted blocks without delaying token output.
3. **Workspace & Model Management**:
   - Users need immediate visibility of the active workspace (`~/xento/test/neocyber`), model profile (`qwen2.5-coder:7b`), and active agent (`cyber` vs `plan`).
   - The launcher must provide easy switches: `--profile`, `--sessions`, `--findings`, and an interactive mode picker.

---

## 2. Design Specification

### Visual Layout
```text
   ██████╗██╗   ██╗██████╗ ███████╗██████╗
  ██╔════╝╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗
  ██║      ╚████╔╝ ██████╔╝█████╗  ██████╔╝
  ██║       ╚██╔╝  ██╔══██╗██╔══╝  ██╔══██╗
  ╚██████╗   ██║   ██████╔╝███████╗██║  ██║
   ╚═════╝   ╚═╝   ╚═════╝ ╚══════╝╚═╝  ╚═╝
  cybersecurity harness · model: qwen2.5-coder:7b (7B) · context: 16384t
────────────────────────────────────────────────────────────────────────────────
 NEOCYBER · cyber · RUNNING             PROFILE: qwen2.5-coder:7b · Ctrl+C stop 
────────────────────────────────────────────────────────────────────────────────

21:27:02 ◉  Analyzing security context...

╭── AGENT RESPONSE ────────────────────────────────────────────────────────────╮
│                                                                              │
│  OBJECTIVE                                                                   │
│  Check current working directory of the host.                                │
│                                                                              │
│  ACTION                                                                      │
│  ┌─ sh ────────────────────────────────────────────┐                         │
│  │  pwd                                            │                         │
│  └─────────────────────────────────────────────────┘                         │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

21:27:06 ▶  Executing command: pwd...

╭── SECURITY TOOL OUTPUT ──────────────────────────────────────────────────────╮
│  Command : pwd                                                               │
│  Status  : SUCCESS · Exit 0 · 0.01s                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│   /home/xento7z/xento/test/neocyber                                          │
╰──────────────────────────────────────────────────────────────────────────────╯

────────────────────────────────────────────────────────────────────────────────
 NEOCYBER · cyber · COMPLETED           WORKSPACE: ~/xento/test/neocyber
────────────────────────────────────────────────────────────────────────────────
```

---

## 3. Step-by-Step Implementation & Single Commit Plan

Each step will be committed individually:

- [ ] **Step 1**: Clean unneeded files and write detailed architecture plan to `plan.md`.
  - *Commit 1: `docs: update plan.md with detailed terminal UI and streaming overhaul`*
- [ ] **Step 2**: Enhance `lib/tui.sh` with clean stream-cleaning primitives (strip raw `##` and backticks, convert into styled box lines and clean headings).
  - *Commit 2: `feat(tui): enhance streaming markdown formatter and styled result boxes in lib/tui.sh`*
- [ ] **Step 3**: Overhaul `lib/engine.py` to stream tokens in real time while formatting text dynamically without raw markdown noise, and executing tools cleanly.
  - *Commit 3: `feat(engine): real-time stream formatter removing raw markdown clutter`*
- [ ] **Step 4**: Restore the primary `cyber` launcher script to integrate profile switching (`--profile`), session tracking (`--sessions`), findings dashboard (`--findings`), and the mode picker.
  - *Commit 4: `feat(launcher): restore cyber bash wrapper with full profile and workspace controls`*
- [ ] **Step 5**: Update `README.md` with complete documentation of features, shortcuts, model changing, and usage instructions.
  - *Commit 5: `docs: update README with usage, model profiles, and terminal UI controls`*
