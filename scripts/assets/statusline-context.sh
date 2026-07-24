#!/usr/bin/env bash
# Claude Code status line — compact: context + effort + speed + teammates.
#
# Format:  Opus(25%) xhigh 47 | 3 20
#   Opus      model name (first word of display_name)
#   (25%)     context used %, colour-coded (green<50 / yellow<75 / red>=75 / bold>=90)
#   xhigh     reasoning effort level (omitted for models without it, e.g. Haiku)
#   47        speed: output tokens per second of ACTIVE API time (idle excluded)
#   | 3 20    teammates of THIS session: their context %, colour-coded (no names, no %)
#
# Percentages come from the pre-calculated context_window stdin (same as /context).
# Fails loud if jq missing. Teammate block is additive (empty if no teammates).

set -euo pipefail
input="$(cat)"

JQ="$(command -v jq 2>/dev/null || true)"
if [ -z "$JQ" ]; then
  for c in /opt/homebrew/bin/jq /usr/local/bin/jq "$HOME/anaconda3/bin/jq" "$HOME/miniconda3/bin/jq"; do
    [ -x "$c" ] && JQ="$c" && break
  done
fi
if [ -z "$JQ" ]; then printf '\033[1;31mSL: jq not found\033[0m'; exit 0; fi

# Join with the ASCII Unit Separator (\u001f), a NON-whitespace delimiter, and read
# with IFS set to it — so EMPTY fields are preserved. (A whitespace delimiter would
# collapse consecutive separators and drop empty fields, e.g. when a model has no
# `effort` level like Haiku — that shifts every later field and corrupts the math.)
IFS=$'\037' read -r used model effort itok otok apims sid csize < <(
  "$JQ" -r '
    [ (.context_window.used_percentage     // -1),
      (.model.display_name                 // "?"),
      (.effort.level                       // ""),
      (.context_window.total_input_tokens  // 0),
      (.context_window.total_output_tokens // 0),
      (.cost.total_api_duration_ms         // 0),
      (.session_id                         // "x"),
      (.context_window.context_window_size // 0)
    ] | map(tostring) | join("\u001f")' <<<"$input"
)

ESC=$'\033'
rst="${ESC}[0m"; dim="${ESC}[2m"
model_short="${model%% *}"   # first word, e.g. "Opus 4.8 (1M context)" -> "Opus"

colour_for() {
  local p=$1
  if   [ "$p" -ge 90 ]; then printf '%s' "${ESC}[1;91m"
  elif [ "$p" -ge 75 ]; then printf '%s' "${ESC}[1;31m"
  elif [ "$p" -ge 50 ]; then printf '%s' "${ESC}[33m"
  else                       printf '%s' "${ESC}[32m"; fi
}

# speed = delta(output tokens) / delta(active API time), per-session state file.
# total_api_duration_ms sums real API-call durations, so idle gaps between turns
# don't dilute the rate (that's the point — "tokens per second of actual run").
# Holds the last value when output isn't growing; 0 only until a first sample.
speed_val() {
  set +e
  local sf last_api last_tok last_rate d dapi rate
  sf="/tmp/sl-speed-${sid}.state"
  case "$otok"  in (''|*[!0-9]*) otok=0;; esac
  case "$apims" in (''|*[!0-9]*) apims=0;; esac
  if [ -f "$sf" ]; then
    read -r last_api last_tok last_rate < "$sf" 2>/dev/null
    case "$last_api" in (''|*[!0-9]*) last_api=0;; esac
    case "$last_tok" in (''|*[!0-9]*) last_tok=0;; esac
    case "$last_rate" in (''|*[!0-9]*) last_rate=0;; esac
    d=$(( otok - last_tok ))
    dapi=$(( apims - last_api ))
    if [ "$d" -gt 0 ] && [ "$dapi" -gt 0 ]; then
      rate=$(( d * 1000 / dapi ))
    else
      rate=$last_rate
    fi
    printf '%s %s %s\n' "$apims" "$otok" "$rate" > "$sf" 2>/dev/null
  else
    rate=0
    printf '%s %s %s\n' "$apims" "$otok" "$rate" > "$sf" 2>/dev/null
  fi
  printf '%s' "$rate"
}

# context % of THIS session's running teammates (empty if none).
# Agent-team teammates run in a tmux server on socket claude-swarm-<PID-of-this-claude>.
# We find OUR socket by walking this script's process ancestry — so we never show
# OTHER sessions' teammates. Each teammate's CTX % is read straight from its pane.
teammates_blurb() {
  set +e
  local U sock_dir snap mypid ppid found step pid cap who ctx out
  U=$(id -u)
  sock_dir="/private/tmp/tmux-$U"; [ -d "$sock_dir" ] || sock_dir="/tmp/tmux-$U"
  [ -d "$sock_dir" ] || return 0
  command -v tmux >/dev/null 2>&1 || return 0
  snap=$(ps -eo pid=,ppid= 2>/dev/null); [ -n "$snap" ] || return 0
  mypid=$$; found=""
  for step in $(seq 1 15); do
    if [ -S "$sock_dir/claude-swarm-$mypid" ]; then found="claude-swarm-$mypid"; break; fi
    ppid=$(awk -v p="$mypid" '$1==p{print $2; exit}' <<<"$snap")
    [ -n "$ppid" ] || break
    [ "$ppid" -le 1 ] && break
    mypid=$ppid
  done
  [ -n "$found" ] || return 0
  out=""
  for pid in $(tmux -L "$found" list-panes -a -F '#{pane_id}' 2>/dev/null); do
    cap=$(tmux -L "$found" capture-pane -p -t "$pid" 2>/dev/null)
    who=$(grep -oE '@[A-Za-z0-9_-]+' <<<"$cap" | tail -1 | tr -d '@')
    [ -n "$who" ] || continue
    ctx=$(grep -oE 'CTX [0-9]+%' <<<"$cap" | tail -1 | grep -oE '[0-9]+')
    if [ -z "$ctx" ]; then out="$out ${dim}?${rst}"
    else out="$out $(colour_for "$ctx")${ctx}${rst}"; fi
  done
  [ -n "$out" ] && printf '%s' " ${dim}|${rst}${out}"
  return 0
}

# Mirror the authoritative context figures to a per-session state file, so the
# UserPromptSubmit context-report hook can inject the SAME number the user sees
# here into the model's own context (one source, two consumers). Best-effort:
# the render must never break, and the figure is the exact one /context shows.
write_ctx_state() {
  "$JQ" -n --argjson u "${used:--1}" --argjson s "${csize:-0}" \
           --argjson i "${itok:-0}"  --arg     m "$model" \
    '{used_percentage:$u,context_window_size:$s,total_input_tokens:$i,model:$m}' \
    > "/tmp/cc-ctx-${sid}.json" 2>/dev/null || true
}

spd=$(speed_val)
tm=$(teammates_blurb)
write_ctx_state

if [ "${used%.*}" = "-1" ]; then
  pctpart="${dim}—${rst}"
else
  pct=$(awk "BEGIN{printf \"%d\", $used+0.5}"); [ "$pct" -gt 100 ] && pct=100
  pctpart="$(colour_for "$pct")${pct}%${rst}"
fi

printf '%s(%s)' "$model_short" "$pctpart"
[ -n "$effort" ] && printf ' %s%s%s' "$dim" "$effort" "$rst"
printf ' %s%s%s' "$dim" "$spd" "$rst"
printf '%s' "$tm"
