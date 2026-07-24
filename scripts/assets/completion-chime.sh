#!/usr/bin/env bash
# Claude Stop hook: play an audible completion chime.
set -u

SOUND="${CLAUDE_COMPLETION_CHIME_SOUND:-/System/Library/Sounds/Glass.aiff}"

if ! command -v afplay >/dev/null 2>&1; then
  echo "completion-chime: afplay not found; cannot play completion sound" >&2
  exit 2
fi

if [ ! -f "$SOUND" ]; then
  echo "completion-chime: sound file not found: $SOUND" >&2
  exit 2
fi

afplay "$SOUND" >/dev/null 2>&1 &
exit 0
