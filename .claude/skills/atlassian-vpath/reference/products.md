# VPATH AI — company & products

## VPATH AI (company)
Engineering-intelligence vendor. Founder & CEO: **Alexander Krumm**.

**Vision:** product development as human-AI collaboration. AI agents need deep, granular
context (for FMEAs, root cause, test coverage); humans need abstract, functional views
matching the organizational structure. VPATH AI is the **knowledge infrastructure** that serves both.

**Core:** a **Product Knowledge Graph** following **systems-engineering ontologies** across all levels
(system, software, component, test, safety), with end-to-end **provenance**. Integrated into existing
toolchains (Siemens Polarion, Azure DevOps, SysML v2) — **does not replace them**.

**Three pillars:** (1) knowledge fusion & deep extraction from documents/code/CAD schematics,
(2) context management for humans & AI, (3) frontier: humanoid-robotics safety (safe-by-design).

---

## EIP — Engineering Intelligence Platform
The platform that prepares the distributed, unstructured existing knowledge and manages it centrally in the
Product Knowledge Graph — reusable for humans and AI.

From a use-case view, **three levels**:
1. **Reengineering pipeline** — builds the knowledge graph from documentation, source code and DWG schematics
   (dedicated coding agents extract knowledge from the as-is implementation).
2. **Chat interaction** with the knowledge graph (with access management) — saves expert meetings,
   avoids wrong decisions.
3. **Workflows** that turn the knowledge into **standards-compliant PLM/ALM artifacts**: specifications in
   Siemens Polarion, test cases in Azure DevOps, architectures as SysML v2 — and proactively identify
   discrepancies between specification and implementation.

Label in Jira: **`produkt-eip`**.

---

## TRIAS — Technical Risk Analysis System
The **AI-assisted Design FMEA**. A joint product of **Schouren Consulting**
(Dr. Frank Schouren, FMEA expert/moderator since 2004) **& VPATH AI**.
Claim: *"The intelligent Design FMEA — faster, more efficient, more sustainable."*

**Method:** Design FMEA per **AIAG & VDA 2019**, 7 steps. Failure chain
**failure effect ← failure mode → failure cause** (level n-1 / n / n+1).
- Steps **1–3**: structure & function analysis (structure import e.g. from Polarion).
- Steps **4–6**: LLM-assisted (failure analysis, risk rating S/O/D + action priority, optimization) —
  **always with expert review** (human-in-the-loop, the AI does not decide alone).
- Step **7**: documentation & export (Excel in VDA format, audit trail).

**USP / "why TRIAS":**
- **No new database** — an intelligent layer on existing systems/BOMs (no data silos).
- **Automatic analyses** — the AI generates malfunctions/failure chains, experts approve or enrich them.
- **Open architecture** — standardized interfaces, **no vendor lock-in**, RAG build possible;
  "your knowledge stays your knowledge".
- **Efficiency:** about **40–55%** less total DFMEA effort (structure −50…80%, function −30%,
  failure analysis −70%, risk −50…60%, optimization −20…80%).

**Operation (short):** the **customer provides the LLM** (provider-neutral, e.g. Azure OpenAI;
project policy: `gpt-5-mini`, **not** `gpt-4o(-mini)`). Various deployment variants,
cost model, GDPR/security and reseller/SLA are in the detailed handbook.

Label in Jira: **`produkt-trias`**.

---

## Sources for depth (do not duplicate here)
- `InputQuellen/TRIAS_Detailhandbuch.md` — architecture, deployment variants, cost model,
  data security/GDPR, certification, contract/SLA.
- `vpath_FMEA/docs/TOOL_BESCHREIBUNG.md` — the 7 TRIAS steps in UI detail.
- Marketing: `…/Schouren & VPATH AI - Dokumente/Marketing/202605_TRiAS-…_{lang,kurz}.{pdf,pptx}`.
