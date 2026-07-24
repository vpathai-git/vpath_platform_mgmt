---
name: atlassian-vpath
description: VPATH AI's way of working in Atlassian plus bundled Confluence publishing. Use for Jira project KAN, roadmaps, epics/features, user stories, product labels, the board, Confluence pages and Markdown→Confluence publishing — and for product knowledge on TRIAS (AI-assisted Design FMEA) and EIP (Engineering Intelligence Platform). Keywords: Jira, Confluence, KAN, roadmap, epic, story, produkt-trias, produkt-eip, DFMEA, knowledge graph.
---

# Atlassian way of working & product knowledge — VPATH AI

This skill is **self-contained**: knowledge + a bundled Confluence publisher
(`scripts/`, **pure Python standard library, no pip needed**). Copy the folder to
`.claude/skills/`, provide a `.env` — done.

## Credentials
A `.env` in the **working directory** (or in this skill folder), or environment
variables (these take precedence). Template: [.env.example](.env.example). Keys:
```
API_Token_Confluence = <Atlassian API token>
Atlassian_Email      = <email of the token owner>
Confluence_Base_URL  = https://vpathai-team-l8xgdmtm.atlassian.net/
```

## Two Atlassian hosts — the key trap
- **Jira:** `https://vpathai-team.atlassian.net` — project **KAN** (team-managed Kanban, Board 1).
- **Confluence:** `https://vpathai-team-l8xgdmtm.atlassian.net` — **its own host** (`Confluence_Base_URL`).
  With the same credentials the **Jira host returns 401 for Confluence** — always use the Confluence host.

## Data model (binding)
| Domain | Jira object | How |
|---|---|---|
| Roadmap | Timeline view | Epics with start / due dates |
| Feature | **Epic** | container |
| User Story | **Task** (`parent` = Epic) | "As … I want … so that …" |
| Product | **Label** `produkt-trias` / `produkt-eip` | which feature it contributes to |

Team-managed limits: **no level above Epic**, **components cannot be attached to issues via API** → product = label.
Nested doc epics (Epic→Feature→Story) → **doc epic = Jira epic, doc feature = Jira task**.
More: [reference/atlassian-model.md](reference/atlassian-model.md).

## Products (short)
- **TRIAS** — "Technical Risk Analysis System", the AI-assisted **Design FMEA** (AIAG & VDA, 7 steps,
  human-in-the-loop). A product of **Schouren Consulting & VPATH AI**. Label `produkt-trias`.
- **EIP** — **Engineering Intelligence Platform**: a Product Knowledge Graph + standards-compliant PLM/ALM
  artifacts (Polarion, Azure DevOps, SysML v2). Label `produkt-eip`.

Details: [reference/products.md](reference/products.md).

## Publish to Confluence — bundled (included in the skill)
| Task | Command (paths relative to the skill folder) |
|---|---|
| One MD file → new child page | `python scripts/publish_md.py --file DOC.md --parent <page-id>` |
| One MD file → replace an existing page's body | `python scripts/publish_md.py --file DOC.md --into <page-id>` |
| Whole directory → page tree (cross-links + ToC) | `python scripts/publish_set.py --dir ./docs --parent <page-id>` |

Idempotent (update by title). Logic in [scripts/confluence_md.py](scripts/confluence_md.py)
(Markdown→storage converter) and [scripts/confluence_api.py](scripts/confluence_api.py) (v2 REST client).

### Rendering traps (otherwise display errors)
- **No heading inside a blockquote** (`> ### …`) — Confluence shows an empty box → render as a bold paragraph.
- **Code/ASCII** as a code macro (whitespace preserved). **Internal `.md` links** → page links by title.
- Umlauts/emojis are preserved; when verifying, compare with `html.unescape` (`—`→`&mdash;`).
More: [reference/publishing.md](reference/publishing.md).

## Jira automation (not bundled → full toolkit repo)
Creating features/stories/roadmaps runs via the full toolkit repo `vpathai-confluence`
(`scripts/cli.py`, `atlassian/jira.py`). Examples: `cli.py feature … --product produkt-trias`,
`cli.py story … --feature KAN-7`. The **model knowledge** for it lives here in the skill (above + reference).

## Heavy lifting → agents
For large batch jobs use the agents `jira-architect` / `confluence-architect` (in the toolkit repo).
This skill = the *knowledge* + portable Confluence publishing; the agents = the *muscle*.
