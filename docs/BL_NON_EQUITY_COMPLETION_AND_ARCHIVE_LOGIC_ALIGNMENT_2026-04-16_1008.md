# BL Non-Equity Completion + Archive Logic Alignment

_Date: 2026-04-16_1008_

## Scope
This batch implements and/or clarifies two linked areas:
1. Business Layer category completion for non-equity focus/key-focus families
2. Archive business-logic alignment against the intended archive rules

Repo boundary followed:
- Business Layer list-definition/seeding work in `ifa-business-layer`
- Archive runtime/data logic work in `ifa-data-platform`

## Milestone A — Business Layer category completion
### Work performed in Business Layer repo
Added artifacts:
- `scripts/seed_non_equity_focus_lists.py`
- `docs/NON_EQUITY_FOCUS_LISTS_2026-04-16.md`
- output artifact: `artifacts/non_equity_focus_seed_2026-04-16_1005.json`

### Intended list families
Created/seeded definitions for:
- `default_futures_key_focus`
- `default_futures_focus`
- `default_commodity_key_focus`
- `default_commodity_focus`
- `default_precious_metal_key_focus`
- `default_precious_metal_focus`

### Truthful seeding result
Current DB/reference truth could not support the requested target sizes cleanly.
No fake fills were inserted.

Observed seeded counts:
- futures_key_focus: `0 / 20`
- futures_focus: `0 / 40`
- commodity_key_focus: `6 / 20`
- commodity_focus: `6 / 40`
- precious_metal_key_focus: `2 / 20`
- precious_metal_focus: `2 / 40`

Resolved inserts actually present:
- commodity:
  - `CU0` 沪铜主连
  - `AL0` 沪铝主连
  - `ZN0` 沪锌主连
  - `RB0` 螺纹钢主连
  - `HC0` 热卷主连
  - `SC0` 原油主连
- precious_metal:
  - `AU0` 沪金主连
  - `AG0` 沪银主连

### Truthful judgment for Milestone A
- list families now exist as Business Layer repo truth
- but current DB/reference truth is insufficient to meet the requested 20/40 sizing for non-equity categories
- therefore Business Layer category completion is only **structurally completed**, not fully populated to intended size
- unresolved sizing shortfall is real and recorded, not hidden

## Milestone B — Archive logic gap audit
Target business logic required:
- archive has two responsibilities:
  1. forward archival of current-day collected data
  2. time-series archival of tradable objects across selected frequencies
- daily: archive all main tradable categories
- 60m: archive by default where source exists
- 15m: archive `key_focus` + `focus`
- 1m: archive `key_focus` only
- 1m/15m: forward-only, no historical backfill now
- historical backfill focus: daily + slower/compact structures, anchor `2023-01-01`
- membership changes affect future archive behavior only; historical archive remains

### Gap map against current code before this batch
#### Already matched / partly matched
- archive runs under unified runtime daemon
- archive checkpoints/catch-up truth exists
- archive has stock/futures/commodity/precious_metal history tables
- archive progression can be observed from DB/runtime evidence

#### Missing / partial / incorrect
1. **Intraday archive backfill rule mismatch**
- stock/futures intraday archivers still resumed from old checkpoints and historical windows
- this violates forward-only 1m/15m business rule

2. **Target-selection logic mismatch**
- archive intraday scope was not driven by `key_focus` / `focus`-style membership rules
- futures/commodity/precious_metal intraday paths were category-based, not BL list-policy based

3. **60-minute archive path**
- required by intended logic
- **not implemented**

4. **Current-day small structured output archive**
- intended business rule says meaningful current-day structured outputs should also be archived
- **not implemented as a first-class archive layer**

5. **Daily backfill anchor formalization**
- intended anchor is `2023-01-01`
- not yet fully normalized as active orchestrator-wide parameterized policy

6. **Membership change semantics**
- intended future behavior rule is clear
- not yet fully formalized as explicit lifecycle doc/contract in code

## Milestone C — Archive implementation alignment
### Code changes in Data Platform repo
Added:
- `src/ifa_data_platform/archive/archive_policy.py`

Updated:
- `src/ifa_data_platform/archive/archive_orchestrator.py`
- `src/ifa_data_platform/archive/stock_15min_archiver.py`
- `src/ifa_data_platform/archive/stock_minute_archiver.py`
- `src/ifa_data_platform/archive/futures_intraday_archiver.py`
- `docs/ARCHIVE_RUNTIME_AND_DATA_STATUS.md`

