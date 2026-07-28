---
entity: src.components.workflow-demo
kind: frontend
stories: [K01]
tests: [tests/standalone-workflow-demo.proof.ts]
status: validated
validated: 2026-07-22
---

# Workflow surfaces and honest empty state

The page always renders the authored three-step configuration and a visible
cluster-only notice. In platform mode it uses `createAllWorkflowHooks` and
`WorkflowApp`; in standalone it renders a configuration-only empty state and no
run control.
