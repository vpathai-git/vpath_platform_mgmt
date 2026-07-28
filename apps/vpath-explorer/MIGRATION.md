# Migration Report

Deterministic brownfield analysis against the VPATH app canon. The default run writes only this report. Citizen opportunities are always report-only.

## Summary

- GATE findings: 0
- SEAM findings: 0
- CITIZEN opportunities: 1
- APPLIED normalizations: 0

## Applied normalizations

None. The manifest was not changed.

## Gate violations

None.

## Boundary seam leaks

None.

## First-class citizen opportunities

### CITIZEN-001 — A storage-like code shape may belong to a first-class platform citizen.

- Where: `src/components/ExplorerLayout.tsx:122`
- What: A storage-like code shape may belong to a first-class platform citizen.
- Why: CITIZENS.md §3 defines the separate declaration and runtime boundary for this citizen.
- Canonical fix: Express durable folders with `spec.appStorage`/`spec.sharedFolders` and use the SDK storage surfaces.

## Safety boundary

Only readiness-budget insertion and legacy health-field renaming have write paths. Dapr, UI, seams, and all citizen blocks are never rewritten automatically.
