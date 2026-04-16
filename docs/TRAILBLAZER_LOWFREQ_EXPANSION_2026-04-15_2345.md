# Trailblazer Lowfreq Expansion Batch

_Date: 2026-04-15 23:45 _

## 1. Purpose of this batch
- Expand unified lowfreq from the earlier small subset to the broader currently enabled production lowfreq dataset set.
- Align unified runtime with current lowfreq registry/daemon/storage reality.

## 2. What was supposed to be done
- Re-check enabled lowfreq registry truth.
- Widen unified lowfreq planned execution to the realistically supported production dataset set.
- Run real lowfreq validation and capture storage evidence.

## 3. What was actually done
- Verified enabled lowfreq registry is materially broader than the older six-dataset subset.
- Verified current/history storage support exists for the widened supported set used in this batch.
- Expanded unified lowfreq planned dataset set to include:
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
- Updated lowfreq integration expectation to the widened supported set.
- Ran a fresh real lowfreq unified execution against the widened set.

## 4. Code files changed
- `src/ifa_data_platform/runtime/unified_runtime.py`
- `tests/integration/test_unified_runtime.py`

## 5. Tests run and results
- Focused integration test:
  - `pytest tests/integration/test_unified_runtime.py::test_unified_runtime_run_once_lowfreq_real_run_executes -q`
  - result: completed successfully in the post-change validation step
- Real-run validation:
  - `python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default`
  - result: succeeded for the widened supported set

## 6. DB/runtime evidence
### Current-head widened lowfreq unified run
- unified run id: `0d40bde4-4ef4-4b1e-bdb5-23e58fcd4fef`
- status: `succeeded`
- execution mode: `real_run`
- executed dataset count: `19`
- datasets executed successfully included:
  - `trade_cal = 2298`
  - `stock_basic = 5505`
  - `index_basic = 8000`
  - `fund_basic_etf = 10000`
  - `sw_industry_mapping = 3000`
  - `announcements = 2811`
  - `news = 1500`
  - `research_reports = 54`
  - `investor_qa = 395`
  - `index_weight = 4664`
  - `etf_daily_basic = 5000`
  - `share_float = 6000`
  - `company_basic = 6272`
  - `stk_managers = 4000`
  - `new_share = 2000`
  - `name_change = 10000`
  - `top10_holders = 5000`
  - `top10_floatholders = 5000`
  - `pledge_stat = 5000`

### Storage evidence after widened run
- `fund_basic_etf_current/history` populated
- `research_reports_current/history` populated
- `investor_qa_current/history` populated
- `index_weight_current/history` populated
- `etf_daily_basic_current/history` populated
- `share_float_current/history` populated
- `stk_managers_current/history` populated
- `new_share_current/history` populated
- `name_change_current/history` populated
- `top10_holders_current/history` populated
- `top10_floatholders_current/history` populated
- `pledge_stat_current/history` populated

## 7. Truthful result / judgment
- Unified lowfreq no longer lags behind the older narrow six-dataset subset.
- Current truthful supported unified lowfreq scope now includes the widened 19-dataset production-oriented set above.
- This materially improves lowfreq readiness toward real operational use.

## 8. Residual gaps / blockers if any
- Additional enabled lowfreq datasets beyond this widened set should still be judged individually against real source/storage/runtime value before inclusion in the active unified path.
- After lowfreq and midfreq expansion, remaining implementation-first work should focus on any still-unclosed archive/lowfreq/midfreq service-mode/state-persistence/operator-readiness gaps before final unified acceptance.

## 9. Whether docs/runtime truth had to be corrected
Yes.
- Earlier lowfreq wording that effectively treated the smaller subset as the active unified lowfreq scope is now stale.
- Canonical docs will need refresh after the remaining implementation batches complete so they reflect the widened real lowfreq scope accurately.
