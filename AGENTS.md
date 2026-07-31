# Project Context for AI Assistants

## Project Overview

Python project template with emphasis on clean, maintainable, AI-friendly
code. This file is the shared repository governance contract for coding
agents. Tool-specific adapters such as `CLAUDE.md`, `.claude/`, and `.codex/`
may add mechanics, but they must not duplicate or contradict these rules.

## Project Structure

```text
vpath_platform_mgmt/
├── src/                    # Main package source code (src layout)
│   └── vpath_platform_mgmt/  # Placeholder package (replace with real code)
├── tests/                  # Test files
├── config/                 # Configuration (settings.py reads .env)
├── context/                # Documentation and guidelines
├── scripts/                # Utility scripts
├── pyproject.toml          # Package metadata + tool config (single source)
└── requirements.txt        # Python runtime dependencies
```

Keep this tree current: update it in the same commit that changes the
structure. The pre-push gate verifies every path listed here exists.

## Hard Rules

- Max 250 lines per file; split into a subfolder module if larger.
- Type hints are required on all public functions; docstrings on public APIs.
- No comments unless critical; self-documenting names; no debug prints in
  commits. A deliberate simplification is critical: record it as one
  `# ponytail: <what was skipped>, <upgrade trigger>` marker.
- Cross-platform always: use `pathlib.Path` / `os.path.join()`, and
  `encoding="utf-8"` on file operations.
- Work in the files that exist; create one only when the task needs it. No
  unsolicited docs; deliver exactly the requested scope.
- Minimalism first: stdlib before native platform before existing dependency
  before new code. See `context/best_practices_short.md`.
- Every non-trivial change leaves a regression test that fails if reverted.
  Trivial one-liners, pure config, and pure deletions are exempt. Guards
  (validation, security, data-loss) are never simplified away and always tested.
- Coverage must stay at or above 85%; `make check` is the completion gate.
- No fallbacks, no soft passes, no silent degradation. Fail hard with a clear
  message; see `context/CHECKLIST.md` Gate 1.

## Dependencies

- `pyproject.toml` `[project.dependencies]` is the source of truth.
  `requirements.txt` is its mirror. Update both when adding a dependency.
- Every dependency change is CVE-scanned with `make scan`; the scan blocks
  CRITICAL/HIGH findings. A waiver in `.trivyignore.yaml` requires human
  confirmation, a justification, and an expiry of at most 90 days.

## Quick Checks

```bash
make check               # full gate, identical to CI
make format              # fix formatting failures
make scan                # required after dependency manifest changes
```

## Must-Know Map

Read the target when the task touches that area. Do not duplicate those rules
into tool-specific adapter files.

| Concern | Source of truth |
|---------|-----------------|
| Package metadata, version, tool config | `pyproject.toml` |
| Quality gate | `make check` / `Makefile` / `.github/workflows/python-app.yml` |
| Agent adapters and hooks | `CLAUDE.md`, `.claude/`, `.codex/`, `scripts/agent_hooks/` |
| Dependency CVE gate | `scripts/scan_dependencies.py` + `make scan` |
| Operational checklist | `context/CHECKLIST.md` |
| Changelog + versioning policy | `CHANGELOG.md` |
| Contribution and commit rules | `CONTRIBUTING.md` |
| Installing the console, connecting it | `docs/INSTALLING_THE_CONSOLE.md` |
| Adding a repository as an app | `docs/ADDING_AN_APP.md` |
| Agent workflow | `context/AGENT_WORKFLOW.md` |
| Design principles | `context/best_practices_short.md` |
| VPath naming + structure | `context/GENERAL_PROJECT_TEMPLATE.md` |
| Runtime configuration | `config/settings.py` + `.env.example` |
| New-project bootstrap | `scripts/init_project.py` |
| Template drift check / upgrade | `scripts/check_template_drift.py`, `scripts/sync_from_template.py`, `.template-version` |
| Recommended practices | `context/RECOMMENDED_WAYS_OF_WORKING.md` |
| Flavor system | `context/FLAVORS.md` |
| Evolution artifacts | `context/MAIN_META_CONVENTION.md` |

## Architecture And Requirements

Once this project develops a real domain model, consider OntoGate to manage
requirements and architecture. See `context/RECOMMENDED_WAYS_OF_WORKING.md`.

OntoGate status: not adopted. If this project adopts OntoGate, update the
adapter stamp in `CLAUDE.md` in the same change.
