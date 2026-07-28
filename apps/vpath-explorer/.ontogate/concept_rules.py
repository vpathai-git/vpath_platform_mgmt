"""Concept-plane rules for a per-app OntoGate book — the five rules R-A..R-E.

Kit flavor of the baseline starter seed (vpath_empty_project
scripts/ontogate_starter/, plan 2026-07-12 Änderung 5): same rules, app-shaped
recipe, run by the SAME check.py as the hull audit (one book, one checker — M7).
Root-parameterized so one evaluation serves the real app AND mutated scratch
copies — the negative concept stories ARE the red drill. Stdlib-only, fail-hard:
a new violation fails, a silently disappeared one fails too.

  R-A  lockstep: every catalog entity named in the book ONTOLOGY.md; concept
       story ids and STORYBOOK.md tell the same set (both directions).
  R-B  catalog<->src bijection over the app's own source surface (api/**/*.py +
       src/**/*.ts|tsx; vendor/build/test trees excluded); declared deps ==
       observed app-internal imports.
  R-C  one docs/concepts/<kind>/<entity>.md per entity, complete frontmatter,
       indexed by the book ONTOLOGY.md; orphan docs are red.
  R-D  sha-pin permission lock: editing a validated concept doc without re-pin
       + dated extension record is red; a pin freezing a reverse_draft
       hypothesis is equally red.
  R-E  story-test twin: every positive concept story names a proof test that
       back-references its id; to_be stories carry a strict-xfail twin (born
       red), landed stories must not.

Plus PIN (gap<->pin ledger, both ways), NEG (each rule negatively exercised),
COV (every gap named on every run). Scratch evaluation deliberately skips M10
freshness — a mutation may edit generated artifacts to prove a rule fires.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

Row = tuple[str, str, str]

RULES = ("R-A", "R-B", "R-C", "R-D", "R-E")
ID_RE = r"\bKN?\d+\b"
DATE_RE = r"\d{4}-\d{2}-\d{2}"
SKIP_PARTS = {
    "node_modules",
    ".next",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "build",
    "tests",
    "test",
}
SCRATCH_IGNORE = (
    "node_modules",
    ".next",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "*.egg-info",
)


def fail(msg: str) -> None:
    print(f"GATE ERROR: {msg}", file=sys.stderr)
    sys.exit(2)


def _book(root: Path) -> Path:
    return root / ".ontogate"


def _load(root: Path, name: str) -> dict[str, Any]:
    path = _book(root) / name
    if not path.is_file():
        fail(f"missing artifact: {name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _prose(root: Path, name: str) -> str:
    path = _book(root) / name
    if not path.is_file():
        fail(f"missing artifact: {name}")
    return path.read_text(encoding="utf-8")


def _frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fm
        key, sep, value = line.partition(":")
        if sep:
            fm[key.strip()] = value.strip()
    return fm


def _row(rid: str, problems: list[str], ok_detail: str) -> Row:
    return (rid, "FAIL", "; ".join(problems)) if problems else (rid, "PASS", ok_detail)


def _verdict(found: list[str], expected: list[str]) -> tuple[bool, str, str]:
    f, e = sorted(set(found)), sorted(set(expected))
    if f == e:
        return True, "PASS", f"({len(e)} expected) " + "; ".join(e)
    return False, "FAIL", f"expected={e} found={f}"


def _entities(root: Path) -> dict[str, dict[str, Any]]:
    return _load(root, "ontology.json").get("entities") or {}


def _stories(root: Path) -> list[dict[str, Any]]:
    stories = _load(root, "usecases.json").get("concept_stories")
    if stories is None:
        fail("usecases.json: concept_stories missing (declare [], never omit)")
    seen: set[str] = set()
    for s in stories:
        for field in ("id", "polarity", "expected_violations"):
            if field not in s:
                fail(f"concept story {s.get('id', '<no-id>')}: missing {field}")
        if s["id"] in seen:
            fail(f"concept story id duplicated: {s['id']}")
        seen.add(s["id"])
        if s["polarity"] == "positive" and "proof" not in s:
            fail(f"concept story {s['id']}: positive without proof")
        if s["polarity"] == "negative" and "mutation" not in s:
            fail(f"concept story {s['id']}: negative without mutation")
    return stories


def _doc_rel(name: str, ent: dict[str, Any]) -> Path:
    return Path("docs", "concepts", str(ent.get("kind", "module")), f"{name}.md")


def _docs(root: Path) -> dict[str, tuple[Path, dict[str, str] | None]]:
    docs = {}
    for name, ent in _entities(root).items():
        rel = _doc_rel(name, ent)
        path = root / rel
        docs[name] = (rel, _frontmatter(path) if path.is_file() else None)
    return docs


def src_files(root: Path) -> set[Path]:
    """The app-own source surface the catalog must biject with."""
    out: set[Path] = set()
    for base, suffixes in (("api", (".py",)), ("src", (".ts", ".tsx"))):
        d = root / base
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            rel = p.relative_to(root)
            if (
                p.is_file()
                and p.suffix in suffixes
                and not (set(rel.parts) & SKIP_PARTS)
                and not any(part.endswith(".egg-info") for part in rel.parts)
            ):
                out.add(rel)
    return out


def _resolve(root: Path, cand: str, endings: tuple[str, ...]) -> Path | None:
    for end in endings:
        rel = Path(posixpath.normpath(cand + end))
        if (root / rel).is_file():
            return rel
    return None


def _observed_deps(root: Path, rel: Path, by_path: dict[Path, str]) -> set[str]:
    """App-internal imports actually present in one source file."""
    text = (root / rel).read_text(encoding="utf-8")
    parent = rel.parent.as_posix()
    found: set[str] = set()
    if rel.suffix == ".py":
        for dots, mod in re.findall(r"^from (\.*)([\w.]+) import", text, re.M):
            tail = "/".join(mod.split("."))
            bases = (
                [f"{parent}/{tail}"]
                if dots
                else [f"api/src/{tail}", f"{parent}/{tail}"]
            )
            for base in bases:
                hit = _resolve(root, base, (".py", "/__init__.py"))
                if hit and hit != rel:
                    found.add(by_path.get(hit, f"?{hit.as_posix()}"))
                    break
    else:
        for spec in re.findall(r'from\s+"([^"]+)"', text):
            if spec.startswith("@/"):
                base = "src/" + spec[2:]
            elif spec.startswith("."):
                base = f"{parent}/{spec}"
            else:
                continue
            hit = _resolve(root, base, (".ts", ".tsx", "/index.ts", "/index.tsx"))
            if hit and hit != rel:
                found.add(by_path.get(hit, f"?{hit.as_posix()}"))
    return found


def lockstep_row(root: Path) -> Row:
    ontology = _prose(root, "ONTOLOGY.md")
    storybook = _prose(root, "STORYBOOK.md")
    problems = [
        f"entity-not-in-ONTOLOGY:{n}" for n in _entities(root) if n not in ontology
    ]
    machine = {s["id"] for s in _stories(root)}
    told = set(re.findall(ID_RE, storybook))
    problems += [f"story-not-in-STORYBOOK:{i}" for i in sorted(machine - told)]
    problems += [f"story-only-in-STORYBOOK:{i}" for i in sorted(told - machine)]
    return _row("R-A", problems, "catalog, ONTOLOGY.md and STORYBOOK.md in lockstep")


def bijection_row(root: Path) -> Row:
    entities = _entities(root)
    declared = {Path(e["path"]): n for n, e in entities.items()}
    observed = src_files(root)
    problems = [
        f"path-missing:{p.as_posix()}" for p in sorted(set(declared) - observed)
    ]
    problems += [f"ungoverned:{p.as_posix()}" for p in sorted(observed - set(declared))]
    for name, ent in entities.items():
        rel = Path(ent["path"])
        if ent.get("resolution") != "mapped" or not (root / rel).is_file():
            continue
        got = _observed_deps(root, rel, declared)
        want = set(ent.get("deps", []))
        if got != want:
            problems.append(f"{name}: declared={sorted(want)} observed={sorted(got)}")
    return _row("R-B", problems, "catalog<->src bijection; declared==observed imports")


def concept_row(root: Path) -> Row:
    index = _prose(root, "ONTOLOGY.md")
    docs = _docs(root)
    problems: list[str] = []
    for name, (rel, fm) in docs.items():
        if fm is None:
            problems.append(f"missing-doc:{rel.as_posix()}")
            continue
        if fm.get("entity") != name:
            problems.append(f"frontmatter-entity-mismatch:{name}")
        if fm.get("status") not in ("validated", "reverse_draft"):
            problems.append(f"bad-status:{name}")
        if "stories" not in fm or "tests" not in fm:
            problems.append(f"incomplete-frontmatter:{name}")
        if fm.get("status") == "validated" and not re.fullmatch(
            DATE_RE, fm.get("validated", "")
        ):
            problems.append(f"validated-without-date:{name}")
        if rel.as_posix() not in index:
            problems.append(f"not-indexed-in-ONTOLOGY:{name}")
    expected = {root / rel for rel, _fm in docs.values()}
    concepts = root / "docs" / "concepts"
    if concepts.is_dir():
        for p in sorted(concepts.rglob("*.md")):
            if p not in expected:
                problems.append(f"orphan-doc:{p.relative_to(root).as_posix()}")
    return _row("R-C", problems, f"{len(docs)} entities <-> concept docs, all indexed")


def lock_row(root: Path) -> Row:
    ontology = _prose(root, "ONTOLOGY.md")
    docs = _docs(root)
    pins = _load(root, "ontology.json").get("concept_pins") or {}
    problems = [f"stale-pin:{n}" for n in sorted(set(pins) - set(docs))]
    for name, (rel, fm) in docs.items():
        if fm is None:
            continue
        if fm.get("status") != "validated":
            if name in pins:
                problems.append(f"pin-freezes-hypothesis:{name}")
            continue
        pin = pins.get(name)
        if not pin:
            problems.append(f"unpinned-validated:{name}")
            continue
        # EOL-normalized like the baseline's pinned_sha: autocrlf checkouts
        # materialize committed LF as CRLF; the pin must survive that, or
        # every pristine Windows clone goes red.
        digest = hashlib.sha256(
            (root / rel).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        if digest != pin.get("sha256"):
            problems.append(f"edited-without-repin:{name}")
        approved = str(pin.get("approved", ""))
        if not re.fullmatch(DATE_RE, approved):
            problems.append(f"pin-without-dated-approval:{name}")
        elif not any(approved in ln and name in ln for ln in ontology.splitlines()):
            problems.append(f"repin-without-extension-record:{name}")
    return _row("R-D", problems, f"{len(pins)} validated concepts sha-locked")


def twin_row(root: Path) -> Row:
    problems: list[str] = []
    positives = [s for s in _stories(root) if s["polarity"] == "positive"]
    for s in positives:
        sid, proof = s["id"], s["proof"]
        path = root / proof
        if not path.is_file():
            problems.append(f"{sid}:missing-test:{proof}")
            continue
        text = path.read_text(encoding="utf-8")
        if sid not in text:
            problems.append(f"{sid}:test-omits-backref:{proof}")
        elif s.get("status") == "to_be" and "xfail" not in text:
            problems.append(f"{sid}:to-be-story-needs-xfail-twin:{proof}")
        elif s.get("status") != "to_be" and "xfail" in text:
            problems.append(f"{sid}:landed-story-still-xfail:{proof}")
    return _row("R-E", problems, f"{len(positives)} positive stories twinned")


def gaps(root: Path, hull_gaps: set[str]) -> set[str]:
    g = set(hull_gaps)
    g |= {
        f"unmapped:{n}"
        for n, e in _entities(root).items()
        if e.get("resolution") != "mapped"
    }
    g |= {
        f"reverse_draft:{n}"
        for n, (_rel, fm) in _docs(root).items()
        if fm and fm.get("status") == "reverse_draft"
    }
    g |= {f"to_be:{s['id']}" for s in _stories(root) if s.get("status") == "to_be"}
    return g


def pin_row(root: Path, hull_gaps: set[str]) -> Row:
    open_gaps = gaps(root, hull_gaps)
    pinned = set(re.findall(r"^- PIN (\S+)", _prose(root, "FINDINGS.md"), re.M))
    problems = [f"gap-without-pin:{x}" for x in sorted(open_gaps - pinned)]
    problems += [f"pin-without-gap:{x}" for x in sorted(pinned - open_gaps)]
    return _row("PIN", problems, f"{len(open_gaps)} open gaps, every one pinned")


def neg_row(root: Path) -> Row:
    exercised: set[str] = set()
    for s in _stories(root):
        if s["polarity"] == "negative":
            exercised |= set(s["expected_violations"])
    missing = [r for r in RULES if r not in exercised]
    return _row(
        "NEG",
        [f"rule-never-rejected:{r}" for r in missing],
        "R-A..R-E negatively exercised",
    )


def coverage_detail(root: Path, hull_gaps: set[str]) -> str:
    entities = _entities(root)
    unmapped = sorted(n for n, e in entities.items() if e.get("resolution") != "mapped")
    parts = [f"{len(entities) - len(unmapped)}/{len(entities)} entities mapped"]
    named = gaps(root, hull_gaps) - {f"unmapped:{n}" for n in unmapped}
    if unmapped:
        parts.append("unmapped: " + ", ".join(unmapped))
    if named:
        parts.append("; ".join(sorted(named)))
    return "; ".join(parts)


# --------------------------------------------------------------------------- #
# Mutations — adaptive, data-driven deliberate breaks for the negative concept
# stories. Applied to a SCRATCH COPY only; each must flip exactly its rule red.
# --------------------------------------------------------------------------- #
def _first_entity(root: Path) -> str:
    entities = _entities(root)
    if not entities:
        fail("mutation needs at least one catalog entity")
    return sorted(entities)[0]


def _mut_detach_ontology_name(root: Path) -> None:
    """R-A (+R-C index cascade): the first entity name vanishes from prose."""
    name = _first_entity(root)
    p = _book(root) / "ONTOLOGY.md"
    p.write_text(
        p.read_text(encoding="utf-8").replace(name, "detached-entity"),
        encoding="utf-8",
    )


def _mut_rogue_source(root: Path) -> None:
    """R-B: a source file lands outside the catalog."""
    if (root / "api" / "src").is_dir():
        (root / "api" / "src" / "zz_rogue.py").write_text(
            "ROGUE = 1\n", encoding="utf-8"
        )
    elif (root / "src").is_dir():
        (root / "src" / "zz_rogue.ts").write_text(
            "export const rogue = 1;\n", encoding="utf-8"
        )
    else:
        fail("mutation rogue-source: app has neither api/src nor src")


def _mut_delete_concept_doc(root: Path) -> None:
    """R-C: an entity loses its concept doc."""
    name = _first_entity(root)
    doc = root / _doc_rel(name, _entities(root)[name])
    if not doc.is_file():
        fail(f"mutation delete-concept-doc: target missing {doc}")
    doc.unlink()


def _mut_break_permission_lock(root: Path) -> None:
    """R-D, adaptive: edit a pinned validated doc without re-pin — or, where
    none exists (brownfield), pin a reverse_draft hypothesis."""
    pins = _load(root, "ontology.json").get("concept_pins") or {}
    for name, (rel, fm) in sorted(_docs(root).items()):
        if fm and fm.get("status") == "validated" and name in pins:
            p = root / rel
            p.write_text(
                p.read_text(encoding="utf-8") + "\ntampered without re-pin\n",
                encoding="utf-8",
            )
            return
    ont = _load(root, "ontology.json")
    ont.setdefault("concept_pins", {})[_first_entity(root)] = {
        "sha256": "0" * 64,
        "approved": "2026-01-01",
    }
    (_book(root) / "ontology.json").write_text(
        json.dumps(ont, indent=2) + "\n", encoding="utf-8"
    )


def _mut_detach_story_proof(root: Path) -> None:
    """R-E: the first positive story's proof test forgets its story id."""
    positives = [s for s in _stories(root) if s["polarity"] == "positive"]
    if not positives:
        fail("mutation detach-story-proof: no positive concept story")
    proof = root / positives[0]["proof"]
    if not proof.is_file():
        fail(f"mutation detach-story-proof: proof missing {proof}")
    proof.write_text("# proof detached from its story\n", encoding="utf-8")


