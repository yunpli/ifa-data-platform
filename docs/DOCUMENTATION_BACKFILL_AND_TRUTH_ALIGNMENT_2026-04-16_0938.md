# Documentation Backfill and Truth Alignment — Full Gap Sweep

_Date: 2026-04-16_0938_

## Scope
This is a broader follow-up to the previous documentation backfill pass.
Goal:
- re-check recent commit history and durable repo docs more comprehensively
- catch remaining stale/superseded documentation assumptions
- patch documentation gaps so the repo is understandable to a future engineer without replaying chat history

## Commit/history window reviewed
Reviewed recent history including:
- `39755d1` — Backfill repo docs to match runtime and data truth
- `7774b0d` — Seed tech focus lists and clarify archive backfill
- `d8b55ff` — Document full-chain alignment and follow-up run truth
- `ef5d902` — Run unified acceptance cleanup and validation batch
- `2d24c50` — Converge runtime daemon and redesign schedule policy
- `a77e625` — Complete highfreq milestone 4-6 operability and runtime audit
- `508d4d1` / `53079ee` / `c3b819e` / `23736d2` / `61d03ca` / `1357a72`
- earlier Trailblazer/runtime audit commits where durable docs originally diverged from current truth

## Additional docs checked in this pass
In addition to the prior core docs pass, this sweep explicitly checked:
- `docs/lowfreq_framework.md`
- `docs/migration_notes.md`
- `docs/FOCUSED_WATCHLIST_DESIGN.md`
- `docs/COLLECTION_RUNTIME_AUDIT_2026-04-14.md`

## What was already acceptable in this second sweep
### `docs/lowfreq_framework.md`
This remains largely valid as a lane/framework reference.
It is detailed, and while it still contains historical lane-level daemon material, it is fundamentally a lowfreq framework document rather than a canonical runtime-entry doc.
It did not require immediate invasive rewrite in this pass.

### `docs/migration_notes.md`
Still acceptable as a migration-philosophy / architecture-boundary note.
It is not a runtime runbook, so it did not materially mislead operators about the current unified runtime entry model.

## Remaining major mismatch found in this sweep
### `docs/FOCUSED_WATCHLIST_DESIGN.md`
This was materially stale in an important way:
- it still described a proposed future `watchlists/watchlist_symbols/watchlist_materializations` schema
- but the repo/database already uses a real Business Layer control-plane model:
  - `focus_lists`
  - `focus_list_items`
  - `focus_list_rules`

That meant the doc was teaching a superseded conceptual model rather than the actual one in use.

### Historical audit doc interpretation risk
`docs/COLLECTION_RUNTIME_AUDIT_2026-04-14.md` was not wrong as historical record, but without a warning banner it could be mistaken as current truth because it still describes lane-daemon runtime chains as formal chains.

## Docs updated in this pass
Updated:
- `docs/FOCUSED_WATCHLIST_DESIGN.md`
- `docs/COLLECTION_RUNTIME_AUDIT_2026-04-14.md`

## Truth added/corrected in this pass
### In `docs/FOCUSED_WATCHLIST_DESIGN.md`
Corrected from proposal-only model to current-truth model:
- explicitly states the current implemented control-plane tables:
  - `focus_lists`
  - `focus_list_items`
  - `focus_list_rules`
- explains that the repo already has first-class list families such as:
  - `default_key_focus`
  - `default_focus`
  - `default_tech_key_focus`
  - `default_tech_focus`
  - `default_archive_targets_15min`
  - `default_archive_targets_minute`
- clarifies remaining gaps instead of pretending the layer is complete:
  - no commodity focus-style lists
  - no precious_metal focus-style lists
  - no explicit archive index target list observed
- updates recommendation so future work extends the current focus-list model instead of inventing a second parallel watchlist schema

### In `docs/COLLECTION_RUNTIME_AUDIT_2026-04-14.md`
Added an explicit historical-note banner stating:
- the doc is a historical audit snapshot
- it is not the current canonical runtime model after unified-daemon convergence
- current truth should be read from:
  - `docs/runbook.md`
  - `docs/architecture.md`
  - `docs/DEVELOPER_COLLECTION_CONTEXT.md`

## Current documentation completeness judgment after full sweep
### Strongly improved / now aligned well enough
The repo now has durable docs that truthfully cover:
- official runtime entry model
- worker/lane relationship under unified daemon
- day-type schedule policy
- DB-backed trading-day gating
- BL influence on runtime scope
- tech list seeding truth
- archive target/backfill unevenness
- watchlist/focus-list control plane using real current tables rather than only proposals

### Still not perfect
Some docs are still historical or lane-specific and could eventually be normalized further, but they are no longer the main source of dangerous confusion.
Remaining improvement opportunities:
1. a dedicated durable doc for runtime/audit/control tables and their exact operator meaning
2. a durable Business Layer list taxonomy doc
3. a dedicated doc for summary-table materialization mismatches (`midfreq_execution_summary`, `highfreq_execution_summary`)
4. a consolidated highfreq durable reference replacing some milestone-only knowledge

### Final truthful assessment
After this broader sweep, the repository is no longer in a state where the main durable docs materially misdescribe the current operating model.
There are still historical docs and layered docs, but the major “doc truth lags code truth” risks have now been substantially reduced.
