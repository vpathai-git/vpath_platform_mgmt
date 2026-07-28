#!/usr/bin/env bash
# Claude Stop hook: play an audible completion chime (macOS / Windows / Linux).
# Cosmetic quality hook: always exit 0 — a missing player is a silent no-op,
# never a per-Stop error that trains the operator to ignore hook output.
set -u

case "$(uname -s)" in
  Darwin)
    SOUND="${CLAUDE_COMPLETION_CHIME_SOUND:-/System/Library/Sounds/Glass.aiff}"
    if command -v afplay >/dev/null 2>&1 && [ -f "$SOUND" ]; then
      afplay "$SOUND" >/dev/null 2>&1 &
    fi
    ;;
  MINGW*|MSYS*|CYGWIN*)
    SOUND="${CLAUDE_COMPLETION_CHIME_SOUND:-C:\\Windows\\Media\\chimes.wav}"
    PS=""
    if command -v powershell.exe >/dev/null 2>&1; then PS="powershell.exe"
    elif command -v pwsh >/dev/null 2>&1; then PS="pwsh"
    fi
    if [ -n "$PS" ]; then
      "$PS" -NoProfile -NonInteractive -Command \
        "(New-Object Media.SoundPlayer '$SOUND').PlaySync()" >/dev/null 2>&1 &
    fi
    ;;
  *)
    SOUND="${CLAUDE_COMPLETION_CHIME_SOUND:-/usr/share/sounds/freedesktop/stereo/complete.oga}"
    for player in paplay aplay; do
      if command -v "$player" >/dev/null 2>&1; then
        "$player" "$SOUND" >/dev/null 2>&1 &
        break
      fi
    done
    ;;
esac
exit 0
