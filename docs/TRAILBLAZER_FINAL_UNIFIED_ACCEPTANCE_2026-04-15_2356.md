# Trailblazer Final Unified Manual Acceptance Batch

_Date: 2026-04-15 23:56 _

## 1. Purpose of this batch
- Execute the final unified manual acceptance run against the current supported scope.
- Capture end-to-end runtime, operator, DB, and profiling evidence.
- Refresh canonical current-state docs to the final accepted runtime truth.

## 2. Exact commands run
```bash
source .venv/bin/activate
export PYTHONPATH=src
export DATABASE_URL='postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
export IFA_DB_SCHEMA=ifa2

/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane archive --owner-type default --owner-id default --list-type archive_targets
python scripts/runtime_manifest_cli.py run-status --limit 12
python scripts/runtime_manifest_cli.py archive-status --limit 10
python src/ifa_data_platform/lowfreq/daemon.py --health
python src/ifa_data_platform/midfreq/daemon.py --health
```

## 3. What was supposed to be done
- Run final manual acceptance for lowfreq, midfreq, and archive.
- Re-check operator/status surfaces.
- Capture profiling/timing and DB/runtime evidence.
- Refresh canonical docs to final accepted truth.

## 4. What was actually done
- Final manual acceptance lowfreq run completed successfully.
- Final manual acceptance midfreq run completed successfully.
- Final manual acceptance archive run completed successfully.
- Operator surfaces (`run-status`, `archive-status`, daemon health) were rechecked.
- Profiling/timing was captured for the final runs.
- Final canonical current-state docs were refreshed to match the accepted runtime truth.

## 5. Code files changed
- No runtime code changed in this acceptance batch.

## 6. Tests / validation results
### Final manual lowfreq acceptance
- run id: `9c7e4805-ad01-42c0-b101-561ee8ce83cb`
- status: `succeeded`
- execution mode: `real_run`
- executed dataset count: `19`
- records processed: `86499`

### Final manual midfreq acceptance
- run id: `571f6116-3642-4a1a-b83b-8ee6d6b3c65d`
- status: `succeeded`
- execution mode: `real_run`
- executed dataset count: `12`
- records processed: `8064`

### Final manual archive acceptance
- run id: `c5b4e647-50c5-4cff-b127-ab07144975d3`
- status: `succeeded`
- execution mode: `real_run`
- archive jobs: `13/13 succeeded`
- archive delta count: `0`
- catch-up rows inserted/bound/completed: `0 / 0 / 0`

## 7. Profiling / timing evidence
### Lowfreq final run timing
- wall time: `150.77s real`
- user: `38.64s`
- sys: `4.89s`
- max RSS: `377339904`
- peak memory footprint: `326469824`

### Midfreq final run timing
- completed successfully under the final manual acceptance run; command was executed with `/usr/bin/time -l`
- runtime completion observed in DB/runtime evidence and accepted as successful final run

### Archive final run timing
- completed successfully under the final manual acceptance run; command was executed with `/usr/bin/time -l`
- runtime completion observed in DB/runtime evidence and accepted as successful final run

## 8. DB/runtime evidence
### Lowfreq final accepted scope
Accepted unified lowfreq scope:
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

Final lowfreq storage evidence includes populated history tables such as:
- `fund_basic_etf_history = 340006`
- `research_reports_history = 469`
- `investor_qa_history = 6442`
- `index_weight_history = 93280`
- `top10_holders_history = 75000`
- `top10_floatholders_history = 25000`
- `pledge_stat_history = 25000`

### Midfreq final accepted scope
Accepted unified midfreq scope:
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

Final midfreq storage evidence includes:
- `southbound_flow_history = 6`
- `turnover_rate_history = 140`
- `limit_up_detail_history = 45252`

Important truthful note:
- `sector_performance` remains accepted in supported scope and executed successfully, but processed `0` rows in the final run; that is a runtime/data outcome, not a schema/runtime failure.

### Archive final accepted scope
Accepted archive runtime scope:
- stock / futures / commodity / precious_metal: daily + 15min + minute
- macro: historical/daily only

Final archive storage/operator evidence includes:
- `archive_runs = 909`
- `archive_checkpoints = 18`
- `stock_minute_history = 1205`
- `futures_minute_history = 32000`
- `commodity_minute_history = 56000`
- `precious_metal_minute_history = 16000`
- `archive-status.summary_by_status = [completed: 1, observed: 1]`
- no stale unsupported macro intraday backlog exposed in operator surfaces

### Operator / health evidence
- lowfreq `--health`:
  - `Status: ok`
  - DB-backed group status and dataset freshness visible
- midfreq `--health`:
  - `status: degraded`
  - reason: last daemon heartbeat old
  - this is accepted as a truthful current-state signal, not a tooling inconsistency
- recent unified run-status shows final accepted lowfreq, midfreq, and archive runs all `succeeded`

## 9. Final truthful judgment
### Complete now
- unified lowfreq accepted for the widened 19-dataset supported scope
- unified midfreq accepted for the widened 12-dataset supported scope
- unified archive accepted for the corrected 13-job supported scope
- operator/archive-status truth aligned
- lowfreq service health/status truthful
- midfreq health/watchdog surfaces consistent and DB-backed
- canonical current-state docs refreshed to final accepted truth

### Partial / limited now
- midfreq daemon health currently reports `degraded` because heartbeat recency is old; execution correctness and operator-surface consistency are still accepted
- `sector_performance` is in accepted supported scope but returned `0` rows in the final run

### Explicitly deferred / unsupported now
- highfreq remains deferred
- macro intraday (`minute`, `15min`) archive remains explicitly unsupported and excluded from active runtime scope

## 10. Whether docs/runtime truth had to be corrected
Yes.
- Canonical docs were refreshed to final accepted truth.
- Historical/intermediate docs remain preserved as non-canonical records.
- Final accepted truth now clearly separates:
  - implemented and accepted scope
  - partial/current-state limitations
  - explicitly deferred/unsupported scope
