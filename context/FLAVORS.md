# Template Flavors — Using This Template Beyond Python

This template is written in its Python flavor. Most of it is **genuinely
language-agnostic**; a clearly bounded set of files is Python-specific and
must be substituted for a Java, Rust, or C++ project. This document marks
the boundary so a flavor never has to guess.

## Universal — identical in every flavor (do NOT change)

| Artifact | Why it's language-agnostic |
|----------|---------------------------|
| `.claude/skills/` (all seven skills) | Commit hygiene, root-cause analysis, durable fixes, UI verification, decision triage, CTO-briefing reporting — none assume Python |
| `CLAUDE.md` structure | Must-know map, skill habit, principles (no fallbacks, fail hard, 250-line files) apply to any language |
| `context/CHECKLIST.md` three-gate structure | Done → commit → release is universal; only the Gate-1 *commands* change (see below) |
| `CHANGELOG.md` + SemVer policy | Language-independent contract |
| `CONTRIBUTING.md` | Conventional commits, PR process |
| `context/MAIN_META_CONVENTION.md` | Two-tier rule is about repos, not languages |
| `context/RECOMMENDED_WAYS_OF_WORKING.md` | Gradle applies even more naturally to Java/C++ |
| `scripts/check_template_drift.py`, `scripts/sync_from_template.py` | They manage *files*, not the project language. They need a Python 3 interpreter as a tool — same as needing git. Keep them. |
| `githooks/pre-commit` + `.claude/settings.json` / `.claude/hooks/` | The pre-commit hook runs `make check` (the universal vocabulary), and the post-edit hook is flavor-aware by file extension — both identical on every branch |
| `scripts/scan_dependencies.py` + the `make scan` target | The CVE gate is flavor-aware by manifest detection (like the post-edit hook); recipe byte-identical on every branch — only the scan INPUT differs (see substitution table) |
| `.env.example` concept, README structure | Universal |

## Flavor-specific — the substitution table

| Concern | Python (this template) | Java | Rust | C++ |
|---------|------------------------|------|------|-----|
| Package manifest + version (source of truth) | `pyproject.toml` | `build.gradle.kts` (or `pom.xml`) | `Cargo.toml` | `CMakeLists.txt` (`project(... VERSION)`) |
| Dependency declaration | `pyproject` deps + `requirements.txt` mirror | Gradle dependencies + lockfile | `Cargo.toml` + `Cargo.lock` | Conan/vcpkg manifest + lockfile |
| Source layout | `src/<pkg>/` (src layout) | `src/main/java`, `src/test/java` | `src/`, `tests/` (Cargo convention) | `src/`, `include/`, `tests/` |
| Formatter | black | spotless / google-java-format | `cargo fmt` | clang-format |
| Linter | flake8 | Checkstyle / Error Prone | `cargo clippy -D warnings` | clang-tidy |
| Type/compile check | mypy | `javac` (compiler is the gate) | `rustc` (compiler is the gate) | compiler warnings-as-errors |
| Test runner | pytest | JUnit via Gradle | `cargo test` | GoogleTest/Catch2 via CTest |
| The full gate (`make check`) | black --check + flake8 + mypy + pytest | `gradle check` | `cargo fmt --check && cargo clippy -- -D warnings && cargo test` | configure + build (`-Werror`) + clang-format --dry-run + clang-tidy + ctest |
| CVE scan input (`make scan`) | frozen environment (`pip freeze`) | committed `gradle.lockfile` | `Cargo.lock` | `conan.lock` / `vcpkg.json` |
| CI matrix | Python 3.10–3.13 | JDK 17 / 21 | stable / beta toolchain | gcc / clang (+ MSVC if shipped on Windows) |
| Placeholder runnable | `vpath-hello` console script | `gradle run` application plugin | `cargo run` | binary target |
| Runtime config | `config/settings.py` + python-dotenv | typed config + dotenv lib | `figment`/`config` crate | env parsing lib |

## Files to replace vs. edit when creating a flavor

**Replace wholesale:** `src/`, `tests/`, `pyproject.toml`, `requirements.txt`,
`config/settings.py`, `.github/workflows/python-app.yml`, the Makefile
recipes (keep the target NAMES — `setup`, `check`, `scan`, `test`, `format`,
`lint`, `run`, `clean` — they are the universal vocabulary; only the commands
behind them change; `scan`'s recipe is byte-identical everywhere).

**Edit in place:** `CLAUDE.md` (Gate commands, dependency-management section,
structure block), `context/CHECKLIST.md` Gate 1 command, `README.md`
(quick start, structure), `.gitignore` (language section),
`scripts/init_project.py` (bootstrap steps).

**Keep verbatim:** everything in the Universal table above.

## The architecture: branch-per-flavor (adopted 2026-06-10)

Flavors live as **branches of this repository** (decision record 002 on the
`meta` branch; grounded in researched best practices — conditional
templating is a documented anti-pattern at 3+ languages, and no generator
tool matches our pristine-detection sync):

- `main` — the shared baseline in its Python flavor (this tree)
- `flavor/java`, `flavor/rust`, `flavor/cpp` — same baseline with the
  substitution table above applied; created on first need

How it works:

- **Stamping:** copy the tree of the flavor branch you need.
- **Sync:** the `.template-version` stamp records `<sha> <ref>`; the
  sync/drift scripts default to the stamped ref, so a Java project
  automatically compares against `flavor/java` — `TRACKED` needs no
  per-flavor editing (files absent on a flavor are skipped, and pristine
  detection runs against that branch's own history).
- **Maintenance:** universal changes land on `main` and are merged into
  each flavor branch (never the reverse); flavor-specific changes go to
  the flavor branch directly. The Makefile target NAMES are the contract
  that keeps `make check` meaning the same thing everywhere.
