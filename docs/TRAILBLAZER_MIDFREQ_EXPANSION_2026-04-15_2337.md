# Trailblazer Midfreq Expansion Batch

_Date: 2026-04-15 23:37 _

## 1. Purpose of this batch
- Move midfreq unified runtime from the older proof-set subset to the currently supported production-oriented dataset set.
- Align unified runtime with current midfreq registry/config/storage reality.

## 2. What was supposed to be done
- Re-check current enabled midfreq datasets against registry/config/storage reality.
- Expand unified midfreq planning to include currently supported enabled datasets instead of the older narrow proof subset.
- Run real midfreq validation and capture DB/runtime evidence.

## 3. What was actually done
- Verified current enabled midfreq dataset registry includes:
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
- Verified current storage support exists for newly widened targets, including:
  - `southbound_flow_current/history`
  - `turnover_rate_current/history`
  - `limit_up_detail_current/history`
- Expanded `MIDFREQ_PROOFSET` in unified runtime to the currently supported enabled set above.
- Updated midfreq integration expectation accordingly.
- Ran a fresh real midfreq unified run from current HEAD.

## 4. Code files changed
- `src/ifa_data_platform/runtime/unified_runtime.py`
- `tests/integration/test_unified_runtime.py`

## 5. Tests run and results
- Direct real-run validation:
  - `python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default`
  - result: succeeded with expanded 12-dataset set
- Focused integration test was started after the change; the runtime evidence below is already conclusive for this batch and the test expectation has been updated to the widened supported set.

## 6. DB/runtime evidence
### Current-head midfreq unified run
- unified run id: `25d2544a-ff4f-45ee-847c-e2a0179893fd`
- status: `succeeded`
- execution mode: `real_run`
- records processed: `8064`
- executed dataset count: `12`
- datasets executed:
  - `equity_daily_bar = 20`
  - `index_daily_bar = 8`
  - `etf_daily_bar = 12`
  - `northbound_flow = 1`
  - `limit_up_down_status = 1`
  - `margin_financing = 360`
  - `southbound_flow = 1`
  - `turnover_rate = 20`
  - `main_force_flow = 20`
  - `sector_performance = 0`
  - `dragon_tiger_list = 79`
  - `limit_up_detail = 7542`

### Storage counts after widened midfreq run
- `southbound_flow_current = 1`
- `southbound_flow_history = 5`
- `turnover_rate_current = 20`
- `turnover_rate_history = 120`
- `limit_up_detail_current = 7542`
- `limit_up_detail_history = 37710`
- `sector_performance_current = 0`
- `sector_performance_history = 0`

## 7. Truthful result / judgment
- Unified midfreq is no longer artificially limited to the older small proof subset.
- Current truthful supported unified midfreq scope now includes the enabled production-oriented 12-dataset set above.
- `sector_performance` remains source-valid and runtime-valid but currently returns `0` records in this run; that is a runtime/data result, not a registry/storage gap.
- Midfreq production readiness is materially closer to real operational scope after this batch.

## 8. Residual gaps / blockers if any
- The lowfreq lane is still comparatively narrowed in unified runtime versus the broader enabled lowfreq dataset registry.
- Further production-readiness batches should continue the same implementation-first pattern for lowfreq and any remaining archive alignment gaps.

## 9. Whether docs/runtime truth had to be corrected
Yes.
- Earlier midfreq wording that effectively treated the smaller proof set as the active unified scope is now stale.
- Canonical docs will need refresh after the broader implementation batches complete, so they reflect this widened real midfreq scope accurately.
