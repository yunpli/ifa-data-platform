# Unified Acceptance Run

_Date: 2026-04-16_0838_

## Scope
This batch executed the controlled pre-production validation run using the accepted runtime model:
- one unified runtime daemon as the only official long-running entry
- four worker domains underneath it:
  - lowfreq
  - midfreq
  - highfreq
  - archive

Execution was performed as standalone local repo processes under the repo-local venv, independent from chat/OpenClaw orchestration.

## Execution environment
- repo: `/Users/neoclaw/repos/ifa-data-platform`
- venv: `/Users/neoclaw/repos/ifa-data-platform/.venv`
- DB: `postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp`
- schema: `ifa2`

## Monitoring script artifact
- script path: `scripts/monitor_unified_acceptance_run.py`

Usage:
- one-shot snapshot:
  - `./.venv/bin/python scripts/monitor_unified_acceptance_run.py once <label>`
- monitoring loop:
  - `./.venv/bin/python scripts/monitor_unified_acceptance_run.py loop 180`

Saved monitoring outputs for this batch:
- `artifacts/acceptance_monitor/pre_run_clean.json`
- `artifacts/acceptance_monitor/t_plus_1m_manual.json`
- `artifacts/acceptance_monitor/t_plus_3m.json`
- `artifacts/acceptance_monitor/t_plus_5m.json`
- `artifacts/acceptance_monitor/t_plus_10m.json`
- `artifacts/acceptance_monitor/t_plus_13m.json`

## Cleanup executed
Cleanup script artifact:
- `scripts/clean_acceptance_tables.py`

Cleanup result artifact:
- `artifacts/acceptance_cleanup_2026-04-16_0832.json`

### What was cleaned
Operational evidence / manifest / working-state residue was cleaned by contents only:
- `archive_runs` 909 -> 0
- `archive_summary_daily` 5 -> 0
- `unified_runtime_runs` 312 -> 0
- `job_runs` 336 -> 0
- `lowfreq_runs` 3313 -> 0
- `highfreq_runs` 177 -> 0
- `midfreq_execution_summary` 2 -> 0
- `highfreq_execution_summary` 10 -> 0
- `lowfreq_raw_fetch` 785 -> 0
- `target_manifest_snapshots` 328 -> 0
- all selected `highfreq_*_working` tables -> 0
- `highfreq_active_scope` kept empty
- `highfreq_dynamic_candidate` kept empty

### What was kept
Hybrid-clean keep set preserved:
- business-layer/config truth:
  - `focus_lists`
  - `focus_list_items`
  - `focus_list_rules`
  - `symbol_universe`
- trading-calendar truth:
  - `trade_cal_current`
  - `trade_cal_history`
- unified runtime schedule truth:
  - `runtime_worker_schedules`
- operator/control-plane baseline:
  - `runtime_worker_state`
- archive progression anchors:
  - `archive_checkpoints`
  - `archive_target_catchup`
  - `stock_history_checkpoint`
- reference/current/history truth tables were preserved

### Why
- cleaned tables were run evidence / manifest residue / temporary working-state residue that would confuse acceptance validation
- kept tables were canonical truth, control-plane truth, checkpoint anchors, or durable reference/history truth

## Exact run commands used
All workers were run through the unified daemon entry under the repo-local venv.

- lowfreq
  - `./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker lowfreq --runtime-budget-sec 1800`
- midfreq
  - `./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker midfreq --runtime-budget-sec 1800`
- highfreq
  - `./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker highfreq --runtime-budget-sec 900`
- archive
  - `./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker archive --runtime-budget-sec 3600`

## Runtime budgets used
- lowfreq: 1800 sec
- midfreq: 1800 sec
- highfreq: 900 sec
- archive: 3600 sec

## Monitoring / progress snapshots observed
### Pre-run clean baseline
From `pre_run_clean.json`:
- `lowfreq_runs=0`
- `job_runs=0`
- `unified_runtime_runs=0`
- `midfreq_execution_summary=0`
- `highfreq_execution_summary=0`
- `highfreq_runs=0`
- `archive_runs=0`
- `archive_summary_daily=0`
- checkpoints/catchup anchors remained:
  - `archive_checkpoints=18`
  - `archive_target_catchup=8`

### Early snapshot
At early run stage (`t_plus_3m.json`):
- lowfreq: running; `lowfreq_runs=6`
- midfreq: running; `midfreq_execution_summary=0` while job/unified rows already existed
- highfreq: already succeeded; duration `10872 ms`
- archive: running; `archive_runs=8`

### Mid snapshot
At later snapshot (`t_plus_10m.json`):
- lowfreq: still running; `lowfreq_runs=14`
- midfreq: succeeded; duration `51173 ms`
- highfreq: succeeded; duration `10872 ms`
- archive: succeeded; duration `57522 ms`; `archive_runs=13`, `archive_summary_daily=1`

### Late snapshot
Additional snapshot captured at `t_plus_13m.json` while lowfreq was still progressing. Lowfreq then completed successfully shortly after.

