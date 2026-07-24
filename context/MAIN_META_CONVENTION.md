# Repository Convention: Where Project-Evolution Artifacts Live

Every project accumulates artifacts about its own evolution: analysis
documents, todo boards, decision records, reports, experiments. This
convention states where they belong. It is a **two-tier rule** — the answer
depends on what the repository ships.

## The rule

**Tier 1 — the package is the product (ordinary libraries, apps):**
evolution artifacts live ON `main`, in the repo, the industry default:

- Decision records in `docs/adr/` (numbered, one decision per file)
- Planning/analysis in `docs/dev/` (or `analysis/`)
- They version in lockstep with the code they explain; package builds
  (wheel/sdist) exclude them automatically, so users never receive them.

**Tier 2 — the working tree is the product (templates, skill packs,
pages-style content):** evolution artifacts live on a **`meta` orphan
branch** — a parallel history in the same repository:

- `main` contains ONLY what ships: every file on main lands verbatim in
  stamped projects / consumers of the tree.
- `meta` contains everything used to evolve the project: `decisions/`,
  `analysis/`, `todos/`, `reports/`.
- This repo (`vpath_empty_project`) and `vpath_ontogate` follow Tier 2.

## Why two tiers (research basis)

Mainstream best practice (Fowler, adr.github.io, Microsoft, Google Cloud)
is docs-as-code: decisions stored next to the code, same timeline, same
repo — that is Tier 1, and we follow it for libraries. Long-lived orphan
branches are an established but niche pattern (`gh-pages` is the
precedent) with real costs: invisible when browsing main, tooling sees one
branch at a time, the "why" lives apart from the "what".

For a template those costs are outweighed by one hard constraint: **the
tree is the deliverable.** A `meta/` folder on main would leak into every
stamped project, or require exclusion machinery in every cloning/stamping
path — machinery that fails silently the day someone forgets it. Branch
separation makes the leak structurally impossible. Match the storage to
what ships.

## Working with a meta branch (Tier 2)

Check it out side-by-side instead of switching (keeps both trees on disk):

```bash
git worktree add ../<project>-meta meta
```

Creating one in a new Tier-2 repo:

```bash
git checkout --orphan meta
git rm -rf .
# add decisions/, analysis/, todos/, reports/, README.md — then:
git commit -m "chore: initialize meta branch"
git push -u origin meta
git checkout main
```

Rules of engagement:

- Never merge `meta` into `main` or vice versa (no shared history — git
  will refuse sensibly; don't force it).
- A change that ships goes to `main`; the thinking that produced it goes
  to `meta`. One PR/commit on each side when both are touched.
- Decision records on `meta` follow the ADR format: numbered, one decision
  per file, status + context + decision + consequences.
- The template's sync/drift scripts read `main` only; `meta` is invisible
  to derived projects by construction.

## Sources

- https://martinfowler.com/bliki/ArchitectureDecisionRecord.html
- https://adr.github.io/
- https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record
- https://docs.cloud.google.com/architecture/architecture-decision-records
- https://graphite.com/guides/git-orphan-branches
