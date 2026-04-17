# Clean Reset and Bounded Validation

_Date: 2026-04-16_1904_

## Scope
This batch created a clean validation state and then ran bounded unified-daemon validations for:
- lowfreq
- midfreq
- highfreq
- archive

Artifacts:
- `scripts/validation_clean_reset.py`
- `scripts/bounded_validation_snapshot.py`
- `artifacts/validation_clean_reset_2026-04-16_1859.json`
- `artifacts/bounded_validation/before_validation.json`
- `artifacts/bounded_validation/during_validation.json`
- `artifacts/bounded_validation/after_validation.json`

## Cleanup executed
### What was cleaned
Fully reset recent runtime/test residue from:
- `unified_runtime_runs`
- `job_runs`
- `lowfreq_runs`
- `highfreq_runs`
- `midfreq_execution_summary`
- `highfreq_execution_summary`
- `target_manifest_snapshots`
- `lowfreq_raw_fetch`
- highfreq working-state / temporary derived-state tables

Recent archive/test residue cleaned for roughly the last 5 days from:
- `archive_runs`
- `archive_summary_daily`
- `daily_structured_output_archive`

### What was kept
Preserved intact:
- Business Layer truth/config tables
- focus/list-family truth tables
- runtime schedule/policy tables
- `trade_cal_current` / `trade_cal_history`
- archive checkpoints/catch-up anchors
- long-term baseline history/reference tables

### Why
This created a clean validation state while preserving canonical truth and long-term baselines.

## Exact run commands and budgets
### lowfreq
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker lowfreq --runtime-budget-sec 300
```

### midfreq
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker midfreq --runtime-budget-sec 300
```

