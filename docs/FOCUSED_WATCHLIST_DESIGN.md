# Focused Watchlist / 关注清单 Design

Last updated: 2026-04-16
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Goal

Provide a formal, queryable "重点关注 / 关注清单" layer that can be consumed consistently by lowfreq, midfreq, highfreq scope planning, and archive without hardcoding ad-hoc symbol lists into each runner.

## 1.1 Current truth
This is no longer a pure proposal-only document.
A Business Layer list model is now already present in the repo/database through:
- `ifa2.focus_lists`
- `ifa2.focus_list_items`
- `ifa2.focus_list_rules`

Current known list families include:
- `default_key_focus`
- `default_focus`
- `default_tech_key_focus`
- `default_tech_focus`
- `default_archive_targets_15min`
- `default_archive_targets_minute`

So the correct interpretation is:
- the repository already has a first-class focus-list / watchlist control plane
- this doc should describe how that current model relates to the original design intent
- not all desired list families are complete yet (for example commodity / precious_metal focus lists still do not exist)

## 2. Design Principle

- `symbol_universe` remains the broad canonical symbol registry / supply side
- focused-watchlist is a **policy / selection layer**, not a replacement for universe
- each collection layer consumes the watchlist differently according to frequency and objective

## 3. Current Layer Placement

The shared collection-control layer is now already placed in the DB, adjacent to runtime control tables, in schema `ifa2`.

Current schema placement:
- `focus_lists`
- `focus_list_items`
- `focus_list_rules`

Reason remains the same:
- lowfreq / midfreq / archive all consume or can consume it
- it is centrally queryable and auditable
- it supports human curation and later dynamic/scored expansion

## 4. Current Tables and Remaining Extensions

### 4.1 Current implemented tables
#### `ifa2.focus_lists`
Purpose: define a named focus/watchlist.

Current semantic fields observed in use:
- `id`
- `owner_type`
- `owner_id`
- `list_type`
- `name`
- `asset_type`
- `frequency_type`
- `description`
- `is_active`
- timestamps

#### `ifa2.focus_list_items`
Purpose: map symbols into a focus/watchlist.

Current semantic fields observed in use:
- `id`
- `list_id`
- `symbol`
- `name`
- `asset_category`
- `priority`
- `source`
- `notes`
- `is_active`
- timestamps

#### `ifa2.focus_list_rules`
Purpose: attach control rules to a focus/watchlist.

Current semantic fields observed in use:
- `id`
- `list_id`
- `rule_key`
- `rule_value`
- timestamps

### 4.2 Remaining optional extension
A per-run materialization/snapshot table is still conceptually useful, but it is not required to claim the watchlist layer exists.
The current repo instead often captures resolved runtime scope through manifest snapshots and unified runtime evidence.

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

## 10. Current Named Lists and Remaining Gaps

Current known named lists:
- `default_key_focus`
- `default_focus`
- `default_tech_key_focus`
- `default_tech_focus`
- `default_archive_targets_15min`
- `default_archive_targets_minute`

Important remaining gaps:
- no explicit commodity key-focus list
- no explicit commodity focus list
- no explicit precious_metal key-focus list
- no explicit precious_metal focus list
- no explicit archive index target list observed

## 11. Non-Goals for This Cleanup Pass

Not required right now:
- full UI
- automatic scoring engine
- complete migration rollout
- changing all existing datasets to watchlist-only mode

## 12. Final Recommendation

Treat the current `focus_lists` / `focus_list_items` / `focus_list_rules` model as the shared control-plane selection layer in `ifa2`, separate from `symbol_universe` but joined to it.

This already gives:
- clear semantics
- runtime auditability
- lowfreq / midfreq / archive reuse
- no more ad-hoc symbol subsets hidden in per-layer code paths

Next-step recommendation is not to invent a second watchlist schema, but to:
- continue seeding missing list families into the current focus-list model
- document list taxonomy clearly
- add any needed materialization/snapshot helpers on top of the current model rather than replacing it
