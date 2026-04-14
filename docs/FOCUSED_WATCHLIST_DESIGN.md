# Focused Watchlist / 关注清单 Design

Last updated: 2026-04-14
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Goal

Provide a formal, queryable "重点关注 / 关注清单" layer that can be consumed consistently by lowfreq, midfreq, and archive without hardcoding ad-hoc symbol lists into each runner.

This doc defines the implementation plan. It does **not** require full implementation in this cleanup pass.

## 2. Design Principle

- `symbol_universe` remains the broad canonical symbol registry / supply side
- focused-watchlist is a **policy / selection layer**, not a replacement for universe
- each collection layer consumes the watchlist differently according to frequency and objective

## 3. Recommended Layer Placement

Implement as a shared collection-control layer in DB, adjacent to runtime control tables.

Recommended schema placement:
- same `ifa2` schema
- separate control tables, not mixed into asset history tables

Reason:
- lowfreq / midfreq / archive all need to consume it
- should be centrally queryable and auditable
- should support human curation + future generated scoring

## 4. Proposed Tables

### 4.1 `ifa2.watchlists`
Purpose: define a named watchlist.

Suggested columns:
- `id` UUID PK
- `watchlist_name` TEXT UNIQUE
- `watchlist_type` TEXT  
  - examples: `focus`, `priority`, `event_driven`, `theme`, `archive_backfill`
- `description` TEXT
- `owner` TEXT
- `is_active` BOOLEAN
- `created_at`
- `updated_at`

### 4.2 `ifa2.watchlist_symbols`
Purpose: map symbols into a watchlist.

Suggested columns:
- `id` UUID PK
- `watchlist_id` UUID FK -> `watchlists.id`
- `symbol` TEXT
- `priority` INTEGER
- `reason_code` TEXT
- `reason_text` TEXT
- `effective_from`
- `effective_to`
- `is_active` BOOLEAN
- `created_at`
- `updated_at`

Constraints:
- unique active tuple on `(watchlist_id, symbol, effective_from)` or equivalent dedupe policy

### 4.3 `ifa2.watchlist_materializations` (optional but recommended)
Purpose: persist per-run resolved watchlist snapshot for audit / replay.

Suggested columns:
- `id` UUID PK
- `watchlist_name` TEXT
- `runtime_layer` TEXT (`lowfreq` / `midfreq` / `archive`)
- `window_name` TEXT nullable
- `run_id` TEXT nullable
- `business_date` DATE
- `symbol_count` INTEGER
- `payload_json` JSONB
- `created_at`

## 5. Relationship with `symbol_universe`

### `symbol_universe` role
`symbol_universe` should remain the broad upstream canonical list of symbols that are valid / active / supported.

### Watchlist role
Watchlist tables select from and annotate that universe.

### Recommended join rule
All watchlist symbols should resolve through `symbol_universe.symbol`.

Policy:
- insert into watchlist only if symbol exists in `symbol_universe`, unless explicitly marked as pending onboarding
- watchlist is allowed to be a sparse, high-conviction subset
- watchlist metadata should not pollute `symbol_universe`

## 6. Consumption by Each Collection Layer

### lowfreq consumption
Use case:
- enrich / prioritize lower-frequency expensive datasets
- choose which entities receive deeper weekly refresh / expensive metadata refresh

Recommended behavior:
- broad baseline datasets still run on canonical universe when required
- expensive deep-refresh datasets can use watchlist subset first
- lowfreq can support config like:
  - `scope = universe`
  - `scope = watchlist:<name>`
  - `scope = union(universe_core, watchlist_focus)`

### midfreq consumption
Use case:
- post-close / intraday-adjacent same-day priority collection
- prioritize the symbols most likely needed by downstream analysis/reporting

Recommended behavior:
- midfreq should be the main consumer of focused watchlist
- if a dataset supports symbol-level fetch, consume only active focused symbols
- if a dataset is market-wide, still run full-market path where required
- record materialized watchlist snapshot per execution window for auditability

### archive consumption
Use case:
- long-history backfill / asset accumulation where budget is limited
- prioritize incomplete or strategically important symbols first

Recommended behavior:
- archive should support a dedicated archive watchlist, e.g. `archive_backfill_priority`
- default order:
  1. incomplete / missing history from priority watchlist
  2. broader universe backlog
- archive can use watchlist priority to allocate night-window budget

## 7. Runtime Interface Proposal

Recommended shared resolver API:
- `resolve_watchlist(name: str, as_of: date | datetime) -> list[symbol]`
- `resolve_scope(scope_expr: str) -> list[symbol]`

Examples:
- `watchlist:focus_core`
- `watchlist:hot_names`
- `union(watchlist:focus_core, watchlist:event_driven)`
- `universe:all_active_a_share`

## 8. Why Not Put This Directly into `symbol_universe`

Because the concepts differ:
- `symbol_universe` = what exists / is supported
- `watchlist` = what we care about right now

If mixed together, the registry becomes polluted with temporary human workflow state and loses clean semantics.

## 9. Minimal Rollout Plan

Phase 1:
- add `watchlists`
- add `watchlist_symbols`
- add simple CLI / seed path
- lowfreq / midfreq / archive can manually query active symbols

Phase 2:
- add watchlist resolver module
- add per-layer config support for `scope=watchlist:<name>`
- add materialization snapshots

Phase 3:
- add dynamic scoring / event-driven promotion rules
- add expiration and owner workflows

## 10. Recommended Initial Named Lists

- `focus_core`
- `focus_event_driven`
- `midfreq_priority`
- `archive_backfill_priority`
- `manual_temp_override`

## 11. Non-Goals for This Cleanup Pass

Not required right now:
- full UI
- automatic scoring engine
- complete migration rollout
- changing all existing datasets to watchlist-only mode

## 12. Final Recommendation

Implement focused-watchlist as a **shared control-plane selection layer** in `ifa2`, separate from `symbol_universe` but joined to it.

This gives:
- clear semantics
- runtime auditability
- lowfreq / midfreq / archive reuse
- no more ad-hoc symbol subsets hidden in per-layer code paths
