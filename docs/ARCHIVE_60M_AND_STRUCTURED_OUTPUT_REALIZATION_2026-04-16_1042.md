# Archive 60m and Structured-Output Realization

_Date: 2026-04-16_1042_

## Scope
This batch moves Archive beyond policy-only alignment by implementing and validating:
1. real 60-minute archive support
2. real current-day structured-output archive writes
3. real archive run evidence with per-job / per-table deltas

Artifacts:
- `alembic/versions/036_archive_60m_and_structured_outputs.py`
- `src/ifa_data_platform/archive/archive_60min_archiver.py`
- `src/ifa_data_platform/archive/structured_output_archive.py`
- `scripts/archive_real_run_snapshot.py`
- `artifacts/archive_real_run/before_real_archive_v2.json`
- `artifacts/archive_real_run/during_real_archive_v2.json`
- `artifacts/archive_real_run/after_real_archive_v2.json`

## Milestone A — Business Layer non-equity coverage improvement
Business Layer was improved again using real contract-like DB/runtime truth.
Current truthful result:
- futures_key_focus: `0 / 20`
- futures_focus: `0 / 40`
- commodity_key_focus: `20 / 20`
- commodity_focus: `21 / 40`
- precious_metal_key_focus: `2 / 20`
- precious_metal_focus: `2 / 40`

This remains a real upstream/reference-coverage limitation, not merely a BL taxonomy problem.

## Milestone B — Archive 60m implementation
### Code added/updated
Added:
- `alembic/versions/036_archive_60m_and_structured_outputs.py`
- `src/ifa_data_platform/archive/archive_60min_archiver.py`

Updated:
- `src/ifa_data_platform/archive/archive_orchestrator.py`
- `src/ifa_data_platform/archive/archive_config.py`

### What 60m implementation does now
- introduces new archive history tables:
  - `stock_60min_history`
  - `futures_60min_history`
  - `commodity_60min_history`
  - `precious_metal_60min_history`
- derives 60m rows from available 15min history where source path exists
- keeps BL-driven symbol selection direction via focus/key_focus-style list families

### Real 60m run evidence
From the real archive run:
- `stock_60min_archive` succeeded, `60 records`
- `futures_60min_archive` succeeded, `250 records`
- `commodity_60min_archive` succeeded, `250 records`
- `precious_metal_60min_archive` succeeded, `250 records`

Per-table deltas:
- `stock_60min_history`: `0 -> 60` (`+60`)
- `futures_60min_history`: `0 -> 250` (`+250`)
- `commodity_60min_history`: `0 -> 250` (`+250`)
- `precious_metal_60min_history`: `0 -> 250` (`+250`)

### Truthful category note
60m is now implemented as a layer.
However, category-specific quality still depends on actual upstream/source/reference truth and available 15min source slices.
Financial-futures BL list coverage remains empty even though 60m rows could still be derived from existing 15min source tables.

## Milestone C — Current-day structured-output archive implementation
### Code added/updated
Added/expanded:
- `src/ifa_data_platform/archive/structured_output_archive.py`
- `alembic/versions/036_archive_60m_and_structured_outputs.py`
- orchestrator call-in from `archive_orchestrator.py`

### What is now real
Structured-output archive now writes into:
- `ifa2.daily_structured_output_archive`

Current supported source tables:
- `dragon_tiger_list_current`
- `limit_up_detail_current`
- `limit_up_down_status_current`
- `highfreq_event_stream_working`

### Real structured-output run evidence
Per-table delta:
- `daily_structured_output_archive`: `0 -> 890` (`+890`)

Meaning:
- current-day structured-output archive is no longer scaffold-only
- it is real and writes rows

### Truthful limitation
This is still a **generic** structured archive layer, not a complete family of dedicated archive tables for every summary object class.
So the feature is real but still partial in modeling richness.

