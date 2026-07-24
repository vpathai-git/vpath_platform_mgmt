# The Checklist

The single canonical checklist for this project. It aggregates the former
release checklist, the CLAUDE.md quick checks, and the health-check questions
from the best-practices condensation. If a check matters, it is here — other
documents point here instead of keeping their own copies.

There are three gates, in increasing scope: **task done** → **commit** →
**release**. Each gate includes everything from the gates before it.

---

## Gate 1 — Definition of Done (every task)

Run the full quality gate — one command, same gate CI runs:

```bash
make check    # this flavor's full gate: formatting + lint/compile + types + tests
```

(Every flavor implements the same target with its own toolchain — Python:
black/flake8/mypy/pytest; Java: gradle check — see `context/FLAVORS.md`.)

Then verify by hand:

- [ ] No debug leftovers: `print()` debugging, commented-out code, temp scripts, `time.sleep()` timing hacks
- [ ] No soft passes introduced: no `|| true`, no `try/except: pass`, no warning-and-continue, no loosened assertions
- [ ] New/changed public functions have type hints and docstrings
- [ ] Files stay under 250 lines — split into a subfolder module if larger
- [ ] Cross-platform: `pathlib.Path` / `os.path.join()` for paths, `encoding="utf-8"` on all file operations (macOS AND Windows must work)
- [ ] New dependency? Declared in the manifest with a version constraint — Python: `pyproject.toml` `[project.dependencies]` AND its `requirements.txt` mirror; other flavors: `build.gradle.kts` / `Cargo.toml` / the CMake package manifest — AND `make scan` passes (pre-commit runs it automatically when a manifest is staged; CRITICAL/HIGH CVEs block). A waiver (`.trivyignore.yaml`: id + justification + expiry ≤90 days) requires a plain-language explanation of the CVE and the human's ACTIVE confirmation — never added autonomously
- [ ] Every non-trivial feature or bug fix has a regression test that fails if the change is reverted (trivial one-liners / pure config / pure deletions are exempt; guards at trust boundaries are never exempt)
- [ ] Minimalism pass (advisory, non-blocking): on a sizable diff, run `/ponytail-audit` and weigh its findings — the best code is the code you never wrote

## Gate 2 — Before committing

Use the `/careful-commit` skill — it enforces all of this:

- [ ] Changes grouped into atomic commits (one revertable logical change each)
- [ ] Conventional commit message: `feat:` / `fix:` / `docs:` / `chore:` / ..., imperative, ≤72 chars first line
- [ ] No secrets in any diff (keys, tokens, passwords, connection strings — also in URLs and env defaults)
- [ ] Nothing committed that belongs in `.gitignore` (artifacts, venvs, OS files, local config)

## Gate 3 — Before releasing

- [ ] Gate 1 and Gate 2 pass
- [ ] All main scripts run successfully from the project root
- [ ] Documentation (README, docs) reflects the changes; code examples updated and working
- [ ] The public API is still easy to explore (`help()` works, `__all__` is current)
- [ ] Version bumped per Semantic Versioning (breaking → MAJOR, feature → MINOR, fix → PATCH)
      in the manifest (source of truth — `pyproject.toml` / `build.gradle.kts` /
      `Cargo.toml` / `CMakeLists.txt`) AND any mirrored version constant
      (e.g. Python's package `__version__`) — they must match
- [ ] `CHANGELOG.md` updated: `[Unreleased]` items moved under the new version with date
- [ ] Package builds cleanly: `python -m pip install -e .` succeeds from a fresh venv
- [ ] CI is green on all supported Python versions — including the dependency CVE scan job
- [ ] Release commit tagged: `git tag v<version>`

## Health-check questions (periodic, not per-release)

Ask these when reviewing overall project quality:

- Can a new user get started in under 5 minutes?
- Does `help(your_function)` provide everything needed?
- Can you run the test suite with one command?
- Could you delete any feature without touching more than 2 files?
- Does the code work on both Windows and macOS/Linux?
- Can an AI understand your control flow without runtime execution?
- Are errors specific enough to search for?
- Could two instances with different configs coexist?
- Does every public function have a type signature?
- Is the "happy path" obvious without reading docs?
- Is `CLAUDE.md` still accurate — does every pointer in it resolve?
- Do tests exist before implementation?
- Can visual outputs be validated through screenshots (`/verify-ui`)?
