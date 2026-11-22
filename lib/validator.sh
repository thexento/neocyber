#!/usr/bin/env bash
# lib/validator.sh — Security Scope, Command & Argument Guardrails for NeoCyber

NC_ALLOWED_HOSTS="${NC_ALLOWED_HOSTS:-127.0.0.1 localhost 10. 192.168. 172.16.}"

# Checks if a target host/IP is authorized
validate_target() {
  local target="$1"
  [[ -z "$target" ]] && return 1

  # Strip protocols or ports
  local host
  host=$(echo "$target" | sed -E 's~^[a-zA-Z]+://~~; s~:[0-9]+/?$~~; s~/.*$~~')

  for allowed in $NC_ALLOWED_HOSTS; do
    if [[ "$host" == "$allowed"* || "$host" == "$allowed" ]]; then
      return 0
    fi
  done

  # If explicitly configured in workspace target.txt
  if [[ -f "$HERE/target.txt" ]]; then
    if grep -qF "$host" "$HERE/target.txt"; then
      return 0
    fi
  fi

  return 1
}

# Checks for dangerous or unconstrained commands that small models might hallucinate
validate_command_safety() {
  local cmd="$1"
  
  # Dangerous destructive system commands
  if echo "$cmd" | grep -E -q 'rm[[:space:]]+-(r|f|rf|fr)[[:space:]]+/|mkfs|dd[[:space:]]+if=|:(){ :|:& };:'; then
    echo "ERROR: Destructive command rejected by safety policy."
    return 1
  fi

  # Prevent unconstrained broad internet scans unless explicitly allowed
  if echo "$cmd" | grep -E -q 'nmap[[:space:]]+-[A-Za-z0-9]*[[:space:]]+0\.0\.0\.0/0'; then
    echo "ERROR: Full internet range scan prohibited."
    return 1
  fi

  return 0
}

# Validates JSON action format if model emits structured actions
validate_action_json() {
  local json_str="$1"
  if ! echo "$json_str" | jq empty 2>/dev/null; then
    echo "ERROR: Action is not valid JSON."
    return 1
  fi

  local action
  action=$(echo "$json_str" | jq -r '.action // empty' 2>/dev/null)
  if [[ -z "$action" ]]; then
    echo "ERROR: Missing 'action' field."
    return 1
  fi

  return 0
}