### What was aligned in code
1. **Archive policy layer added**
`archive_policy.py` now defines the intended policy matrix and records current support status.
It truthfully classifies:
- daily categories as intended backfill family
- 60m as currently unsupported
- 15m as forward-only for focus/key-focus families
- 1m as forward-only for key-focus only

2. **Forward-only intraday semantics enforced**
Stock 15m / 1m and futures-family intraday archivers now clamp start time to the current forward window instead of using old checkpoint state as historical backfill continuation.
This makes intraday behavior align with “start accumulating from official runtime forward” rather than retroactive multi-year intraday backfill.

3. **BL-driven archive intraday selection introduced**
Archive orchestrator now resolves archive intraday symbol scope through `archive_scope_symbols(...)`, which reads Business Layer manifest/list scope rather than relying purely on broad category slices.

### What remains partial / deferred
1. **60-minute archive implementation**
- still not implemented
- explicitly unsupported in current code/policy truth

2. **Current-day structured-output archive family**
- still not implemented as first-class archive tables/collectors
- examples like signal/judgment summaries, hot-sector summaries, event summaries remain a future archive-expansion item

3. **Daily backfill anchor full implementation**
- anchor is now formalized in policy module as `2023-01-01`
- but the full archive fleet is not yet uniformly reworked around that parameter as a complete daily-backfill policy engine

4. **Non-equity BL coverage insufficiency**
- because futures/commodity/precious_metal BL lists are still sparsely populated, the archive intraday policy can now reference the correct list families but current practical scope remains incomplete

## Milestone D — Testing and evidence
### Tests run
Data Platform repo:
- `python3 -m pytest -q tests/integration/test_unified_runtime_daemon.py`
- result: `5 passed, 72 warnings in 0.49s`

### Runtime evidence
Archive dry-run via unified daemon:
- `python3 -m ifa_data_platform.runtime.unified_daemon --worker archive --runtime-budget-sec 3600 --dry-run-manifest-only`
- result:
  - `status=succeeded`
  - `tables_updated=[ifa2.archive_runs, ifa2.archive_checkpoints, ifa2.archive_target_catchup]`
  - `governance_state=ok`

### Important runtime caveat observed
Dry-run archive invocation still emits unrelated midfreq dataset-registration logs at startup.
That is a runtime hygiene issue, not proof of archive business-logic failure, but it should be cleaned up in a later runtime hygiene pass.

### DB evidence for BL seeding
Business Layer seeding artifact:
- `artifacts/non_equity_focus_seed_2026-04-16_1005.json`

It proves:
- lists were created/updated in DB
- actual inserted counts are far below target sizes for non-equity categories
- unresolved sizing is explicit and auditable

## Milestone E — Documentation completion
### Business Layer repo docs added
- `docs/NON_EQUITY_FOCUS_LISTS_2026-04-16.md`

### Data Platform repo docs updated
- `docs/ARCHIVE_RUNTIME_AND_DATA_STATUS.md`

### What documentation now states truthfully
- non-equity list families exist but are under-populated relative to intended size
- archive intended business rule is explicit
- current code now partially aligns that rule in selection and forward-only intraday semantics
- 60m and current-day structured output archive remain unsupported/deferred

## Final truthful judgment
### What is completed
- Business Layer non-equity list families now exist as repo/business truth
- archive policy truth is now explicitly encoded in code
- archive intraday target selection is now aligned toward BL-driven focus/key-focus semantics
- archive intraday code now reflects forward-only behavior instead of historical intraday backfill behavior
- documentation in both repos has been updated to reflect these truths

### What is not completed
- requested non-equity target sizes are **not** achieved with current DB/reference truth
- 60-minute archive path is not implemented
- current-day structured-output archive is not implemented
- daily backfill anchor is not yet fully enforced as a complete orchestrator-wide policy system
- membership-change behavior is documented conceptually but not yet fully formalized as a comprehensive lifecycle subsystem

### Bottom-line assessment
This batch achieved real alignment work and closed real business-logic mismatches, but it does **not** justify claiming full archive business-logic completion.
The truthful state after this batch is:
- **policy model improved**
- **archive intraday behavior materially corrected**
- **Business Layer category families created**
- but **full intended business logic is still only partially implemented because source/reference/list coverage and some archive feature paths remain incomplete**
