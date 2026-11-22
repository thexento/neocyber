#!/usr/bin/env bash
# lib/tools.sh — Deterministic Security Tool Wrappers for NeoCyber

source "$HERE/lib/validator.sh"
source "$HERE/lib/context.sh"

NC_FINDINGS_FILE="${NC_FINDINGS_FILE:-$HERE/reports/findings.json}"

# Initialize findings store
mkdir -p "$(dirname "$NC_FINDINGS_FILE")"
[[ ! -f "$NC_FINDINGS_FILE" ]] && echo '[]' > "$NC_FINDINGS_FILE"

# Deterministic Nmap Execution
execute_nmap() {
  local target="$1"
  local port_range="${2:-1-1000}"
  local scan_type="${3:--sT}"

  if ! validate_target "$target"; then
    cat <<EOF
{
  "tool": "nmap",
  "status": "error",
  "error": "Target '$target' is outside the authorized scope."
}
EOF
    return 1
  fi

  local cmd="nmap $scan_type -p $port_range -T4 --open $target"
  local raw_output
  raw_output=$(eval "$cmd" 2>&1)
  local code=$?

  normalize_output "nmap" "$raw_output"
  return $code
}

# Deterministic HTTP Probe
execute_curl() {
  local url="$1"
  local method="${2:-GET}"

  if ! validate_target "$url"; then
    cat <<EOF
{
  "tool": "curl",
  "status": "error",
  "error": "Target URL '$url' is outside the authorized scope."
}
EOF
    return 1
  fi

  local cmd="curl -s -i -k -X $method '$url'"
  local raw_output
  raw_output=$(eval "$cmd" 2>&1)
  local code=$?

  normalize_output "curl" "$raw_output"
  return $code
}

# Structured Security Finding Writer
record_finding() {
  local title="$1"
  local severity="$2" # Critical, High, Medium, Low, Informational
  local asset="$3"
  local description="$4"
  local evidence_file="${5:-}"
  local remediation="${6:-}"

  local finding_json
  finding_json=$(jq -n \
    --arg title "$title" \
    --arg severity "$severity" \
    --arg asset "$asset" \
    --arg desc "$description" \
    --arg evidence "$evidence_file" \
    --arg remediation "$remediation" \
    --arg ts "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
    '{
      id: ("FIND-" + ($ts | gsub("[-:TZ]"; ""))),
      title: $title,
      severity: $severity,
      asset: $asset,
      description: $desc,
      evidence_file: $evidence,
      remediation: $remediation,
      timestamp: $ts,
      verified: true
    }')

  local updated
  updated=$(jq --argjson f "$finding_json" '. += [$f]' "$NC_FINDINGS_FILE" 2>/dev/null)
  if [[ -n "$updated" ]]; then
    echo "$updated" > "$NC_FINDINGS_FILE"
  fi

  cat <<EOF
{
  "action": "record_finding",
  "status": "recorded",
  "title": "$title",
  "severity": "$severity"
}
EOF
}

# List all recorded findings
get_findings() {
  if [[ -f "$NC_FINDINGS_FILE" ]]; then
    cat "$NC_FINDINGS_FILE"
  else
    echo '[]'
  fi
}
