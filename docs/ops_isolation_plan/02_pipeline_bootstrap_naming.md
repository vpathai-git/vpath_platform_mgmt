# Components 7–9 — Extraction Timing, First-Time Bootstrap, Naming

## 7. Pipeline extraction timing (the Kernanforderung deviation)

The prompt's first core requirement is literal: *"Die Build-Pipeline aus dem
Serverprojekt in ein separates Repository isolieren."* The v1 plan does the
opposite for the foreseeable future and presents it as settled. This
component makes the timing an explicit, signed-off decision.

| Option | Weight | Pros | Cons |
|---|---|---|---|
| **A. Staged: extraction stays at phase 6, after verbs stabilize (recommended)** | **8/10** | No dual maintenance while the server rebuild is still "ausbügeln"-phase; PIPELINE UNITY preserved; the engine sits where airgap/host-only tasks (`erase-installation.sh`) must run anyway; extraction later means the extracted artifact is right-sized to proven verbs | Literal requirement unmet for months; stakeholders may read it as non-delivery; the build worker still needs the monorepo checkout |
| B. Early extraction: publish `vpath-pipeline` as a versioned job image in phase 2–3 | 6/10 | Literal compliance early; clean versioning from day one; monorepo stops being the ops checkout sooner | Extracting while ~60 scripts still assume monorepo paths (`lib/vm.sh`, `apps_infra/apps`) means high-churn double work; recreates the drift risk that killed topology B; delays the console MVP that delivers the actual role value |
| C. Literal now: move Gradle + `lib/pipeline` wholesale, new repo becomes source of truth | 3/10 | Unambiguous compliance | Breaks standalone PIPELINE UNITY; host-only tasks still need code adjacent to the server; a large migration lands before any console value ships; the server team loses hotfix locality mid-stabilization |

**Recommendation: A — but only with an explicit deviation record.** The
reasoning: the requirement's *intent* is that nobody must operate from
inside the server project, and Coolify inversion delivers that intent
earlier and more safely than a physical repo move. A physical move now (B/C)
optimizes for the requirement's *letter* at the cost of drift, double
maintenance, and a delayed MVP — the exact failure modes the server team
just spent the rebuild eliminating. What turns this from silent
reinterpretation into a legitimate decision is (a) the sign-off in the
README deviations section and (b) a concrete extraction trigger instead of
"later": **start B when the six MVP verbs have run ≥4 weeks without a verb
schema change AND the registry contract (component 10) is live.** If
stakeholders veto, fall back to B, accepting the churn consciously.

## 8. First-time install on a new machine (bootstrap)

Coolify inversion assumes an engine already running on the shared server —
but the prompt requires *"Server neu installieren — First-Time auf eine neue
Maschine"*, where no Ops API exists yet to call. v1 conflated reinstall
(engine exists) with first install (it does not). The design constraint
itself points at the answer: *"beim NUC-Install muss der Servercode nur auf
der NUC-Install-Seite verfügbar sein."*

| Option | Weight | Pros | Cons |
|---|---|---|---|
| **A. Documented Admin runbook: clone server monorepo on the install side, run the existing install, engine + Ops API take over afterwards (recommended now)** | **8/10** | Zero new code; exactly today's proven path (`goReinstall`, `bootstrap-vms.sh`, `provision-deploy-vm.sh`); fully inside the design constraint — the Admin role explicitly may touch the monorepo break-glass; works for every target class incl. airgapped | Not self-service; the Admin still handles a full checkout; runbook quality becomes load-bearing |
| B. Bootstrap bundle: `vpath bootstrap <target>` in this repo downloads a pinned server release artifact and drives the install over SSH | 7/10 (medium-term) | One entry point for Admins; no monorepo clone; version-pinned installs; natural companion to the extracted job image | Requires published release artifacts — the same prerequisite as engine extraction, so it cannot ship before component 7's trigger; new engineering; airgap transfer of the bundle is still manual |
| C. Golden image / VM template / ISO provisioning | 4/10 | Fastest re-provision for the Azure `vm5` class; immutable and repeatable | Does not fit the physical NUC or the airgapped CLAAS host; an image build pipeline is new infrastructure; images go stale between releases |

**Recommendation: A now, B at engine-extract time, C opportunistically for
Azure only.** The reasoning: first-time install is an Admin-only, rare,
high-privilege operation — the one flow where "touches the server checkout"
is explicitly permitted and where investing in self-service earliest buys
the least. A costs one well-written runbook in this repo
(`docs/INSTALL_RUNBOOK.md`, referencing — not copying — the monorepo docs)
and closes the chicken-and-egg hole immediately. B is the right end state
but shares its hard prerequisite (published, versioned release artifacts)
with component 7's option B, so bundling them into the same phase avoids
building the artifact plumbing twice. C is never the general answer because
two of the four known targets are physical or airgapped, but once `vm5`-class
targets are routinely erased and reinstalled (the 2026-07-21 reinstall
report suggests they are), a template image is cheap leverage there.

## 9. Repo naming and home

v1 locked `vpath-server-mngmt`; the repo actually created is
`vpath_platform_mgmt`, initialized from the `vpath_empty_project` template.

| Option | Weight | Pros | Cons |
|---|---|---|---|
| **A. Adopt `vpath_platform_mgmt` — reality wins (recommended)** | **8/10** | Repo already exists with template gates wired; underscore form matches the VPath template convention (`context/GENERAL_PROJECT_TEMPLATE.md`); "platform mgmt" is *more accurate* — the plane manages apps AND server instances, not only the server; no infra churn | Every reference in the v1 bundle must be renamed before pasting; the decided name in past discussion becomes stale |
| B. Rename the repo to `vpath-server-mngmt` | 4/10 | Matches the locked decision text and any external references to it | Churn (remotes, CI, worktrees) for zero functional gain; hyphens break the local naming convention; "mngmt" is a typo-prone abbreviation people will misspell in URLs forever |
| C. Keep both names as aliases | 1/10 | Nobody has to update anything today | Permanent ambiguity in docs, chat, and config; violates one-canonical-name; guarantees a future "which repo?" incident |

**Recommendation: A.** The reasoning: a name's job is to be findable and
typeable; `vpath_platform_mgmt` wins on both and the semantic argument
(platform > server) is real, not cosmetic — EasyAccess and app lifecycle
management are platform concerns. The only cost is a mechanical
`s/vpath-server-mngmt/vpath_platform_mgmt/` pass over the v1 bundle, which
must happen anyway before the split-paste (component 12). Do it once, note
the rename at the top of the pasted handoff so readers of the old plan are
not confused, and never mention the old name again.
