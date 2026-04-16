# Archive Real Execution and Policy Truth

_Date: 2026-04-16_1030_

## Scope
This batch provides real archive execution evidence under the current aligned archive policy, not only dry-run or framework evidence.

Artifacts:
- `scripts/archive_real_run_snapshot.py`
- `artifacts/archive_real_run/before_real_archive.json`
- `artifacts/archive_real_run/during_real_archive.json`
- `artifacts/archive_real_run/after_real_archive.json`

## Real run command used
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker archive --runtime-budget-sec 3600
```

## Real archive run summary
Unified daemon result:
- `status=succeeded`
- `governance_state=ok`
- `duration_ms=49677`
- `tasks_executed=['archive']`
- `tables_updated=['ifa2.archive_runs', 'ifa2.archive_checkpoints', 'ifa2.archive_target_catchup']`

Archive orchestrator summary:
- `Window manual_archive completed: 13/13 succeeded, 0 failed, 0 records`

## Per-job summary
All 13 archive jobs ran and succeeded:
1. `stock_daily_archive` — stock / daily — `0 records`
2. `macro_archive` — macro / daily — `0 records`
3. `futures_archive` — futures / daily — `0 records`
4. `commodity_archive` — commodity / daily — `0 records`
5. `precious_metal_archive` — precious_metal / daily — `0 records`
6. `stock_15min_archive` — stock / 15min — `0 records`
7. `futures_15min_archive` — futures / 15min — `0 records`
8. `commodity_15min_archive` — commodity / 15min — `0 records`
9. `precious_metal_15min_archive` — precious_metal / 15min — `0 records`
10. `stock_minute_archive` — stock / 1min — `0 records`
11. `futures_minute_archive` — futures / 1min — `0 records`
12. `commodity_minute_archive` — commodity / 1min — `0 records`
13. `precious_metal_minute_archive` — precious_metal / 1min — `0 records`

## Per-table row-delta summary
Before vs after the real archive run:

| table | meaning | class | before | after | delta |
|---|---|---|---:|---:|---:|
| `archive_runs` | archive per-job run evidence | runtime/audit | 26 | 39 | +13 |
| `archive_checkpoints` | archive checkpoint rows | checkpoint | 18 | 18 | 0 |
| `archive_target_catchup` | catch-up intent/progress rows | catch-up | 8 | 8 | 0 |
| `archive_summary_daily` | daily archive summary | runtime/audit | 1 | 1 | 0 |
| `stock_15min_history` | stock 15min history | history | 1290 | 1290 | 0 |
| `stock_minute_history` | stock 1m history | history | 2410 | 2410 | 0 |
| `futures_15min_history` | futures 15min history | history | 22912 | 22912 | 0 |
| `futures_minute_history` | futures 1m history | history | 32000 | 32000 | 0 |
| `commodity_15min_history` | commodity 15min history | history | 49456 | 49456 | 0 |
| `commodity_minute_history` | commodity 1m history | history | 56000 | 56000 | 0 |
| `precious_metal_15min_history` | precious metal 15min history | history | 16000 | 16000 | 0 |
| `precious_metal_minute_history` | precious metal 1m history | history | 16000 | 16000 | 0 |
| `dragon_tiger_list_history` | compact structured daily output history | structured-output archive candidate | 1989 | 1989 | 0 |
| `limit_up_detail_history` | compact structured daily output history | structured-output archive candidate | 60336 | 60336 | 0 |
| `limit_up_down_status_history` | compact structured daily output history | structured-output archive candidate | 13 | 13 | 0 |
| `unified_runtime_runs` | unified runtime evidence | runtime/audit | 11 | 12 | +1 |
| `job_runs` | generic job evidence | runtime/audit | 11 | 12 | +1 |

## Logic confirmation from the real run
### 1m forward-only behavior
Confirmed operationally in the sense that 1m jobs ran but did not perform historical catch-up writes.
Observed 0-row result across:
- `stock_minute_archive`
- `futures_minute_archive`
- `commodity_minute_archive`
- `precious_metal_minute_archive`

This is consistent with forward-only semantics rather than multi-year backfill behavior.

### 15m forward-only behavior
Confirmed similarly:
- `stock_15min_archive`
- `futures_15min_archive`
- `commodity_15min_archive`
- `precious_metal_15min_archive`
all ran and wrote 0 rows in this real pass.

That is consistent with a forward-only policy where no new eligible forward window data was added during this run.

### Backfill anchor / backfill_days parameter effect
Code truth now supports:
- `backfill_anchor_date`
- `backfill_days`

In this real run, that parameterization existed in code/config/checkpoint flow, but the observed execution produced no new history rows, so this run validates the existence of parameterized control rather than demonstrating a positive-row bounded backfill case.

### BL-driven membership selection in practice
Code path is now aligned to BL-driven selection via `archive_scope_symbols(...)`.
However, the real run produced 0 intraday rows, so this batch confirms the selection path is wired but does not yet prove positive data expansion from the newly improved BL non-equity lists.

### Current-day structured-output archive status
Current-day structured-output archive is still **partial / scaffold-only**.
Evidence:
- candidate tables checked:
  - `dragon_tiger_list_history`
  - `limit_up_detail_history`
  - `limit_up_down_status_history`
- all remained unchanged in this real run

Therefore:
- current-day structured outputs are explicitly recognized in code/docs
- but no real new write happened in this archive run
- this remains partial rather than completed

### 60m archive status
- still **unsupported / unimplemented**
- no 60m archive job ran
- policy matrix explicitly marks 60m as unsupported at current code truth

## Residual gap classification
### Source/reference limitation
- approved financial-futures roots still have no current DB/runtime truth, so futures BL lists remain empty
- precious_metal contract coverage remains too narrow to fill 20/40 targets

### Reference/seed limitation
- commodity improved materially, but broader 40-name focus still remains short because current contract truth is not broad enough

### Runtime limitation
- current-day structured-output archive is only scaffold-level
- 60m archive is not implemented
- archive run still emits unrelated midfreq registration logs at startup (runtime hygiene issue)

### Storage limitation
- none newly discovered in this run for archive history tables; they simply received 0 new rows

## Truthful final judgment
What is truly implemented now:
- real archive run through unified daemon
- per-job archive execution evidence
- real touched-table evidence
- forward-only 1m/15m behavior direction reflected in practice by zero-row no-backfill execution
- BL-driven selection path in code
- parameterized backfill controls in code/config

What is still partial / unsupported:
- 60m archive
- current-day structured-output archive real writing path
- positive-row proof for new BL-driven non-equity intraday expansion
- full non-equity BL target-size completion

This batch therefore proves real runtime behavior and real touched-table truth, but it does not justify claiming full archive feature completeness.
