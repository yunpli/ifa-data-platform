# Migration Notes

## 1. Migration principle

This repository is the new engineering mainline for the backend substrate behind **iFA 2.0**.

Migration does **not** mean copying the old IFA / ICD execution chain into a new repo. It means preserving what is useful while breaking the old coupling that made the previous chain hard to evolve.

Carry forward:
- useful object boundaries
- evidence/fact field ideas
- market/report operational lessons
- source knowledge and historical pain points

Leave behind:
- tightly coupled fetch -> interpret -> assemble -> deliver chains
- report-time-only state
- archive/manual/runs as architecture anchors
- one-off repair logic as core system design

## 2. What changed in the current understanding

The corrected product context is:
- iFA 2.0 is primarily a **report product** built around market-clock delivery
- 2.0 output is briefing + general market long reports
- 2.1 / 2.2 / 3.x add later layers of personalization and strategy capability

Therefore this repo should not be described as an isolated end-state data product detached from the report system.

The correct framing is:
- this repo is the backend substrate **serving iFA 2.0 report production**
- it must still be independently operable enough to provide stable schema/runtime contracts
- but its architecture should remain subordinate to the product delivery path, not abstracted away from it

## 3. What is reasonable to reuse from old assets

### Reusable references
- practical object ideas from `ifa_*` scripts/tables
- naming and identity patterns for market/fact/source entities
- old operational lessons about timing, failure points, and report production pain
- existing DB connectivity assumptions around `ifa_db`

### Reference-only materials
- old archive folders
- historical report outputs
- manual scripts
- run artifacts
- recovery notes and ad-hoc fixes

These can inform design, but they should not define the new runtime backbone.

## 4. What should not be transplanted directly

- old manual/archive/runs as core structure
- report-generation-first chains as the permanent backend model
- OpenClaw-specific orchestration details inside the repo core
- domain-specific patch logic generalized as architecture
- assumptions that every report run must rebuild evidence from scratch

## 5. Current migration stance

### New mainline
- repo: `ifa-data-platform`
- database host: `ifa_db`
- isolated schema: `ifa2`
- migration system: Alembic
- runtime baseline: minimal scheduler/worker/job-state loop

### Current role of the old system
- historical reference
- source of lessons
- source of candidate field/object boundaries
- not the future mainline

## 6. Migration method from here

1. keep the new repo as the engineering main branch
2. preserve the already-landed real schema/runtime closure
3. refine naming/contracts so they better serve iFA 2.0 report production
4. selectively absorb old object knowledge without reviving old coupling
5. gradually introduce richer report-material inputs, then adapter/source onboarding

## 7. Practical rule

When deciding whether to carry something over from old IFA/ICD, use this test:

- If it improves evidence continuity, replayability, provenance, or reusable report inputs, it is a candidate.
- If it mainly preserves old chain coupling, late-stage patching, or report-time-only glue, it should stay behind.
