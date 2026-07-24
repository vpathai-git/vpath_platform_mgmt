---
name: ponytail-audit
description: Read-only over-engineering scan that flags code minimalism could remove — bloat, needless abstractions, reinvented stdlib/native features, speculative options. Scans the working diff by default, or the whole repo with `--repo`. Use for a minimalism pass before committing, or a periodic whole-repo audit. Advisory only — it reports, it never edits and is never a gate. Adapted from ponytail (MIT); respects this project's test and guard rules.
---

Hunt over-engineering. The best code is the code you never wrote — this skill
finds code that should not have been written. It is **read-only**: it produces
a ranked list of findings, never edits, and is never a blocking gate (LLM
judgment is not deterministic, so it cannot be fail-hard machinery).

## When to use

- Before committing — a quick minimalism pass over the diff.
- Periodically — a whole-repo over-engineering audit (`--repo`).
- After a feature lands and feels heavier than it should.

## Scope

- **Default (no args):** the working diff — staged plus unstaged (`git diff HEAD`).
- **`--repo`:** the whole tracked codebase, findings ranked by lines saved.

## What to flag (over-engineering only — not bugs, not style)

Tag every finding with exactly one:

- `delete` — code or a feature that need not exist at all (YAGNI).
- `stdlib` — hand-rolled code the standard library already provides.
- `native` — a reinvented language / runtime / framework feature.
- `yagni` — speculative generality: options, hooks, or abstractions with one caller.
- `shrink` — works, but expressible in materially fewer lines without losing clarity.

## What you must NEVER flag for removal

- A regression test required by the test hard rule — non-trivial logic keeps its check.
- Input validation at a trust boundary, error handling that prevents data
  loss, or a security control. "Write less" never cuts a guard.
- Anything whose removal changes observable behavior — that is a bug, not bloat.

## Output — one line per finding, then a footer

```
<tag>  <file>:<line>  <what to remove and the smaller replacement>
...
net: -N lines, -M deps possible.
```

Rank by impact (lines saved) in `--repo` mode. Be specific and conservative:
if you are not certain code is dead or redundant, say so rather than assert it.
Findings are proposals for a human — this skill removes nothing itself.