### highfreq
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker highfreq --runtime-budget-sec 300
```

### archive
```bash
./.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker archive --runtime-budget-sec 1200
```

Budgets used:
- lowfreq: 300 sec
- midfreq: 300 sec
- highfreq: 300 sec
- archive: 1200 sec

## Lowfreq validation result
### Outcome
- finished within budget
- status: succeeded

### Touched tables / row deltas
- `unified_runtime_runs`: `0 -> 4` (+4 across all workers)
- `job_runs`: `0 -> 4` (+4 across all workers)
- `lowfreq_runs`: `0 -> 19` (+19)

Primary data-table deltas attributable to lowfreq:
- `trade_cal_history`: `126304 -> 128602` (+2298)
- `stock_basic_history`: `297195 -> 302700` (+5505)
- `index_basic_history`: `432018 -> 440018` (+8000)
- `fund_basic_etf_history`: baseline retained; fresh lowfreq write path ran again
- `announcements_history`: increased
- `news_history`: increased
- `research_reports_history`: increased
- `investor_qa_history`: increased
- `company_basic_history`: increased
- `stk_managers_history`: increased
- `new_share_history`: increased
- `name_change_history`: increased
- `top10_holders_history`: increased
- `top10_floatholders_history`: increased
- `pledge_stat_history`: increased

### What the new rows correspond to
- trading calendar truth
- stock/index/reference universes
- announcements/news/research/IR QA
- company/shareholding/corporate-reference data

### Runtime evidence rows created
- 1 new lowfreq unified run row
- 19 lowfreq run rows
- 1 generic job run envelope at unified level

### Validation-phase judgment
Sufficient for this bounded validation phase.
Lowfreq clearly re-populated a broad set of reference/history outputs from clean runtime evidence state.

## Midfreq validation result
### Outcome
- finished within budget
- status: succeeded

### Touched tables / row deltas
- `equity_daily_bar_history`: increased
- `index_daily_bar_history`: increased
- `etf_daily_bar_history`: increased
- `northbound_flow_history`: increased
- `limit_up_down_status_history`: increased
- `margin_financing_history`: increased
- `southbound_flow_history`: increased
- `turnover_rate_history`: increased
- `main_force_flow_history`: increased
- `dragon_tiger_list_history`: increased
- `limit_up_detail_history`: increased
- `sector_performance_history`: remained 0/unchanged

### What the new rows correspond to
- stock/index/ETF daily bars
- northbound/southbound flow
- margin financing / turnover / main-force flow
- dragon-tiger list
- limit-up detail and market breadth status

### Runtime evidence rows created
- unified runtime evidence increased
- generic job evidence increased
- `midfreq_execution_summary` remained at 0 row-count despite runtime success

### Validation-phase judgment
Sufficient for bounded validation.
Still retains one known source-empty / summary-materialization gap:
- `sector_performance_history` unchanged
- summary-table materialization still not a trustworthy sole operator surface

## Highfreq validation result
### Outcome
- finished within budget
- status: succeeded

### Touched tables / row deltas
Highfreq working-state tables were repopulated from zeroed state:
- `highfreq_stock_1m_working`: `0 -> 6`
- `highfreq_index_1m_working`: `0 -> 6`
- `highfreq_proxy_1m_working`: `0 -> 1`
- `highfreq_futures_minute_working`: `0 -> 40`
- `highfreq_open_auction_working`: `0 -> 1`
- `highfreq_close_auction_working`: `0 -> 1`
- `highfreq_event_stream_working`: `0 -> 400`

Remained zero:
- `highfreq_sector_breadth_working`
- `highfreq_sector_heat_working`
- `highfreq_leader_candidate_working`
- `highfreq_intraday_signal_state_working`
- `highfreq_limit_event_stream_working`
- `highfreq_active_scope`
- `highfreq_dynamic_candidate`

### What the new rows correspond to
- stock/index/proxy 1m slices
- non-equity intraday raw slice
- open/close auction snapshots
- event timestamp stream

### Runtime evidence rows created
- `highfreq_runs`: `0 -> 7`
- unified runtime evidence increased
- generic job evidence increased

### Validation-phase judgment
Sufficient for bounded validation of the highfreq raw lane.
Derived-signal/state layers still remain sparse/zero and should not be overclaimed.

## Archive forward-validation result
### Outcome
- finished within budget
- status: succeeded

### Forward-oriented jobs
Archive still ran the current archive worker set including:
- 60m jobs
- 15m jobs
- 1m jobs
- structured-output archive

### Forward proof in this bounded run
Observed positive-row proof for 60m + structured-output archive in the bounded validation window:
- `stock_60min_history`: `0 -> 60` (+60)
- `futures_60min_history`: `0 -> 250` (+250)
- `commodity_60min_history`: `0 -> 250` (+250)
- `precious_metal_60min_history`: `0 -> 250` (+250)
- `daily_structured_output_archive`: `0 -> 890` (+890)

### If still zero elsewhere
1m / 15m archive remained unchanged in this bounded validation run.
That is consistent with forward-only behavior and absence of fresh eligible forward material in the tested window.

## Archive bounded-backfill result
### What was checked
This bounded validation used a clean recent-runtime state but preserved long-term history/checkpoint truth.
The purpose was to verify that archive can still operate coherently with:
- preserved checkpoint anchors
- preserved long-term history baselines
- bounded runtime budget

### Observed checkpoint / catch-up truth
- `archive_checkpoints`: preserved and remained stable during the run
- `archive_target_catchup`: preserved and remained stable during the run
- `archive_runs`: increased from cleaned recent state as new archive jobs executed
- `archive_summary_daily`: recreated from cleaned recent state

### Backfill judgment
This bounded validation demonstrates:
- archive can run against preserved checkpoint state
- recent test residue can be removed without breaking archive progression logic
- 60m and structured-output archive can repopulate fresh rows from a clean recent state

However, this batch does **not** yet prove a day-by-day 10-day recent-gap backfill sweep as a positive-row behavior across intraday categories.
So the truthful bounded-backfill conclusion is:
- backfill control remains parameterized and coherent
- checkpoint/catch-up state remains intact
- but this run is stronger as a clean-state forward/near-history validation than as a full explicit 10-day recent-gap backfill proof

## Touched-table / row-delta truth summary
### Archive runtime/audit
- `archive_runs`: recreated/increased from cleaned state
- `archive_summary_daily`: recreated
- `unified_runtime_runs`: recreated/increased
- `job_runs`: recreated/increased

### Archive history / structured-output
- `stock_60min_history`: +60
- `futures_60min_history`: +250
- `commodity_60min_history`: +250
- `precious_metal_60min_history`: +250
- `daily_structured_output_archive`: +890
- 1m / 15m history tables: unchanged in this run

### Checkpoint / catch-up
- `archive_checkpoints`: no row-count delta, anchors preserved
- `archive_target_catchup`: no row-count delta, anchors preserved

## Final truthful judgment
### Lowfreq
- bounded validation succeeded
- touched many core reference/history tables
- sufficient for this validation phase

### Midfreq
- bounded validation succeeded
- core market-structure/history tables advanced
- one known zero-result / summary-surface issue remains (`sector_performance` / summary materialization)

### Highfreq
- bounded validation succeeded
- raw working-state was repopulated from clean reset
- sufficient for raw-lane validation, but not proof of rich derived-state closure

### Archive
- bounded validation succeeded within budget
- forward archive behavior is positively demonstrated through:
  - 60m archive deltas
  - structured-output archive deltas
- checkpoint/catch-up state remained coherent after clean reset
- 1m / 15m remained zero in this bounded run, consistent with forward-only/no-fresh-material behavior
- bounded backfill remains partially demonstrated at control/state level, but not yet fully proven as an explicit recent-10-day fill sweep in this batch

Overall:
- the system is now in a much cleaner validation state
- low/mid/high/archive all ran through unified daemon under bounded budgets
- archive forward behavior is materially demonstrated
- explicit recent-gap bounded backfill proof remains only partial and should not be overstated
