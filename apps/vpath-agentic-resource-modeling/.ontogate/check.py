#!/usr/bin/env python3
"""OntoGate gate for vpath-agentic-resource-modeling — the app's Spine-3 filling
the app-hull foundation, with the NEED face filled FOR REAL. THREE-LAYER
composition (per foundation/ADOPTION.md):

  (1) the kit's vendored gatelib (stdlib-only): M10 freshness on the generated
      ontology.json + story_lint grammar + verdict pinning.
  (2) the FOUNDATION audit (kit foundation/audit) run against THIS app repo
      (READ-ONLY) — the 34 hull contracts as file checks.
  (3) app-specific stories over this catalog: a POSITIVE story per contract +
      a NEGATIVE story per break (the red drill, woven into the gate).

PLUS an APP-STRICT NEED override. The foundation audit is LENIENT on the NEED
face by design (an absent need reads as 'unused' -> pass; the spine docstring
says "an under-declared real need is caught by the per-app story, not silently
here"). Because THIS app's Spine-3 DECLARES the agent-provider need
(need.resource_requirements.declared: true), the gate enforces it strictly: the
root manifest MUST carry resourceRequirements, or C-need-resource-requirements
goes RED. That strict check is what the N07 red-drill (delete-resource-requirements)
flips — making the DECLARED need binding (the whole point of this example).

Run:  python3 examples/vpath-agentic-resource-modeling/.ontogate/check.py
No soft pass: a positive story whose contract fires, OR a negative story whose
mutation fails to turn the named contract red, is a MISMATCH (exit 1). gatelib
freshness/skew is a hard stop (exit 2).
"""

import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT_ROOT = HERE.parents[2]
FOUNDATION = KIT_ROOT / "foundation"
sys.path.insert(0, str(FOUNDATION / "_vendor"))  # vendored gatelib (stdlib)
sys.path.insert(0, str(FOUNDATION))  # the foundation `audit` package
sys.path.insert(0, str(HERE / "tests"))  # the red-drill mutation fixtures
import gatelib  # noqa: E402
from audit import Result, audit_index, CONTRACT_IDS  # noqa: E402
from audit.helpers import has_key, manifest_text  # noqa: E402
from mutations import MUTATIONS  # noqa: E402

# The NEED face this app's Spine-3 declares as REAL (manifest must carry it).
# id -> (dotted manifest key, human label).
APP_STRICT_NEEDS = {
    "C-need-resource-requirements": ("resourceRequirements", "agent-provider"),
}


def app_strict_need(cid, app):
    """Strict per-app NEED check: the declared need MUST be in the root manifest.

    Returns a Result that FIRES (fail) when the manifest lacks the key — the
    foundation audit alone never fires this (it is lenient on NEED), so this
    override is what makes the DECLARED need binding (and what N07 flips RED)."""
    key, label = APP_STRICT_NEEDS[cid]
    text = manifest_text(app)
    if has_key(text, key):
        return Result(
            cid, "need", "pass", f"{label} need DECLARED via {key} (app-strict)"
        )
    return Result(
        cid,
        "need",
        "fail",
        f"Spine-3 declares the {label} need but the manifest lacks {key} (app-strict)",
    )


def indexed(app):
    """The foundation audit index with the app-strict NEED overrides applied."""
    idx = dict(audit_index(app))
    for cid in APP_STRICT_NEEDS:
        idx[cid] = app_strict_need(cid, app)
    return idx


def app_repo():
    """Resolve the audit target from spine.yaml model.app_repo (relative to
    this .ontogate dir, OR absolute) — the READ-ONLY app repo."""
    spine = (HERE / "spine.yaml").read_text(encoding="utf-8")
    rel = next(
        line.split("app_repo:")[1].strip()
        for line in spine.splitlines()
        if line.strip().startswith("app_repo:")
    )
    p = Path(rel)
    if not p.is_absolute():
        p = HERE / rel
    p = p.resolve()
    if not p.exists():
        sys.exit(f"GATE ERROR: app repo not found at {p}")
    return p


def run_mutation(app, name):
    """Copy the app to a scratch dir, apply the mutation there, return the
    indexed audit (with app-strict overrides) over the MUTATED copy. The real
    app is never touched."""
    with tempfile.TemporaryDirectory(prefix="hull-reddrill-") as tmp:
        scratch = Path(tmp) / "app"
        shutil.copytree(
            app,
            scratch,
            ignore=shutil.ignore_patterns("node_modules", ".next", ".git"),
        )
        MUTATIONS[name](scratch)
        return indexed(scratch)


def main():
    ont = gatelib.load(HERE, "ontology.json")
    book = gatelib.load(HERE, "usecases.json")
    missing = gatelib.check_model_keys(ont, "version", "extension_procedure")
    if missing:
        print("GATE ERROR: " + "; ".join(missing), file=sys.stderr)
        sys.exit(2)
    gatelib.check_freshness(ont, HERE)  # M10 provenance + skew — hard stop

    app = app_repo()
    real = indexed(app)
    rows, mismatches, exercised = [], 0, set()

    cat = sorted(ont["contracts"].keys())
    ok, _, detail = gatelib.verdict(cat, CONTRACT_IDS)
    mismatches += 0 if ok else 1
    rows.append(("CAT", "PASS catalog=34" if ok else "MISMATCH", detail))

    ok, row = gatelib.method_version_row(ont)  # F5: method_version == generated_with
    mismatches += 0 if ok else 1
    rows.append(row)

    for story in book["stories"]:
        cid = story["steps"][0]["contract"]
        exercised.add(cid)
        if story["polarity"] == "positive":
            r = real[cid]
            found = [] if r.ok else [cid]
        else:  # negative — mutate a scratch copy, expect the contract RED
            mut = run_mutation(app, story["mutation"])
            r = mut[cid]
            found = [cid] if not r.ok else []
        ok, label, _ = gatelib.verdict(found, story["expected_violations"])
        mismatches += 0 if ok else 1
        ev = r.evidence if not r.ok else "pass"
        rows.append((story["id"], label, f"{cid}: {ev[:54]}"))

    ok, row = gatelib.story_lint(book)
    mismatches += 0 if ok else 1
    rows.append(row)

    dead = sorted(set(CONTRACT_IDS) - exercised)
    if dead:
        mismatches += 1
        rows.append(("M4", "FAIL", f"contracts never storied: {', '.join(dead)}"))
    else:
        rows.append(("M4", "PASS", f"all {len(CONTRACT_IDS)} contracts storied"))

    ok, row = gatelib.unguarded_row(ont, CONTRACT_IDS)  # UNG: rules held by discipline
    mismatches += 0 if ok else 1
    rows.append(row)

    # SEAM (M13, 0.10.27; row 0.10.30): the FORCED requirement-seam
    # declaration, verified LINK-ONLY — block present, status valid, and for
    # `n/a` the dated decision record resolves (file exists, anchor found).
    # This book declares `n/a`; the record it points at is the decision.
    ok, row = gatelib.requirement_seam_row(ont, HERE)
    mismatches += 0 if ok else 1
    rows.append(row)

    fails = [cid for cid, r in real.items() if not r.ok]
    rows.append(
        (
            "APP",
            "PASS green" if not fails else "FAIL",
            f"real-app fails: {fails or 'none'}",
        )
    )

    sys.exit(gatelib.finish(rows, len(book["stories"]), mismatches))


if __name__ == "__main__":
    main()
