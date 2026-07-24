---
name: ponytail-sweep
description: Active, fan-out minimalism pass over the WHOLE repo. Distributes every file to parallel agents (one prompt, repeated), each of which reviews the file against the minimalism ladder, applies only the obvious behavior-preserving trims, stamps the file with a `ponytail <date>` review marker, and returns its findings — which are then collected race-free into a root `ponytail.md` ledger. The ACTIVE sibling of `/ponytail-audit` (which only reports and never edits). Use for a whole-repo minimalism sweep that leaves an auditable, per-file record and a reviewable git diff. Honors read-only / vendored / governed zones and never cuts a test or a guard. Adapted from ponytail (MIT).
---

A whole-repo minimalism sweep, parallelized. `/ponytail-audit` is the read-only
proposer; **this skill is the disposer's hand** — it still proposes (the
findings ledger), but it also (a) marks every file it reviewed so coverage is
visible in `git`, and (b) applies the trims that are too obvious to argue about.
The best code is the code you never wrote; this sweep removes a little of the
code that was.

It does this by **fan-out**: build the file list, hand each file (the same
prompt every time) to its own agent, let the agents work in parallel, then fold
their findings into one ledger. The work is mechanical per file but large in
aggregate — exactly the shape one context cannot hold, so distribute it.

## The doctrine it applies — the minimalism ladder

Single-source with `/ponytail-audit` and `context/best_practices_short.md`
(Decision 006). Before keeping any code, climb DOWN and stop at the first rung:
does it need to exist (YAGNI) → stdlib → native platform feature → an installed
dep → one line → minimal necessary code. Tag every finding with exactly one:

- `delete` — code/feature that need not exist at all.
- `stdlib` — hand-rolled code the standard library already provides.
- `native` — a reinvented language / runtime / framework feature.
- `yagni` — speculative generality: an option/hook/abstraction with one caller.
- `shrink` — works, but expressible in materially fewer lines without losing clarity.

**Never cut** (this is absolute — it overrides "write less"): a required
regression test, input validation at a trust boundary, error handling that
prevents data loss, a security control, or anything whose removal changes
observable behavior. Removing those is a bug, not a trim.

## Arguments

- `--agents N` — size of the fan-out (default ~20, or scale to the repo: aim
  for ~5–8 files per agent). The operator sets the ceiling; respect it.
- `--date YYYY-MM-DD` — marker date (default: today).
- `--mark-only` — review + mark + record findings, but apply **no** edits
  (turns the sweep into a marking audit). Default is mark + obvious trims.
- `--repo <path>` — target repo (default: the current repo).

## Procedure

0. **Understand the doctrine first.** Read `/ponytail-audit` and
   `best_practices_short.md` in the target repo so the lens is exact. A wrong
   understanding here is multiplied across every file — get it right once.
1. **Enumerate** tracked files: `git ls-files` (never walk `node_modules/` or
   build output).
2. **Classify** each file into one of three tiers (see *Classification* below).
   This is the safety step — it is what keeps the sweep from editing things it
   must not.
3. **Bucket** the `active`+`review-only` files into ≤ `--agents` cohesive
   work-units (sort by path so same-directory files share an agent — better
   cross-file judgment for `yagni`). Most units are a few files.
4. **Fan out** with the *one* per-file agent contract below (the same prompt for
   every agent — that uniformity is the point). Prefer the **Workflow tool**:
   structured returns, parallelism, and the per-file output stays out of the
   orchestrator's context. Agents edit *distinct* files, so no worktree
   isolation is needed; never let two agents touch one file.
5. **Collect race-free.** Agents **return** their findings; they do **not**
   append to the ledger. A **single writer** (the orchestrator, or one final
   collector agent) composes `ponytail.md`. Parallel appends to one file
   silently lose data — that is a fallback, and fallbacks are forbidden.
6. **Report**, don't commit. Summarize counts, net lines, and the top findings;
   leave the `git` diff and `ponytail.md` for the human. Committing is a
   separate, explicitly-requested step (`/careful-commit`). A green "it
   compiles" board is a precondition, not proof a trim was safe.

## Classification (the three tiers)

- **skip** — never touch: vendored / read-only substrate the repo declares
  (CLAUDE.md / README saying "read-only", "vendored", "refresh, never edit",
  `LOCKED`; `.gitattributes linguist-vendored`); lockfiles & generated output
  (`*-lock.*`, `*.lock`, `dist/`, `build/`, `.next/`); `LICENSE*`.