## Per-worker final outcome
### lowfreq
- status: `succeeded`
- governance: `ok`
- duration: `155354 ms` (~155.4s)
- tasks executed:
  - `trade_cal`
  - `stock_basic`
  - `index_basic`
  - `fund_basic_etf`
  - `sw_industry_mapping`
  - `announcements`
  - `news`
  - `research_reports`
  - `investor_qa`
  - `index_weight`
  - `etf_daily_basic`
  - `share_float`
  - `company_basic`
  - `stk_managers`
  - `new_share`
  - `name_change`
  - `top10_holders`
  - `top10_floatholders`
  - `pledge_stat`
- observed storage progress from logs included:
  - `trade_cal` 2298
  - `stock_basic` 5505
  - `index_basic` 8000
  - `announcements` 3041
  - `news` 1500
  - `research_reports` 54
  - `investor_qa` 564
  - `index_weight` 4664
  - `etf_daily_basic` 5000 fetched / 10500 canonical persisted
  - `share_float` 6000
  - `company_basic` 6272
  - `stk_managers` 4000
  - `new_share` 2000
  - `name_change` 10000
  - `top10_holders` 5000 fetched / 13962 canonical persisted
  - `top10_floatholders` 5000 fetched / 21933 canonical persisted
  - `pledge_stat` 5000 fetched / 23256 canonical persisted

### midfreq
- status: `succeeded`
- governance: `ok`
- duration: `51173 ms` (~51.2s)
- tasks executed:
  - `equity_daily_bar`
  - `index_daily_bar`
  - `etf_daily_bar`
  - `northbound_flow`
  - `limit_up_down_status`
  - `margin_financing`
  - `southbound_flow`
  - `turnover_rate`
  - `main_force_flow`
  - `sector_performance`
  - `dragon_tiger_list`
  - `limit_up_detail`
- observed storage progress from logs included:
  - `equity_daily_bar` 20
  - `index_daily_bar` 8
  - `etf_daily_bar` 12
  - `northbound_flow` 1
  - `limit_up_down_status` 1
  - `margin_financing` 360
  - `southbound_flow` 1
  - `turnover_rate` 20
  - `dragon_tiger_list` 79
  - `limit_up_detail` 7542
  - `sector_performance` 0

### highfreq
- status: `succeeded`
- governance: `ok`
- duration: `10872 ms` (~10.9s)
- tasks executed:
  - `stock_1m_ohlcv`
  - `index_1m_ohlcv`
  - `etf_sector_style_1m_ohlcv`
  - `futures_commodity_pm_1m_ohlcv`
  - `open_auction_snapshot`
  - `close_auction_snapshot`
  - `event_time_stream`
- evidence:
  - unified run row succeeded
  - highfreq worker-specific rows were recreated from clean baseline during the run
  - monitoring showed `highfreq_runs=7` shortly after completion

### archive
- status: `succeeded`
- governance: `ok`
- duration: `57522 ms` (~57.5s)
- tasks executed:
  - `archive`
- final archive orchestrator summary:
  - `Window manual_archive completed: 13/13 succeeded, 0 failed, 1291 records`

## Archive progression details
Archive finished within budget, so this is a completion/performance result rather than a timeout/stall case.

### Recorded progression
Observed from logs:
- stock archive completed: `0 records`
- futures archive completed: `0 records`
- commodity archive completed: `0 records`
- precious_metal archive completed: `0 records`
- stock 15min archive completed: `85 records`
  - examples shown:
    - `000007.SZ` archived 17 rows
    - `000032.SZ` archived 17 rows
    - `000977.SZ` archived 17 rows
    - `001339.SZ` archived 17 rows
    - `002074.SZ` archived 17 rows
- stock minute archive completed: `1205 records`
- futures minute archive completed: `0 records`
- commodity minute archive completed: `0 records`
- precious_metal minute archive completed: `0 records`

### Archive outcome judgment
- archive completed successfully within the 3600-second budget
- meaningful progression occurred
- observed material advanced:
  - `1291` total records in final window summary
  - `85` stock 15min rows
  - `1205` stock minute rows
- checkpoint/catchup anchors were preserved throughout the run and remained part of operator evidence

## What new data was created by this acceptance run
This acceptance run created fresh validation data in at least the following categories:
- new unified runtime run evidence in `ifa2.unified_runtime_runs`
- new job-level evidence in `ifa2.job_runs`
- new lane-local evidence:
  - `ifa2.lowfreq_runs`
  - `ifa2.highfreq_runs`
  - `ifa2.midfreq_execution_summary`
  - `ifa2.archive_runs`
  - `ifa2.archive_summary_daily`
- refreshed/repersisted working-state in highfreq working tables
- refreshed current/history/business-support data in multiple lowfreq and midfreq storage tables
- archive progression updates and new archive run evidence

## Important explicit note about post-run data
This run created **fresh validation data**.
That validation data is **not** the final long-lived production baseline.

Before the final true production rollout, this newly created acceptance-run data should also be cleaned again where appropriate, especially:
- operational evidence tables
- run/summary tables
- temporary working-state tables
- other validation-only residue created during this acceptance run

## Final judgment
- hybrid clean acceptance mode executed successfully
- unified-daemon manual acceptance run completed successfully for all four workers
- standalone monitoring artifact was created and used
- archive was evaluated as a real progression/performance run, not just pass/fail
- the system is now in a validated pre-production state, but the acceptance-run data itself should still be cleaned again before the final true production start
