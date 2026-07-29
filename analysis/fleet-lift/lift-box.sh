#!/usr/bin/env bash
# Lift one registered instance onto a target commit, via the 06 selector only.
#
# Guard and action are one chain: the deploy runs only if the box checkout is
# already exactly at the target. A mismatch aborts and writes a marker; it never
# leaves the deploy to run.
#
# Usage: lift-box.sh <instance> <checkout-on-box> <target-sha>
set -u -o pipefail

INSTANCE=${1:?instance}
CHECKOUT=${2:?checkout path on the box}
TARGET=${3:?target sha}

MGMT=/Users/drnorden/projects/vpath/vpath_platform_mgmt
REG=$MGMT/instances.local.env
PY=$MGMT/.venv/bin/python
LOGD=$MGMT/analysis/fleet-lift/logs
LOG=$LOGD/$INSTANCE-deploy.log

export PYTHONPATH=$MGMT/src

sel() { "$PY" -m vpath_platform_mgmt.instances.selector --register "$REG" "$@"; }

mkdir -p "$LOGD"

# --- guard: the box must already carry the target commit -------------------
head_out=$(sel exec "$INSTANCE" -- "git -C $CHECKOUT rev-parse HEAD" 2>&1)
head_rc=$?
BOXHEAD=$(printf '%s' "$head_out" | tr -d '[:space:]')

if [ "$head_rc" -ne 0 ] || [ "$BOXHEAD" != "$TARGET" ]; then
  {
    echo "===ABORTED_GUARD==="
    echo "instance=$INSTANCE rc=$head_rc"
    echo "box_head=$BOXHEAD"
    echo "target  =$TARGET"
    echo "--- selector output ---"
    echo "$head_out"
  } >>"$LOG"
  exit 2
fi

# --- action ----------------------------------------------------------------
{
  echo "=== deploy start $(date -u +%FT%TZ) instance=$INSTANCE head=$BOXHEAD ==="
} >"$LOG"

sel --timeout 14400 gradle "$INSTANCE" -- \
  deployPipeline "-PvpathBuildId=$TARGET" >>"$LOG" 2>&1
rc=$?
echo "===EXIT=$rc===" >>"$LOG"
echo "=== deploy end $(date -u +%FT%TZ) ===" >>"$LOG"
exit "$rc"
