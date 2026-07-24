---
name: careful-commit
description: Review all uncommitted changes and commit them in logical, atomic sets — with secrets and debug-code hygiene. Use when asked to commit, or when a work session ends with a dirty working tree.
---

Think hard, review all uncommitted changes, and check their relevance before committing anything.

## Steps

1. Run `git status` and `git diff` to see ALL uncommitted changes (staged and unstaged)
2. Read `git log --oneline -10` to match the repo's existing commit message style
3. Carefully analyze each changed file — understand what it does and why it changed
4. Group related changes into logical commit sets (e.g., "fix API routing", "update config schema", "fix CI workflow")
5. For any files that do NOT belong in the repo (build artifacts, temp files, local config, secrets, etc.) — add them to `.gitignore`
6. Everything that doesn't fit into a clear logical commit — leave uncommitted
7. Create each commit following the best practices below
8. After committing, run `git status` to show what remains uncommitted and why

## Commit Best Practices

### Message Format
- Use conventional commit prefixes: `fix:`, `feat:`, `refactor:`, `docs:`, `test:`, `chore:`, `build:`, `ci:`
- First line: imperative mood, max ~72 chars (e.g., "fix: filter terminated jobs from status list")
- If needed, add a blank line then a body explaining the WHY, not the what
- Match the existing commit style of the repo when one exists

### Atomic Commits
- Each commit should be ONE logical change that could be reverted independently
- Never mix unrelated changes (e.g., a bug fix + a new feature = 2 commits)
- Never mix formatting/whitespace changes with functional changes
- If a refactor is needed for a feature, commit the refactor first, then the feature

### What to Stage
- Stage files explicitly by name — never use `git add -A` or `git add .`
- Never commit secrets, credentials, `.env` files, API keys, or tokens
- Never commit build artifacts, `node_modules/`, `__pycache__/`, `dist/`, `venv/`
- Never commit OS files (`.DS_Store`, `Thumbs.db`)
- Never commit editor/IDE config unless shared by the team (`.idea/`, `.vscode/`)
- When in doubt about a file, leave it uncommitted and mention it in the summary

### Secrets Hygiene
- Scan every diff for hardcoded passwords, API keys, tokens, connection strings, private keys
- Watch for secrets hiding in: URLs (`https://user:pass@host`), env defaults (`os.getenv("KEY", "actual-secret")`), config objects, comments
- If a secret is found in a diff — revert that line, extract it to an env var or your secret store, and `.gitignore` the source file if needed
- Never commit `.env`, `.env.local`, `credentials.json`, `*.pem`, `*.key`, or config files with real secret values
- If a secret was already committed in a previous commit, warn the user — it needs to be rotated, not just removed

### Debug & Temp Code Hygiene
- Strip out all `console.log`, `print()`, `debugger`, `breakpoint()` statements added for debugging
- Remove commented-out code blocks that were used during development (e.g., `// TODO: remove`, `# HACK`, `# DEBUG`)
- Remove hardcoded `localhost`, `127.0.0.1`, test ports, or temp URLs that override real config
- Remove `sleep()` / `time.sleep()` calls added for manual testing timing
- Remove `skip` markers on tests (`@pytest.mark.skip`, `xit(`, `.skip(`) unless intentional
- Remove any `TODO` or `FIXME` comments that reference the current work — either fix them or leave them out
- If debug/temp code is found, revert those lines before staging — do NOT commit and "clean up later"

### Safety
- Commit infrastructure/config changes before code that depends on them
- Commit library/dependency changes before code that uses them
- Commit tests alongside (or just after) the code they test