- **review-only** — review + record findings, but **no edit, no marker**:
  uncommentable formats (`*.json` and anything a leading comment would break);
  governed / machine-checked docs — files with a dated-assumption block
  (`validated:` + `review_horizon_days:`), the repo's own `CLAUDE.md`, baseline
  canon (`context/**`), CI (`.github/**`), editor config, git hooks. When in
  doubt whether a marker could trip a gate, treat the file as review-only.
- **active** — review + obvious trim + marker: everything else — your own source
  and author docs.

Record review-only and skipped files in the ledger with their reason. Skipping
silently would read as "covered everything" when it didn't — log what was left.

## Marker — syntax & placement

The marker is one line: `ponytail <date>`, in the file's comment syntax.

| File kind | Marker |
|-----------|--------|
| `.py .sh .yaml .yml .toml .txt .cfg .ini` Makefile | `# ponytail <date>` |
| `.ts .tsx .js .jsx .mjs .cjs .go .java .rs .c .cpp` | `// ponytail <date>` |
| `.css .scss` | `/* ponytail <date> */` |
| `.md .html` | `<!-- ponytail <date> -->` |
| `.json` and other uncommentable | none — file is review-only |

Placement (read the file first; the marker must not break syntax):
- Shebang (`#!…`) on line 1 → marker on **line 2**.
- `.md`/`.html` with YAML frontmatter (`---` … `---` at top) → **after the
  closing `---`** (a comment inside frontmatter breaks the YAML).
- A file opening with a single `---` YAML document marker → right after it.
- Otherwise → **line 1**.
- Idempotent: if a `ponytail <date>` marker is already present, do not add another.

## The per-file agent contract (reuse verbatim, one agent per file/bucket)

> You are applying the **ponytail minimalism sweep** to the files below in repo
> `{ROOT}`. Today is `{DATE}`. For **each** file:
> 1. Read it. Judge it against the minimalism ladder (delete / stdlib / native /
>    yagni / shrink). Produce specific, conservative findings — if you are not
>    certain code is dead or redundant, record it as a finding, do not act on it.
> 2. If `mode=active` **and** not `--mark-only`: apply ONLY trims that are
>    obvious and behavior-preserving (dead code, an unused import/var, a
>    reinvented one-liner the stdlib gives, a one-caller wrapper). When in
>    doubt, do not edit — just flag. NEVER weaken a test assertion, input
>    validation, error handling that prevents data loss, a security check, or
>    anything that changes observable behavior.
> 3. If `mode=active`: add the provided marker line at the correct position
>    (shebang→line 2; md/html frontmatter→after closing `---`; else line 1).
>    Use the exact marker string given for the file. Skip if already present.
> 4. If `mode=review`: do NOT edit and do NOT mark — only record findings.
> 5. Keep the repo's gate green: for `.py`, your edit MUST stay `black`- and
>    `flake8`-clean (≤88 cols) — a hook/CI runs them and will reject a dirty
>    edit; for `.sh`, stay `shellcheck`-clean; keep manifests valid YAML, keep
>    TS/TSX parseable, and introduce no color/palette literals. If a trim would
>    risk the gate, don't trim — flag it.
> Return structured output per file: `{path, mode, marked, marker_skipped_reason,
> fixes_applied:[{line,tag,summary}], findings:[{tag,line,what,replacement}],
> net_lines_saved, verdict: clean|fixed|flagged|fixed+flagged}`.
> Your returned object IS the result — do not address a human.

## `ponytail.md` (the ledger — append a dated section per run)

```
# ponytail sweep — <date>

Run: <N> agents, <files> reviewed (<active> active / <review-only> review-only /
<skipped> skipped). Marked: <M>. Trimmed: <T> files, net -<lines> lines.
Doctrine: the minimalism ladder (Decision 006). ponytail proposes, the gate disposes.

## Findings (proposals for a human)
<grouped by tag, then file:line — what to remove and the smaller replacement>

## Marked clean (reviewed, no change needed)
<files>

## Review-only / skipped (and why)
<file — reason>
```

## Notes

- The marker proves review; the trim is the bonus. Coverage (every file marked
  or logged) matters more than aggressive deletion.
- Default intensity is judgment-applied, not deletion-first. This skill is
  active where `/ponytail-audit` is read-only — so its guardrails are stricter,
  not looser: it may only edit what it is certain is safe.
- Do not commit. Surface the diff + ledger; let the human dispose (and run
  `/careful-commit` when they choose to).
