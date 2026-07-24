# Claude Code Adapter

@AGENTS.md

## Claude Code

Claude Code reads this file and imports the shared repository governance from
`AGENTS.md`. Keep project-wide rules in `AGENTS.md`; this adapter may contain
only Claude-specific mechanics, stamps, and load-path notes.

## Project Skills

Installed under `.claude/skills/`, invoked with `/<name>` — use them instead of
improvising the workflow they cover. When you notice a repetitive,
checklist-dependent, or error-expensive task done 3+ times, propose capturing it
as a skill.

| Skill | Use when |
|-------|----------|
| `/careful-commit` | Committing changes — reviews the full diff, groups atomic commits, enforces secrets and debug-code hygiene |
| `/find-fix-for-good` | A bug needs root-cause analysis before coding |
| `/fix-and-persist` | Implementing a fix that must not come back |
| `/verify-ui` | Defensibly answering whether a user-visible feature works |
| `webapp-testing` | Browser mechanics: servers, Playwright, selectors |
| `/decide-next` | Multiple open decisions block progress |
| `/plain-summary` | A German CTO briefing, status-first and self-contained |
| `/fable-team` | Tiered-team sessions and high-stakes review |
| `/ponytail-audit` | Read-only scan for over-engineering |
| `/ponytail-sweep` | Active whole-repo minimalism pass |

## Context Budget

The agent's real context fill is reported each turn by the `context-report`
UserPromptSubmit hook, fed from the status line. Never self-estimate; if the
figure is absent, say so rather than guess. The global `~/.claude/CLAUDE.md`
carries the operating rule. Opt in per machine via `scripts/init_project.py`.

The bands below are a dated, revalidatable assumption. Re-check at the horizon,
sooner if the session model changes or new long-context evidence lands.

<!-- CONTEXT-DECAY-ASSUMPTIONS-BEGIN -->
```yaml
hard_complex_work: ~30%   # architecture, multi-hop, many scattered facts, high error cost
medium_work: ~40-50%      # local edits, scoped debugging
easy_lookup: ~60-70%      # verbatim retrieval, then compact for output headroom
flag_once_at: 50%         # if larger/complex work follows, recommend compaction first
mirror: bands also live as behaviour in the global ~/.claude/CLAUDE.md; update both on revalidation
basis: no measured Opus-4.8 curve; judgment from Anthropic context-rot/attention-budget guidance plus Chroma 2025, NoLiMa 2025, RULER 2024, Michelangelo 2024, Databricks 2024
fact: literal retrieval holds near full 1M; complex reasoning degrades 4-10x earlier; Opus 4.8 has no native context self-tracking
recheck_sources: Anthropic context-windows and effective-context-engineering; Chroma Context Rot; NoLiMa and RULER plus a live long-context leaderboard
validated: 2026-06-24
review_horizon_days: 120
```
<!-- CONTEXT-DECAY-ASSUMPTIONS-END -->

## This File Is A Dated Assumption

Machine-checked by `scripts/check_skill_assumptions.py`. When stale, review it
against reality, propose edits for human approval, then re-stamp. Add a rule
only after an observed repeated failure, never in anticipation.

<!-- CLAUDE-MD-ASSUMPTIONS-BEGIN -->
```yaml
validated: 2026-06-28
review_horizon_days: 180
ontogate: not-adopted
```
<!-- CLAUDE-MD-ASSUMPTIONS-END -->
