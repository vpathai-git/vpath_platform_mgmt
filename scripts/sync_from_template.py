#!/usr/bin/env python3
"""Pull template improvements into a project created from the template.

    python scripts/sync_from_template.py            # dry-run: show the plan
    python scripts/sync_from_template.py --apply    # copy new + update pristine
    python scripts/sync_from_template.py --merge    # also 3-way merge customized

Per tracked file (see check_template_drift.TRACKED) the script decides:

  up to date   identical to the latest template - nothing to do
  new          template has it, project doesn't            -> copied on --apply
  update       file matches SOME historical template
               version (pristine, just stale)              -> overwritten on --apply
  customized   content never shipped by the template       -> review; with --merge
               and a .template-version stamp: 3-way merge (conflict markers kept)
  removed      template deleted it; project copy pristine  -> deleted on --apply

Pristine-ness is exact, not heuristic: the project file's git blob hash is
searched in the template's full history, so projects that missed many
template iterations still classify correctly. After a fully clean run the
template commit is stamped into .template-version, enabling precise 3-way
merges of customized files later. Exit 0 = nothing left to do, 1 = pending
actions or review items, 2 = execution error.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import check_template_drift as drift


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        env=drift.GIT_CLEAN_ENV,
    )
    if result.returncode != 0:
        sys.exit(f"ERROR: git {' '.join(args)} failed:\n{result.stderr.decode()}")
    return result.stdout


def clone_full(repo: str, ref: str) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="template_sync_"))
    cmd = ["git", "clone", "--quiet", "--branch", ref, repo, str(tmp)]
    result = subprocess.run(
        cmd, capture_output=True, text=True, env=drift.GIT_CLEAN_ENV
    )
    if result.returncode != 0:
        shutil.rmtree(tmp, onerror=drift._on_rm_error)
        sys.exit(f"ERROR: could not clone {repo} (ref {ref}):\n{result.stderr}")
    return tmp


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def content_shas(data: bytes) -> set[str]:
    """Blob hashes to compare against git history: raw and LF-normalized.

    Git stores text blobs LF-normalized under autocrlf, so a pristine
    Windows checkout is CRLF on disk — it must still count as pristine,
    or sync misclassifies every unmodified file as custom.
    """
    shas = {blob_sha(data)}
    normalized = data.replace(b"\r\n", b"\n")
    if normalized != data:
        shas.add(blob_sha(normalized))
    return shas


def history_blobs(tmp: Path) -> dict[str, set[str]]:
    """Every blob hash the template ever shipped, per path (posix keys).

    Scoped to HEAD (the synced ref), NOT --all: other branches (e.g. the
    template's own meta branch) must not count as 'shipped' versions.
    """
    out = git(
        tmp, "log", "HEAD", "--raw", "--no-renames", "--no-abbrev", "--format="
    ).decode("utf-8", errors="replace")
    blobs: dict[str, set[str]] = {}
    for line in out.splitlines():
        if not line.startswith(":") or "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        for sha in meta.split()[2:4]:
            if sha.strip("0"):
                blobs.setdefault(path, set()).add(sha)
    return blobs


def base_bytes(tmp: Path, stamp_sha: str, path: str) -> bytes | None:
    probe = subprocess.run(
        ["git", "-C", str(tmp), "cat-file", "-e", f"{stamp_sha}:{path}"],
        capture_output=True,
        env=drift.GIT_CLEAN_ENV,
    )
    if probe.returncode != 0:
        return None
    return git(tmp, "show", f"{stamp_sha}:{path}")


def merge3(ours: Path, base: bytes, theirs: Path, workdir: Path) -> tuple[bytes, int]:
    """git merge-file 3-way merge; returns (merged content, conflict count).

    All three inputs are LF-normalized before merging: the base comes from
    git's object store (always LF) while Windows checkouts are CRLF — mixed
    endings would otherwise conflict on every line. The project file's
    ending style is restored on the merged result.
    """
    ours_raw = ours.read_bytes()
    uses_crlf = b"\r\n" in ours_raw
    ours_c = workdir / "ours"
    base_c = workdir / "base"
    theirs_c = workdir / "theirs"
    ours_c.write_bytes(ours_raw.replace(b"\r\n", b"\n"))
    base_c.write_bytes(base.replace(b"\r\n", b"\n"))
    theirs_c.write_bytes(theirs.read_bytes().replace(b"\r\n", b"\n"))
    result = subprocess.run(
        [
            "git",
            "merge-file",
            "-p",
            "-L",
            "project",
            "-L",
            "template(base)",
            "-L",
            "template(latest)",
            str(ours_c),
            str(base_c),
            str(theirs_c),
        ],
        capture_output=True,
        env=drift.GIT_CLEAN_ENV,
    )
    if result.returncode < 0:
        sys.exit(f"ERROR: merge failed for {ours}:\n{result.stderr.decode()}")
    merged = result.stdout
    if uses_crlf:
        merged = merged.replace(b"\n", b"\r\n")
    return merged, result.returncode


def removed_candidates(root: Path, latest: set[str]) -> list[str]:
    """Tracked files present locally but gone from the latest template."""
    extra: list[str] = []
    for entry in (e for e in drift.TRACKED if e.endswith("/")):
        for f in sorted((root / entry).rglob("*")) if (root / entry).is_dir() else []:
            rel = f.relative_to(root).as_posix()
            if f.is_file() and rel not in latest:
                if not set(f.parts) & drift.IGNORED_NAMES:
                    extra.append(rel)
    return extra


def classify(root: Path, tmp: Path) -> dict[str, list[str]]:
    blobs = history_blobs(tmp)
    latest = [p.as_posix() for p in drift.template_files(tmp)]
    plan: dict[str, list[str]] = {
        "same": [],
        "new": [],
        "update": [],
        "custom": [],
        "remove": [],
        "keep": [],
    }
    for rel in latest:
        local = root / rel
        if not local.is_file():
            plan["new"].append(rel)
        elif local.read_bytes() == (tmp / rel).read_bytes():
            plan["same"].append(rel)
        elif content_shas(local.read_bytes()) & blobs.get(rel, set()):
            plan["update"].append(rel)
        else:
            plan["custom"].append(rel)
    for rel in removed_candidates(root, set(latest)):
        if rel not in blobs:
            continue  # project-own file in a tracked dir — not ours to touch
        pristine = bool(content_shas((root / rel).read_bytes()) & blobs[rel])
        plan["remove" if pristine else "keep"].append(rel)
    return plan


def execute(
    root: Path, tmp: Path, plan: dict[str, list[str]], stamp: str | None, merge: bool
) -> list[str]:
    """Apply the plan; returns customized files left unresolved."""
    for rel in plan["new"] + plan["update"]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmp / rel, root / rel)
        print(f"  wrote   {rel}")
    for rel in plan["remove"]:
        (root / rel).unlink()
        print(f"  deleted {rel}")
    unresolved = list(plan["custom"])
    if merge and stamp:
        with tempfile.TemporaryDirectory() as wd:
            for rel in plan["custom"]:
                base = base_bytes(tmp, stamp, rel)
                if base is None:
                    print(f"  review  {rel} (no base at stamped version)")
                    continue
                merged, conflicts = merge3(root / rel, base, tmp / rel, Path(wd))
                (root / rel).write_bytes(merged)
                state = (
                    f"MERGED with {conflicts} conflict(s)" if conflicts else "merged"
                )
                print(f"  {state:<7} {rel}")
                if not conflicts:
                    unresolved.remove(rel)
    return unresolved


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    stamp, stamp_ref = drift.read_stamp(root)
    parser = argparse.ArgumentParser(
        description="Pull template improvements into this project."
    )
    parser.add_argument("--repo", default=drift.TEMPLATE_REPO_DEFAULT)
    parser.add_argument(
        "--ref",
        default=stamp_ref or "main",
        help="template flavor branch (default: the stamped ref, else main)",
    )
    parser.add_argument("--apply", action="store_true", help="perform safe actions")
    parser.add_argument(
        "--merge",
        action="store_true",
        help="with --apply: 3-way merge customized files (needs stamp)",
    )
    parser.add_argument(
        "--write-stamp",
        action="store_true",
        help="stamp template HEAD even if customized files remain",
    )
    args = parser.parse_args()

    stamp_path = root / drift.STAMP_FILE
    tmp = clone_full(args.repo, args.ref)
    try:
        head = git(tmp, "rev-parse", "HEAD").decode().strip()
        print(f"Template: {args.repo} @ {head[:10]} (ref {args.ref})")
        print(f"Stamp:    {stamp or 'none (first sync or pre-stamp project)'}\n")
        plan = classify(root, tmp)
        for kind, label in [
            ("new", "+ new      "),
            ("update", "^ update   "),
            ("custom", "! customized"),
            ("remove", "- removed  "),
            ("keep", "? removed-but-customized"),
        ]:
            for rel in plan[kind]:
                print(f"  {label} {rel}")
        actionable = plan["new"] or plan["update"] or plan["custom"] or plan["remove"]
        print(
            f"\n{len(plan['same'])} up to date, {len(plan['new'])} new, "
            f"{len(plan['update'])} to update, {len(plan['custom'])} customized, "
            f"{len(plan['remove']) + len(plan['keep'])} removed in template."
        )
        if not args.apply:
            if actionable:
                print("Dry-run only. Re-run with --apply (and optionally --merge).")
            return 1 if actionable else 0
        unresolved = execute(root, tmp, plan, stamp, args.merge)
        clean = not unresolved and not plan["keep"]
        if clean or args.write_stamp:
            stamp_path.write_text(f"{head} {args.ref}\n", encoding="utf-8")
            print(
                f"\nStamped {drift.STAMP_FILE} @ {head[:10]} ({args.ref}) "
                "— commit it with the sync."
            )
        else:
            print(
                f"\n{len(unresolved)} file(s) need review; stamp NOT updated "
                f"(reconcile, then re-run or use --write-stamp)."
            )
        return 0 if clean else 1
    finally:
        shutil.rmtree(tmp, onerror=drift._on_rm_error)


if __name__ == "__main__":
    sys.exit(main())