## Milestone D — Real Archive execution validation
### Real run command
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker archive --runtime-budget-sec 3600
```

### Unified runtime result
- `status=succeeded`
- `governance_state=ok`
- `duration_ms=70563`

### Important runtime bug observed
Orchestrator log summary reported:
- `Window manual_archive completed: 18/17 succeeded, 0 failed, 1700 records`

That is an explicit counting bug after adding more archive jobs + structured-output archive result aggregation.
The per-job evidence and table deltas are still trustworthy, but the summary counter needs a follow-up fix.

### Per-job summary
| job | category | frequency | status | records |
|---|---|---|---|---:|
| stock_daily_archive | stock | daily | succeeded | 0 |
| macro_archive | macro | daily | succeeded | 0 |
| futures_archive | futures | daily | succeeded | 0 |
| commodity_archive | commodity | daily | succeeded | 0 |
| precious_metal_archive | precious_metal | daily | succeeded | 0 |
| stock_60min_archive | stock | 60min | succeeded | 60 |
| futures_60min_archive | futures | 60min | succeeded | 250 |
| commodity_60min_archive | commodity | 60min | succeeded | 250 |
| precious_metal_60min_archive | precious_metal | 60min | succeeded | 250 |
| stock_15min_archive | stock | 15min | succeeded | 0 |
| futures_15min_archive | futures | 15min | succeeded | 0 |
| commodity_15min_archive | commodity | 15min | succeeded | 0 |
| precious_metal_15min_archive | precious_metal | 15min | succeeded | 0 |
| stock_minute_archive | stock | 1min | succeeded | 0 |
| futures_minute_archive | futures | 1min | succeeded | 0 |
| commodity_minute_archive | commodity | 1min | succeeded | 0 |
| precious_metal_minute_archive | precious_metal | 1min | succeeded | 0 |
| structured_output_archive | structured_output | daily | succeeded | 890 |

## Per-table row-delta summary
| table | meaning | class | before | after | delta |
|---|---|---|---:|---:|---:|
| `archive_runs` | archive per-job run evidence | runtime/audit | 39 | 56 | +17 |
| `archive_checkpoints` | archive checkpoints | checkpoint | 18 | 18 | 0 |
| `archive_target_catchup` | catch-up intent/progress | catch-up | 8 | 8 | 0 |
| `archive_summary_daily` | archive summary rollup | runtime/audit | 1 | 1 | 0 |
| `stock_60min_history` | stock 60m archive | history | 0 | 60 | +60 |
| `futures_60min_history` | futures 60m archive | history | 0 | 250 | +250 |
| `commodity_60min_history` | commodity 60m archive | history | 0 | 250 | +250 |
| `precious_metal_60min_history` | precious metal 60m archive | history | 0 | 250 | +250 |
| `stock_15min_history` | stock 15m archive | history | 1290 | 1290 | 0 |
| `stock_minute_history` | stock 1m archive | history | 2410 | 2410 | 0 |
| `futures_15min_history` | futures 15m archive | history | 22912 | 22912 | 0 |
| `futures_minute_history` | futures 1m archive | history | 32000 | 32000 | 0 |
| `commodity_15min_history` | commodity 15m archive | history | 49456 | 49456 | 0 |
| `commodity_minute_history` | commodity 1m archive | history | 56000 | 56000 | 0 |
| `precious_metal_15min_history` | precious metal 15m archive | history | 16000 | 16000 | 0 |
| `precious_metal_minute_history` | precious metal 1m archive | history | 16000 | 16000 | 0 |
| `daily_structured_output_archive` | compact current-day structured archive store | structured-output archive | 0 | 890 | +890 |
| `dragon_tiger_list_history` | existing domain history table | structured-output candidate | 1989 | 1989 | 0 |
| `limit_up_detail_history` | existing domain history table | structured-output candidate | 60336 | 60336 | 0 |
| `limit_up_down_status_history` | existing domain history table | structured-output candidate | 13 | 13 | 0 |
| `unified_runtime_runs` | unified runtime evidence | runtime/audit | 12 | 13 | +1 |
| `job_runs` | generic runtime/job evidence | runtime/audit | 12 | 13 | +1 |

## Specific confirmations
### 1. 60m archive now exists
Confirmed real and writing rows.
It is no longer acceptable to describe 60m as wholly unsupported.

### 2. Current-day structured-output archive now writes real rows
Confirmed via `daily_structured_output_archive: +890`.
So structured-output archive is now real, though still generic/partial rather than fully specialized.

### 3. Intraday forward-only behavior remains preserved
1m and 15m archive jobs all executed but produced `0` rows in this run.
That is consistent with forward-only semantics and absence of new eligible forward data in this run, not with historical intraday backfill.

### 4. Backfill parameterization remains real
Code/config support remains in place through:
- `ArchiveConfig.backfill_anchor_date`
- `ArchiveConfig.backfill_days`
- checkpoint upsert flows in intraday archivers

### 5. BL-driven membership selection remains part of scope shaping
Archive still resolves symbols through BL-driven selection functions.
However, positive-row proof is strongest for 60m and weakest for new non-equity 1m/15m expansion because those intraday jobs remained 0-row in this run.

## Exact remaining partial / unsupported items
1. Futures BL list coverage still 0 because approved roots have no current DB/runtime truth.
2. Precious-metal BL list coverage still thin (2 rows only).
3. Commodity focus still below 40.
4. 1m / 15m intraday archive remains real but did not advance rows in this run.
5. Structured-output archive is real but generic; not all summary families have dedicated archive tables.
6. Archive result summary counter has a bug (`18/17 succeeded`) and needs a follow-up fix.
7. Archive index coverage is still not explicitly present in current BL target definitions.

## Final truthful judgment
This batch moved Archive materially closer to the intended business logic in a real way:
- 60m is implemented and writes rows
- structured-output archive writes rows
- archive real-run evidence now shows meaningful table advancement
- 1m/15m forward-only behavior remains intact

But full completeness still cannot be claimed because:
- non-equity BL coverage remains incomplete
- structured-output archive is still generic/partial
- 1m/15m positive-row non-equity expansion is not yet demonstrated
- archive summary accounting bug remains open
