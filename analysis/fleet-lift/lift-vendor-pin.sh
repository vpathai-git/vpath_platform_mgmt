#!/usr/bin/env bash
# Box precondition: advance the box-local vendored vpath_agents checkout onto the
# commit the target server commit pins (config/workflow-base-vpath-agents-pin.yaml).
#
# Why this is needed and why the pipeline's own printed remedy cannot be used:
# lib/vm.sh:2878 resolves the workflow-base vendor source as
# "$PROJECT_ROOT/vpath_agents". On a from-within NUC run PROJECT_ROOT is the box
# checkout, so the source is the box's own sibling clone. That clone sits on the
# previous pin, and it cannot fetch the new one: mars12/terra carry no `origin`
# remote at all, and mercury8/venus10 have one but the box holds no credential
# for the private repo. So `git fetch origin && git checkout <sha>` — the remedy
# the pipeline prints — cannot run there. The commit has to travel Mac -> box on
# the same delivery-push channel the server checkout already uses
# (server README use case 4b).
#
# The pipeline is NOT modified. This is a box precondition, in the sense of
# analysis/mars-install/REPORT-2026-07-28.md ("each was fixed as a box
# precondition, never in the pipeline").
#
# Guard and action are one chain throughout: nothing is pushed before the source
# is proven to be the pinned commit, and nothing is merged before the push landed.
#
# ORDER MATTERS — learned the hard way on venus10, 2026-07-29: run this AFTER the
# server commit has been delivered to the box, never before. The acceptance step
# is the pipeline's own verify-vpath-agents-pin.sh, and that compares the vendored
# HEAD against config/workflow-base-vpath-agents-pin.yaml *in the box checkout*.
# While the box still carries the old server commit, that file still names the old
# pin, so a correctly advanced vendored repo is reported as wrong. Deliver first,
# then run this.
#
# Usage: lift-vendor-pin.sh <instance> <checkout-on-box> <pinned-agents-sha>
set -u -o pipefail

INSTANCE=${1:?instance}
CHECKOUT=${2:?checkout path on the box}
PIN=${3:?pinned vpath_agents sha}

MGMT=/Users/drnorden/projects/vpath/vpath_platform_mgmt
REG=$MGMT/instances.local.env
PY=$MGMT/.venv/bin/python
SRC=/Volumes/T7/vpath/vpath_server_dev/vpath_agents
BRANCH="agents-pin-${PIN:0:12}"
VENDOR="$CHECKOUT/vpath_agents"

export PYTHONPATH=$MGMT/src

sel() { "$PY" -m vpath_platform_mgmt.instances.selector --register "$REG" "$@"; }

fail() { echo "ABORT: $*" >&2; exit 1; }

# --- guard 1: the Mac source really is the pinned commit -------------------
src_head=$(git -C "$SRC" rev-parse HEAD) || fail "cannot read $SRC"
[ "$src_head" = "$PIN" ] || fail "Mac source $SRC is at $src_head, not the pinned $PIN"
echo "guard1 OK: Mac source is exactly the pinned commit $PIN"

# --- guard 2: the box vendored repo is clean and behind --------------------
box_head=$(sel exec "$INSTANCE" -- "git -C $VENDOR rev-parse HEAD" | tr -d '[:space:]') \
  || fail "cannot read box vendored HEAD"
[ -n "$box_head" ] || fail "box vendored HEAD came back empty"
if [ "$box_head" = "$PIN" ]; then
  echo "guard2 OK: box vendored repo already at the pin — verifying, not assuming"
  sel exec "$INSTANCE" -- \
    "bash $CHECKOUT/platform_infra/docker/workflow-base/verify-vpath-agents-pin.sh \
       $VENDOR $CHECKOUT/config/workflow-base-vpath-agents-pin.yaml vendor_src" \
    || fail "the pipeline's own pin verifier says no — is the server commit delivered yet?"
  echo "verify2 OK: the pipeline's own verify-vpath-agents-pin.sh accepts the box copy"
  echo "CHAIN_OK $INSTANCE"
  exit 0
fi
dirty=$(sel exec "$INSTANCE" -- "git -C $VENDOR status --porcelain | wc -l" | tr -d '[:space:]')
[ "$dirty" = "0" ] || fail "box vendored repo has $dirty local modifications — not touching it"
echo "guard2 OK: box vendored repo at $box_head, clean"

# --- guard 3: the move is a fast-forward, never a rewrite ------------------
git -C "$SRC" merge-base --is-ancestor "$box_head" "$PIN" \
  || fail "$box_head is not an ancestor of $PIN — refusing anything but a fast-forward"
echo "guard3 OK: $box_head -> $PIN is a fast-forward"

# --- action: push onto a NON-current branch, then fast-forward there -------
# The register holds both halves; a bare `git push` would use the ssh DEFAULT key
# and fail on any instance whose key is not that default (terra, 2026-07-29:
# "Permission denied (publickey)"). This is the same gap the selector's own
# deliver has (selector.py:90-94 builds the push without -i, while
# transport.py:124-125 passes -i for exec/gradle) — filed as a finding, not
# patched there. Here we pass the registered key explicitly.
TARGET_INFO=$("$PY" - "$REG" "$INSTANCE" <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, "/Users/drnorden/projects/vpath/vpath_platform_mgmt/src")
from vpath_platform_mgmt.instances import registry
inst = registry.load(Path(sys.argv[1])).get(sys.argv[2])
print(inst.ssh_target)
print(inst.ssh_key or "")
PYEOF
) || fail "cannot resolve ssh target from the register"
SSH_TARGET=$(printf '%s\n' "$TARGET_INFO" | sed -n 1p)
SSH_KEY=$(printf '%s\n' "$TARGET_INFO" | sed -n 2p)
if [ -n "$SSH_KEY" ]; then
  [ -f "$SSH_KEY" ] || fail "registered ssh key for $INSTANCE does not exist"
  export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=12 -i $SSH_KEY"
fi

git -C "$SRC" push --no-verify "${SSH_TARGET}:${VENDOR}" "${PIN}:refs/heads/${BRANCH}" \
  || fail "push of the pinned commit into $VENDOR failed"
echo "action OK: pinned commit delivered as $BRANCH"

sel exec "$INSTANCE" -- \
  "cd $VENDOR && git merge --ff-only $BRANCH" \
  || fail "fast-forward on the box failed"

# --- verify: the pipeline's own verifier is the acceptance ----------------
new_head=$(sel exec "$INSTANCE" -- "git -C $VENDOR rev-parse HEAD" | tr -d '[:space:]')
[ "$new_head" = "$PIN" ] || fail "box vendored HEAD is $new_head, expected $PIN"
echo "verify1 OK: box vendored HEAD == $PIN"

sel exec "$INSTANCE" -- \
  "bash $CHECKOUT/platform_infra/docker/workflow-base/verify-vpath-agents-pin.sh \
     $VENDOR $CHECKOUT/config/workflow-base-vpath-agents-pin.yaml vendor_src" \
  || fail "the pipeline's own pin verifier still says no"
echo "verify2 OK: the pipeline's own verify-vpath-agents-pin.sh accepts the box copy"
echo "CHAIN_OK $INSTANCE"