MUTATIONS = {
    "detach-ontology-name": _mut_detach_ontology_name,
    "rogue-source": _mut_rogue_source,
    "delete-concept-doc": _mut_delete_concept_doc,
    "break-permission-lock": _mut_break_permission_lock,
    "detach-story-proof": _mut_detach_story_proof,
}


def rule_rows(root: Path, hull_gaps: set[str]) -> list[Row]:
    return [
        lockstep_row(root),
        bijection_row(root),
        concept_row(root),
        lock_row(root),
        twin_row(root),
        pin_row(root, hull_gaps),
        neg_row(root),
    ]


def _scratch_found(root: Path, mutation: str, hull_gaps: set[str]) -> list[str]:
    if mutation not in MUTATIONS:
        fail(f"unknown concept mutation: {mutation}")
    with tempfile.TemporaryDirectory(prefix="concept-reddrill-") as tmp:
        scratch = Path(tmp) / "app"
        shutil.copytree(root, scratch, ignore=shutil.ignore_patterns(*SCRATCH_IGNORE))
        MUTATIONS[mutation](scratch)
        return [
            rid
            for rid, label, _detail in rule_rows(scratch, hull_gaps)
            if label == "FAIL" and rid in RULES
        ]


def run(root: Path, hull_stories: list[dict[str, Any]]) -> tuple[list[Row], int]:
    """All concept-plane rows for the real app + the negative-story red drill.

    hull_stories feed the honest-green ledger: a positive hull story with
    pinned expected_violations is an as_is finding and must appear as a
    `hull_as_is:<contract>` pin in FINDINGS.md.
    """
    hull_gaps = {
        f"hull_as_is:{cid}"
        for s in hull_stories
        if s.get("polarity") == "positive"
        for cid in s.get("expected_violations", [])
    }
    rows = rule_rows(root, hull_gaps)
    mismatches = sum(1 for _rid, label, _d in rows if label != "PASS")
    for story in _stories(root):
        if story["polarity"] != "negative":
            continue
        found = _scratch_found(root, story["mutation"], hull_gaps)
        ok, label, detail = _verdict(found, story["expected_violations"])
        mismatches += 0 if ok else 1
        rows.append((story["id"], label, detail))
    rows.append(("COV", "INFO", coverage_detail(root, hull_gaps)))
    return rows, mismatches
