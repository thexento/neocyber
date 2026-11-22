#!/usr/bin/env bash
# lib/context.sh — Context Normalization & Tool Output Reduction for NeoCyber

NC_EVIDENCE_DIR="${NC_EVIDENCE_DIR:-$HERE/reports/evidence}"
mkdir -p "$NC_EVIDENCE_DIR"

# Save raw output to evidence directory and return file path
persist_evidence() {
  local tool_name="$1"
  local raw_content="$2"
  local ts; ts=$(date +%Y%m%d_%H%M%S)
  local filename="${tool_name}_${ts}.log"
  local filepath="$NC_EVIDENCE_DIR/$filename"

  printf '%s\n' "$raw_content" > "$filepath"
  echo "$filepath"
}

# Normalize nmap scan results into a compact representation
normalize_nmap() {
  local raw_output="$1"
  local evidence_file="$2"

  local open_ports
  open_ports=$(echo "$raw_output" | grep -E '^[0-9]+/(tcp|udp)[[:space:]]+open' | awk '{printf "%s (%s %s), ", $1, $3, $4}' | sed 's/, $//')
  
  if [[ -z "$open_ports" ]]; then
    if echo "$raw_output" | grep -qi "All [0-9]* scanned ports .* are closed\|filtered"; then
      open_ports="No open ports discovered (closed/filtered)"
    else
      open_ports="Scan finished without detected open ports"
    fi
  fi

  cat <<EOF
{
  "tool": "nmap",
  "status": "completed",
  "open_services": "$open_ports",
  "evidence_file": "$evidence_file",
  "note": "Full raw scan stored in evidence_file"
}
EOF
}

# Normalize HTTP probe results (curl)
normalize_curl() {
  local raw_output="$1"
  local evidence_file="$2"

  local status_code
  status_code=$(echo "$raw_output" | grep -E '^HTTP/[0-9\.]+' | tail -n 1 | awk '{print $2}')
  local server
  server=$(echo "$raw_output" | grep -i '^server:' | head -n 1 | awk '{print $2}' | tr -d '\r')

  cat <<EOF
{
  "tool": "curl",
  "status_code": "${status_code:-unknown}",
  "server": "${server:-none_advertised}",
  "evidence_file": "$evidence_file",
  "snippet": "$(echo "$raw_output" | head -n 10 | tr '\n' ' ' | sed 's/"/\\"/g' | cut -c1-200)"
}
EOF
}

# General output normalizer: Truncates if output exceeds line threshold
normalize_output() {
  local tool_name="$1"
  local raw_output="$2"
  local threshold="${NC_SUMMARIZE_THRESHOLD:-30}"

  local evidence_file
  evidence_file=$(persist_evidence "$tool_name" "$raw_output")

  case "$tool_name" in
    nmap)
      normalize_nmap "$raw_output" "$evidence_file"
      return 0
      ;;
    curl)
      normalize_curl "$raw_output" "$evidence_file"
      return 0
      ;;
  esac

  local total_lines
  total_lines=$(echo "$raw_output" | wc -l)

  if [[ $total_lines -le $threshold ]]; then
    cat <<EOF
{
  "tool": "$tool_name",
  "lines": $total_lines,
  "output": $(echo "$raw_output" | jq -Rs .),
  "evidence_file": "$evidence_file"
}
EOF
  else
    local head_part tail_part
    head_part=$(echo "$raw_output" | head -n 15)
    tail_part=$(echo "$raw_output" | tail -n 10)
    cat <<EOF
{
  "tool": "$tool_name",
  "status": "truncated",
  "total_lines": $total_lines,
  "evidence_file": "$evidence_file",
  "summary": "Output truncated to preserve small model context budget. Inspect evidence_file for full content.",
  "preview": $(printf "%s\n[... %d lines omitted ...]\n%s" "$head_part" "$((total_lines - 25))" "$tail_part" | jq -Rs .)
}
EOF
  fi
}
