#!/usr/bin/env bash
# lib/profiles.sh — Model Profiles Management for NeoCyber

NC_PROFILES_FILE="${NC_PROFILES_FILE:-$HERE/config/profiles.json}"

load_profile() {
  local prof_name="${1:-}"
  if [[ -z "$prof_name" && -f "$NC_PROFILES_FILE" ]]; then
    prof_name=$(jq -r '.default_profile // "qwen2.5-coder:7b"' "$NC_PROFILES_FILE" 2>/dev/null)
  fi
  [[ -z "$prof_name" ]] && prof_name="qwen2.5-coder:7b"

  if [[ ! -f "$NC_PROFILES_FILE" ]]; then
    export NC_PROFILE_NAME="default"
    export NC_MODEL_ID="ollama/cyber"
    export NC_CONTEXT_BUDGET=16384
    export NC_MAX_OUTPUT=4096
    export NC_NATIVE_TOOLS="true"
    export NC_TEMPERATURE=0.2
    export NC_MAX_RETRIES=3
    export NC_SUMMARIZE_THRESHOLD=30
    return 0
  fi

  local pdata
  pdata=$(jq -c --arg p "$prof_name" '.profiles[$p] // empty' "$NC_PROFILES_FILE" 2>/dev/null)
  if [[ -z "$pdata" ]]; then
    # Fallback to default
    prof_name=$(jq -r '.default_profile // "qwen2.5-coder:7b"' "$NC_PROFILES_FILE" 2>/dev/null)
    pdata=$(jq -c --arg p "$prof_name" '.profiles[$p] // empty' "$NC_PROFILES_FILE" 2>/dev/null)
  fi

  export NC_PROFILE_NAME="$prof_name"
  export NC_MODEL_ID=$(echo "$pdata" | jq -r '.model_id // "ollama/cyber"')
  export NC_OLLAMA_NAME=$(echo "$pdata" | jq -r '.ollama_name // "hf.co/bartowski/Qwen2.5-Coder-7B-Instruct-abliterated-GGUF:Q4_K_M"')
  export NC_PARAM_SIZE=$(echo "$pdata" | jq -r '.param_size // "7B"')
  export NC_CONTEXT_BUDGET=$(echo "$pdata" | jq -r '.context_budget // 16384')
  export NC_MAX_OUTPUT=$(echo "$pdata" | jq -r '.max_output_tokens // 4096')
  export NC_NATIVE_TOOLS=$(echo "$pdata" | jq -r '.native_tools // true')
  export NC_TEMPERATURE=$(echo "$pdata" | jq -r '.temperature // 0.2')
  export NC_TIMEOUT=$(echo "$pdata" | jq -r '.timeout_sec // 60')
  export NC_MAX_RETRIES=$(echo "$pdata" | jq -r '.max_retries // 3')
  export NC_SUMMARIZE_THRESHOLD=$(echo "$pdata" | jq -r '.summarize_threshold_lines // 30')
}

list_profiles() {
  if [[ -f "$NC_PROFILES_FILE" ]]; then
    jq -r '.profiles | to_entries[] | "  - \(.key) (Size: \(.value.param_size), Ctx: \(.value.context_budget), Tools: \(.value.native_tools))"' "$NC_PROFILES_FILE"
  fi
}
