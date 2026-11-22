#!/usr/bin/env bash
# lib/tui.sh — Terminal User Interface: ANSI Boxes, Timeline, Diffs & Findings

# ─── colours & symbols ────────────────────────────────────────────────────────
if [[ -t 1 ]] && tput colors &>/dev/null && [[ $(tput colors) -ge 8 ]]; then
  C_RESET=$'\033[0m'
  C_BOLD=$'\033[1m'
  C_DIM=$'\033[2m'
  C_CYAN=$'\033[36m'
  C_GREEN=$'\033[32m'
  C_YELLOW=$'\033[33m'
  C_RED=$'\033[31m'
  C_WHITE=$'\033[97m'
  C_GRAY=$'\033[90m'
  C_MAGENTA=$'\033[35m'
else
  C_RESET='' C_BOLD='' C_DIM='' C_CYAN='' C_GREEN=''
  C_YELLOW='' C_RED='' C_WHITE='' C_GRAY='' C_MAGENTA=''
fi

SYM_RUN="◉"   # active
SYM_OK="✓"    # done
SYM_ERR="✗"   # error
SYM_TOOL="▶"  # tool execution
SYM_FILE="⬡"  # file op
SYM_FIND="!"  # finding
SYM_STEP="·"  # step bullet

cols() { tput cols 2>/dev/null || echo 80; }
rows() { tput lines 2>/dev/null || echo 24; }

hr() {
  local w; w=$(cols)
  local char="${1:-─}"
  local color="${2:-$C_DIM}"
  printf '%s' "$color"
  printf '%*s' "$w" '' | tr ' ' "$char"
  printf '%s\n' "$C_RESET"
}

box_top() {
  local title="$1" w; w=$(cols)
  local inner=$((w - 4))
  local tlen=${#title}
  printf '%s╭─ %s%s%s ' "$C_CYAN" "$C_BOLD" "$title" "$C_RESET$C_CYAN"
  local remaining=$((inner - tlen - 2))
  [[ $remaining -lt 0 ]] && remaining=0
  printf '%*s' "$remaining" '' | tr ' ' '─'
  printf '╮%s\n' "$C_RESET"
}

box_line() {
  printf '%s│%s %s\n' "$C_CYAN" "$C_RESET" "$1"
}

box_bottom() {
  local w; w=$(cols)
  printf '%s╰' "$C_CYAN"
  printf '%*s' $((w - 2)) '' | tr ' ' '─'
  printf '╯%s\n' "$C_RESET"
}

activity() {
  local icon="$1" color="$2" msg="$3"
  local ts; ts=$(date '+%H:%M:%S')
  printf '%s%s%s %s%s%s  %s%s%s\n' \
    "$C_GRAY" "$ts" "$C_RESET" \
    "$color" "$icon" "$C_RESET" \
    "$C_WHITE" "$msg" "$C_RESET"
}

print_statusbar() {
  local mode="${1:-cyber}" state="${2:-READY}" profile="${3:-$NC_PROFILE_NAME}"
  local w; w=$(cols)
  local left=" NEOCYBER · $mode · $state"
  local right="PROFILE: $profile · Ctrl+C stop "
  local pad=$(( w - ${#left} - ${#right} ))
  [[ $pad -lt 0 ]] && pad=0
  printf '%s%s%s%*s%s%s\n' \
    "$C_CYAN$C_BOLD" "$left" "$C_RESET$C_DIM" \
    "$pad" '' \
    "$right" "$C_RESET"
}

# Real-time Diff Viewer
render_diff() {
  local file_path="$1"
  local old_file="$2"
  local new_file="$3"

  box_top "FILE DIFF · $file_path"
  if [[ -f "$old_file" && -f "$new_file" ]]; then
    while IFS= read -r line; do
      if [[ "$line" =~ ^\+ ]]; then
        box_line "$C_GREEN$line$C_RESET"
      elif [[ "$line" =~ ^\- ]]; then
        box_line "$C_RED$line$C_RESET"
      elif [[ "$line" =~ ^@@ ]]; then
        box_line "$C_CYAN$line$C_RESET"
      else
        box_line "$C_DIM$line$C_RESET"
      fi
    done < <(diff -u "$old_file" "$new_file" | tail -n +3)
  else
    box_line "$C_YELLOW(New or deleted file: $file_path)$C_RESET"
  fi
  box_bottom
}

# Structured Security Findings Display
render_findings() {
  local findings_file="${1:-$HERE/reports/findings.json}"
  [[ ! -f "$findings_file" ]] && return 0

  local count
  count=$(jq '. | length' "$findings_file" 2>/dev/null || echo 0)
  [[ $count -eq 0 ]] && return 0

  printf '\n'
  box_top "SECURITY FINDINGS ($count identified)"
  while IFS= read -r f; do
    local title sev asset desc
    title=$(echo "$f" | jq -r '.title // "Finding"')
    sev=$(echo "$f" | jq -r '.severity // "INFO"' | tr '[:lower:]' '[:upper:]')
    asset=$(echo "$f" | jq -r '.asset // "unknown"')
    desc=$(echo "$f" | jq -r '.description // ""')

    local sev_col="$C_CYAN"
    case "$sev" in
      CRITICAL) sev_col="$C_RED$C_BOLD" ;;
      HIGH)     sev_col="$C_RED" ;;
      MEDIUM)   sev_col="$C_YELLOW" ;;
      LOW)      sev_col="$C_GREEN" ;;
      *)        sev_col="$C_CYAN" ;;
    esac

    box_line "$(printf '%s[%-8s]%s %s%s%s (Target: %s)' "$sev_col" "$sev" "$C_RESET" "$C_BOLD" "$title" "$C_RESET" "$asset")"
    [[ -n "$desc" ]] && box_line "  $C_DIM$desc$C_RESET"
  done < <(jq -c '.[]' "$findings_file" 2>/dev/null)
  box_bottom
  printf '\n'
}
