# Atlassian model & way of working (detail)

## Instances
| Product | Host | Purpose |
|---|---|---|
| Jira | `https://vpathai-team.atlassian.net` | project **KAN** (id 10000), Board 1 |
| Confluence | `https://vpathai-team-l8xgdmtm.atlassian.net` | its own host, personal/team space |

Auth = HTTP Basic with `Atlassian_Email` + `API_Token_Confluence` (one token for both).
The Jira host answers Confluence requests with **401** — for Confluence always use `Confluence_Base_URL`.

## Jira project KAN
- **Team-managed (next-gen) Kanban.** Issue types: **Task** (hierarchy 0), **Epic** (1), **Sub-task** (−1).
- Settable fields (verified): `labels`, `parent` (on Task), `customfield_10015` (start date), `duedate`.
- Team-managed limits:
  - **No hierarchy level above Epic** (Initiative etc. only with Jira Premium).
  - **Components cannot be attached to issues via API** (the feature is not active in the project).
  → Both are why **product = label** instead of a component / its own hierarchy level.

## Mapping rules
| Domain | Jira | Note |
|---|---|---|
| Roadmap | Board timeline view | Epics need start + due; then enable Project settings → Features → **Timeline** (one manual click, not via API) |
| Feature | Epic | description = goal + success criteria |
| User Story | Task, `parent` = Epic | format "As <role> I want <goal> so that <benefit>" |
| Product | Label `produkt-<slug>` | normalize via `config.product_label()` |

### Nested doc epics (Epic → Feature → Story)
When a source document itself has an Epic→Feature→Story hierarchy (e.g. `vpath_FMEA/docs/epics/*`):
- **Doc epic → Jira epic**
- **Doc feature → Jira task** (`parent` = Epic)
- (Doc stories / sub-bullets would become sub-tasks; create only on request.)
This yields the two native levels that team-managed allows at most.

## Products ↔ labels
| Product | Label |
|---|---|
| TRIAS | `produkt-trias` |
| EIP | `produkt-eip` |

Configuration centralized in `config.py` (`PRODUCTS`, `TEAM`, issue-type mapping, field ids).

## Conventions
- **Idempotency:** write helpers check for duplicates by summary (Jira) or title (Confluence).
- **Read before write** (JQL/GET before POST/PUT). After writing, verify by reading + report the URL.
- **Cross-platform:** `pathlib`, `encoding='utf-8'`. **Permissive licenses only** (MIT/Apache/BSD).
- Never print or commit tokens / `.env` (`.gitignore` protects `.env`).
- Team (5 people) + assignees: from `config.TEAM`; inviting into the project is a UI step.

## Useful Python building blocks
```python
from atlassian.jira import Jira
jira = Jira()
feat = jira.create_feature("Title", "produkt-trias", start="2026-07-01", due="2026-09-30",
                           description="Goal: …\nSuccess criteria:\n- …")
jira.create_story("As … I want …", feat["key"], "produkt-trias")
jira.roadmap("produkt-eip"); jira.stories_of("KAN-7")
```
