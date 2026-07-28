#!/usr/bin/env python3
"""OntoGate gate for vpath-workflow-demo — the app's Spine-3 filling the
app-hull foundation. FOUR-LAYER composition (per foundation/ADOPTION.md +
plan 2026-07-12 change 5):

  (1) the kit's vendored gatelib (stdlib-only): M10 freshness on the generated
      ontology.json + story_lint grammar + verdict pinning.
  (2) the FOUNDATION audit (kit foundation/audit) run against THIS app repo
      (READ-ONLY) — the 34 hull contracts as file checks.
  (3) app-specific stories over this catalog: a POSITIVE story per contract
      (asserts audit == pass) + a NEGATIVE story per break (applies a mutation
      to a SCRATCH COPY, asserts the named contract goes RED, discards the
      copy). The negative arm IS the red drill, woven into the gate.
  (4) the CONCEPT PLANE (concept_rules.py beside this file): the five starter
      rules R-A..R-E over the app-domain catalog (entities / concept docs /
      pins / story twins) + PIN/NEG/COV, with its own negative concept
      stories red-drilling each rule on scratch copies.

Run:  python3 examples/vpath-workflow-demo/.ontogate/check.py
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
sys.path.insert(0, str(HERE))  # the concept plane (R-A..R-E)
import gatelib  # noqa: E402
from audit import audit_index, run_audit, CONTRACT_IDS  # noqa: E402
from mutations import MUTATIONS  # noqa: E402
import concept_rules  # noqa: E402


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
    audit index over the MUTATED copy. The real app is never touched."""
    with tempfile.TemporaryDirectory(prefix="hull-reddrill-") as tmp:
        scratch = Path(tmp) / "app"
        shutil.copytree(
            app,
            scratch,
            ignore=shutil.ignore_patterns("node_modules", ".next", ".git"),
        )
        MUTATIONS[name](scratch)
        return audit_index(scratch)


def main():
    ont = gatelib.load(HERE, "ontology.json")
    book = gatelib.load(HERE, "usecases.json")
    missing = gatelib.check_model_keys(ont, "version", "extension_procedure")
    if missing:
        print("GATE ERROR: " + "; ".join(missing), file=sys.stderr)
        sys.exit(2)
    gatelib.check_freshness(ont, HERE)  # M10 provenance + skew — hard stop

    app = app_repo()
    real = audit_index(app)
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

    fails = [r.id for r in run_audit(app) if not r.ok]
    rows.append(
        (
            "APP",
            "PASS green" if not fails else "FAIL",
            f"real-app fails: {fails or 'none'}",
        )
    )

    # Layer 4 — the concept plane: R-A..R-E + PIN/NEG/COV over the app-domain
    # catalog, plus the negative concept stories (the concept red drill).
    # Hull stories feed the honest-green ledger (pinned as_is hull findings
    # must appear as hull_as_is pins in FINDINGS.md).
    crows, cmismatches = concept_rules.run(app, book["stories"])
    rows += crows
    mismatches += cmismatches

    n_stories = len(book["stories"]) + len(book.get("concept_stories", []))
    sys.exit(gatelib.finish(rows, n_stories, mismatches))


if __name__ == "__main__":
    main()
