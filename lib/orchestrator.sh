#!/usr/bin/env bash
# lib/orchestrator.sh — Task Decomposition & Step-by-Step Execution for Small Models

source "$HERE/lib/tools.sh"
source "$HERE/lib/profiles.sh"

# Decomposes high-level security goal into 4 structured stages
# Returns list of stages as newline-delimited strings
decompose_task() {
  local prompt="$1"
  local target
  target=$(echo "$prompt" | grep -oE '([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|localhost)' | head -n 1)
  [[ -z "$target" ]] && target="localhost"

  cat <<EOF
STG1: Scope Validation & Target Discovery ($target)
STG2: Port & Active Service Fingerprinting ($target)
STG3: Configuration & Vulnerability Assessment ($target)
STG4: Findings Synthesis & Remediation Summary ($target)
EOF
}

# Run a single milestone step with the small model, feeding only relevant context
execute_step() {
  local agent="$1"
  local step_desc="$2"
  local session_id="${3:-}"

  local step_prompt="You are in step: $step_desc.
Execute this specific step concisely. If tools are needed, run exact commands.
Reply using standard format:
## Objective
## Action
## Result
## Next"

  local oc_args=("run" "--format" "json" "--agent" "$agent" "--model" "$NC_MODEL_ID")
  [[ -n "$session_id" ]] && oc_args+=("--session" "$session_id")
  oc_args+=("$step_prompt")

  ( cd "$HERE" && "$OPENCODE" "${oc_args[@]}" )
}
