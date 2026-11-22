#!/usr/bin/env bash
# lib/tui.sh — Terminal User Interface: ANSI Boxes, Timeline, Diffs & Findings

# ─── colours & symbols ────────────────────────────────────────────────────────
if [[ -t 1 ]] && tput colors &>/dev/null && [[ $(tput colors) -ge 8 ]]; then
  C_RESET=$'\033[0m'
  C_BOLD=$'\033[1m'
  C_DIM=$'\033[2m'
  C_CYAN=$'\033[36m'
  C_BRIGHT_CYAN=$'\033[96m'
  C_GREEN=$'\033[32m'
  C_BRIGHT_GREEN=$'\033[92m'
  C_YELLOW=$'\033[33m'
  C_BRIGHT_YELLOW=$'\033[93m'
  C_RED=$'\033[31m'
  C_BRIGHT_RED=$'\033[91m'
  C_WHITE=$'\033[97m'
  C_GRAY=$'\033[90m'
else
  C_RESET='' C_BOLD='' C_DIM='' C_CYAN='' C_BRIGHT_CYAN='' C_GREEN=''
  C_BRIGHT_GREEN='' C_YELLOW='' C_BRIGHT_YELLOW='' C_RED='' C_BRIGHT_RED=''
  C_WHITE='' C_GRAY=''
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
  local ws_display="${HERE:-$PWD}"
  ws_display="${ws_display/#$HOME/~}"
  
  local left=" NEOCYBER · $mode · $state"
  local right="PROFILE: $profile · WS: $ws_display "
  local pad=$(( w - ${#left} - ${#right} ))
  [[ $pad -lt 0 ]] && pad=0
  printf '%s%s%s%*s%s%s\n' \
    "$C_CYAN$C_BOLD" "$left" "$C_RESET$C_DIM" \
    "$pad" '' \
    "$right" "$C_RESET"
}

# Clean Markdown Renderer (Strips raw ## hashes, removes ``` backticks, styles sections)
clean_render_markdown() {
  local text="$1"
  local in_code=0 fence_lang=""

  while IFS= read -r line; do
    # Code fence toggle
    if [[ "$line" =~ ^\`\`\`(.*)$ ]]; then
      if [[ $in_code -eq 0 ]]; then
        in_code=1
        fence_lang="${BASH_REMATCH[1]}"
        printf '\n  %s┌─ %s%s%s %s┐%s\n' "$C_GRAY" "$C_BOLD" "${fence_lang:-command}" "$C_RESET$C_GRAY" "──────────────────────────────────────────────" "$C_RESET"
      else
        in_code=0
        printf '  %s└─────────────────────────────────────────────────┘%s\n\n' "$C_GRAY" "$C_RESET"
      fi
      continue
    fi

    if [[ $in_code -eq 1 ]]; then
      printf '  %s│%s  %s%s%s\n' "$C_GRAY" "$C_RESET" "$C_BRIGHT_GREEN" "$line" "$C_RESET"
      continue
    fi

    # Headings: Strip ## and convert to clean upper banner
    if [[ "$line" =~ ^#{1,4}[[:space:]](.+)$ ]]; then
      local h_title="${BASH_REMATCH[1]}"
      printf '\n%s%s◆ %s%s\n' "$C_BRIGHT_CYAN" "$C_BOLD" "${h_title^^}" "$C_RESET"
      continue
    fi

    # Bullet points: clean dot
    if [[ "$line" =~ ^[-*][[:space:]](.+)$ ]]; then
      printf '  %s·%s %s\n' "$C_CYAN" "$C_RESET" "${BASH_REMATCH[1]}"
      continue
    fi

    if [[ -z "$line" ]]; then
      printf '\n'
      continue
    fi

    # Remove inline backticks and style with yellow
    local rendered="$line"
    rendered="${rendered//\`/$C_YELLOW}"
    printf '  %s%s\n' "$rendered" "$C_RESET"
  done <<< "$text"
}

# Tool Execution Result Box
render_tool_result_box() {
  local cmd="$1"
  local exit_code="$2"
  local duration="$3"
  local output="$4"

  local w; w=$(cols)
  local box_w=$((w - 4))
  [[ $box_w -gt 86 ]] && box_w=86

  local border_col="$C_CYAN"
  local status_col="$C_BRIGHT_GREEN"
  local status_text="SUCCESS · Exit $exit_code · ${duration}s"
  if [[ "$exit_code" -ne 0 ]]; then
    border_col="$C_BRIGHT_RED"
    status_col="$C_BRIGHT_RED"
    status_text="FAILED · Exit $exit_code · ${duration}s"
  fi

  printf '\n  %s╭── %sSECURITY TOOL OUTPUT%s%s ──%*s╮%s\n' \
    "$border_col" "$C_BOLD" "$C_RESET" "$border_col" $((box_w - 27)) '' "$C_RESET" | tr ' ' '─'
  printf '  %s│%s  %sCommand :%s %s%s%s\n' "$border_col" "$C_RESET" "$C_GRAY" "$C_RESET" "$C_BOLD$C_WHITE" "$cmd" "$C_RESET"
  printf '  %s│%s  %sStatus  :%s %s%s%s\n' "$border_col" "$C_RESET" "$C_GRAY" "$C_RESET" "$status_col" "$status_text" "$C_RESET"
  printf '  %s├%*s┤%s\n' "$border_col" $((box_w - 2)) '' "$C_RESET" | tr ' ' '─'

  if [[ -z "$output" ]]; then
    printf '  %s│%s  %s(No output generated)%s\n' "$border_col" "$C_RESET" "$C_DIM" "$C_RESET"
  else
    local count=0
    while IFS= read -r l && [[ $count -lt 15 ]]; do
      local line_disp="${l:0:$((box_w - 6))}"
      printf '  %s│%s  %s%s%s\n' "$border_col" "$C_RESET" "$C_BRIGHT_GREEN" "$line_disp" "$C_RESET"
      (( count++ ))
    done <<< "$output"
    if [[ $count -ge 15 ]]; then
      printf '  %s│%s  %s... [truncated for context efficiency]%s\n' "$border_col" "$C_RESET" "$C_GRAY" "$C_RESET"
    fi
  fi
  printf '  %s╰%*s╯%s\n\n' "$border_col" $((box_w - 2)) '' "$C_RESET" | tr ' ' '─'
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
