#!/usr/bin/env bash
# UserPromptSubmit hook — inject the REAL context-window fill into the model's
# context: the SAME figure the user sees in the status line. Source of truth is
# the per-session state file written by statusline-context.sh on each render
# (one source, two consumers: the user's status line and the model's context).
#
# Honest by construction. It reports only the measured figure. If none is
# available (status line not active in this project), it stays SILENT rather
# than guess — and the CLAUDE.md rule forbids estimating in that absence, so
# silence cannot degrade into an invented number. The status line rewrites the
# state on every render, so at prompt-submit time the figure is inherently fresh
# (session ids are unique, so a stale same-session file cannot occur).
set -euo pipefail
input="$(cat)"

JQ="$(command -v jq 2>/dev/null || true)"
if [ -z "$JQ" ]; then
  for c in /opt/homebrew/bin/jq /usr/local/bin/jq "$HOME/anaconda3/bin/jq" "$HOME/miniconda3/bin/jq"; do
    [ -x "$c" ] && JQ="$c" && break
  done
fi
[ -z "$JQ" ] && exit 0

sid="$("$JQ" -r '.session_id // empty' <<<"$input")"
[ -z "$sid" ] && exit 0

state="/tmp/cc-ctx-${sid}.json"
[ -f "$state" ] || exit 0

IFS=$'\037' read -r used csize itok model < <(
  "$JQ" -r '[ (.used_percentage      // -1),
              (.context_window_size  // 0),
              (.total_input_tokens   // 0),
              (.model                // "?")
            ] | map(tostring) | join("")' "$state"
)

human() {
  local n=$1
  case "$n" in (''|*[!0-9]*) n=0;; esac
  if   [ "$n" -ge 1000000 ]; then awk "BEGIN{printf \"%gM\", $n/1000000}"
  elif [ "$n" -ge 1000 ];    then awk "BEGIN{printf \"%dk\", $n/1000}"
  else                            printf '%s' "$n"; fi
}

pct="${used%.*}"
case "$pct" in (''|*[!0-9-]*) pct=-1;; esac

if [ "$pct" -lt 0 ]; then
  printf 'Context window: not yet measured this session (fresh, ~empty).'
else
  [ "$pct" -gt 100 ] && pct=100
  printf 'Context window: %s%% used — ~%s of %s tokens (%s). Real figure from the status line; do not estimate.' \
    "$pct" "$(human "$itok")" "$(human "$csize")" "${model%% *}"
fi
