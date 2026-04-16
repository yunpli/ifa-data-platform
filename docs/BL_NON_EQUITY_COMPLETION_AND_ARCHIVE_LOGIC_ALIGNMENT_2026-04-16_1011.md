# BL Non-Equity Completion + Archive Logic Alignment

_Date: 2026-04-16_1011_

## Scope
This batch completes the next combined Business Layer + Data Platform implementation step around:
1. non-equity Business Layer family completion
2. archive policy/runtime alignment
3. backfill/forward-archive formalization
4. documentation truth alignment

## Business Layer result summary
Business Layer repo deliverables:
- `scripts/seed_non_equity_focus_lists.py`
- `scripts/inspect_symbol_universe.py`
- `artifacts/non_equity_focus_seed_2026-04-16_1005.json`
- `docs/NON_EQUITY_FOCUS_LISTS_2026-04-16.md`
- `docs/NON_EQUITY_FOCUS_LISTS_2026-04-16_1010.md`

### Implemented list families
- `default_futures_key_focus`
- `default_futures_focus`
- `default_commodity_key_focus`
- `default_commodity_focus`
- `default_precious_metal_key_focus`
- `default_precious_metal_focus`

### Truthful seeding result
Actual resolvable inserts from current DB/runtime truth:
- futures_key_focus: `0 / 20`
- futures_focus: `0 / 40`
- commodity_key_focus: `6 / 20`
- commodity_focus: `6 / 40`
- precious_metal_key_focus: `2 / 20`
- precious_metal_focus: `2 / 40`

This batch therefore achieves:
- **Business Layer category-family completion**
- but **not full non-equity population completeness**

## Archive gap summary
### Already matched / improved in this batch
- archive unified-runtime positioning already matched and remains intact
- intraday archive policy now has an explicit code-level matrix in `archive_policy.py`
- intraday target selection is now driven toward BL membership semantics
- stock/futures-family intraday paths now enforce forward-only behavior
- backfill anchor is now parameterized in config (`backfill_anchor_date`, `backfill_days`)

### Partial after this batch
- current-day structured-output archive is now partially implemented as a registry/service scaffold in `structured_output_archive.py`
- it truthfully enumerates supported archiveable current-day outputs vs unsupported ones
- but it is not yet a full independent persistent archive subsystem

### Still missing / unsupported
- 60-minute archive path is still not implemented
- full daily-backfill orchestration around `2023-01-01` / `N days` is only partially formalized (config + checkpoint anchoring are present; full fleet-wide rollout is not complete)
- membership-change future behavior is represented through BL-driven selection semantics, but not yet as a dedicated lifecycle/change-management subsystem
- non-equity BL coverage remains sparse because underlying DB/runtime truth remains sparse

## Code/docs updated in Data Platform repo
Added:
- `src/ifa_data_platform/archive/archive_policy.py`
- `src/ifa_data_platform/archive/structured_output_archive.py`
- `tests/unit/test_archive_policy.py`
- `docs/BL_NON_EQUITY_COMPLETION_AND_ARCHIVE_LOGIC_ALIGNMENT_2026-04-16_1008.md`
- `docs/BL_NON_EQUITY_COMPLETION_AND_ARCHIVE_LOGIC_ALIGNMENT_2026-04-16_1011.md`

Updated:
- `src/ifa_data_platform/archive/archive_config.py`
- `src/ifa_data_platform/archive/archive_orchestrator.py`
- `src/ifa_data_platform/archive/stock_15min_archiver.py`
- `src/ifa_data_platform/archive/stock_minute_archiver.py`
- `src/ifa_data_platform/archive/futures_intraday_archiver.py`
- `docs/ARCHIVE_RUNTIME_AND_DATA_STATUS.md`

## Tests run
- `python3 -m pytest -q tests/unit/test_archive_policy.py tests/integration/test_unified_runtime_daemon.py`
- result: `6 passed, 72 warnings in 0.38s`

## DB/runtime evidence
### BL evidence
- `artifacts/non_equity_focus_seed_2026-04-16_1005.json`
- proves list-family creation + actual inserted counts + honest shortfall

### Archive runtime evidence
- `python3 -m ifa_data_platform.runtime.unified_daemon --worker archive --runtime-budget-sec 3600 --dry-run-manifest-only`
- result:
  - `status=succeeded`
  - `governance_state=ok`
  - `tables_updated=[ifa2.archive_runs, ifa2.archive_checkpoints, ifa2.archive_target_catchup]`

### Archive policy evidence
`test_archive_policy.py` proves policy matrix contains the intended key business distinctions:
- daily rows exist and are supported
- 15m rows are forward-only and supported
- 1m rows are forward-only and supported
- 60m rows exist but are currently marked unsupported
- commodity 1m policy uses `commodity_key_focus`

## Truthful final judgment
### Completed in a production-meaningful way
- BL non-equity list families now exist in repo code/docs/DB truth
- archive intraday semantics are materially corrected to forward-only behavior
- archive backfill control is now parameterized at config/policy level instead of being only a fixed implicit behavior
- archive selection logic is now aligned toward BL membership semantics rather than only broad category heuristics
- archive docs now explicitly distinguish implemented / partial / unsupported logic

### Not completed / cannot be truthfully overclaimed
- non-equity lists do **not** meet intended target counts with current DB/reference truth
- 60m archive support is still missing
- current-day structured-output archive is only partially implemented
- full daily backfill fleet alignment is not yet complete
- the system should not yet claim full archive-business-logic closure

### Bottom-line assessment
This batch moves the system from “archive business logic documented but not well-enforced” toward “archive business logic explicitly encoded and partially enforced in production code,” while keeping unsupported areas explicit.
That is the truthful state after this implementation batch.
