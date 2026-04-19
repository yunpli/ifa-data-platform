# Archive Pre-Production Cleanup Audit

Generated: 2026-04-19 02:55 PDT
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## Summary

This cleanup batch removed Archive V2 development / validation / manual-test residue before the next formal production run, while protecting production-triggered Archive V2 truth and all non-Archive truth tables.

Truthful final conclusion:
- **manual/test Archive V2 run evidence has been cleaned out**
- **manual/test-linked completeness has been cleaned out**
- **legacy `archive_runs` test/validation residue has been cleaned out**
- **only protected production-triggered Archive V2 rows remain**
- **the system is clean enough to enter the next formal production run**

---

## Scope used for cleanup

### Lookback window
- last 30 days of Archive V2 manual/dev/test activity

### Cleanup strategy
1. identify manual/dev/test `ifa_archive_runs` + `ifa_archive_run_items`
2. derive `business_date × family` scope from those runs
3. protect any `business_date × family` pair also written by:
   - `production_nightly_archive_v2`
   - `runtime_archive_v2_nightly`
4. delete only **manual-only** Archive V2 data pairs
5. delete manual/test Archive V2 evidence rows
6. delete legacy `archive_runs` rows with clear test/validation/retest naming

### Protected by design — intentionally not touched
- Business Layer truth/config tables
- trading calendar / trade day truth tables
- runtime schedule truth tables (`runtime_worker_schedules`)
- runtime worker state truth tables
- canonical retained source truth tables
- production-triggered Archive V2 data/evidence on protected pairs

---

## Cleanup evidence sources

Artifacts:
- `artifacts/archive_preprod_cleanup_plan_20260419.json`
- `artifacts/archive_preprod_cleanup_apply_20260419.json`

### Scope stats
- scoped dates found: `17`
- scoped families found: `39`
- deletable manual-only pairs: `282`
- protected production-overlap pairs: `11`

### Example scoped dates
- `2025-06-16`
- `2025-09-12`
- `2025-12-18` .. `2025-12-31`
- `2026-01-30`
- `2026-04-14`
- `2026-04-15`
- `2026-04-16`
- `2026-04-17`

### Why some data was protected
`2026-04-17` overlaps with production-triggered Archive V2 nightly truth.
So cleanup did **not** blindly delete all rows for that date.
It protected production-overlap `business_date × family` pairs and only removed manual-only residue.

---

## Tables touched and rows deleted/reset

## Archive V2 data tables — aggregated deleted rows
- `ifa_archive_equity_daily`: `70,972`
- `ifa_archive_etf_daily`: `24,119`
- `ifa_archive_limit_up_detail_daily`: `15,087`
- `ifa_archive_non_equity_daily`: `12,785`
- `ifa_archive_announcements_daily`: `6,997`
- `ifa_archive_news_daily`: `3,575`
- `ifa_archive_equity_1m`: `1,928`
- `ifa_archive_commodity_1m`: `1,575`
- `ifa_archive_equity_15m`: `808`
- `ifa_archive_investor_qa_daily`: `503`
- `ifa_archive_precious_metal_1m`: `450`
- `ifa_archive_sector_performance_daily`: `394`
- `ifa_archive_highfreq_event_stream_daily`: `382`
- `ifa_archive_futures_1m`: `225`
- `ifa_archive_dragon_tiger_daily`: `130`
- `ifa_archive_research_reports_daily`: `108`
- `ifa_archive_commodity_15m`: `105`
- `ifa_archive_equity_60m`: `54`
- `ifa_archive_commodity_60m`: `49`
- `ifa_archive_macro_daily`: `39`
- `ifa_archive_precious_metal_15m`: `30`
- `ifa_archive_index_daily`: `24`
- `ifa_archive_futures_15m`: `15`
- `ifa_archive_precious_metal_60m`: `14`
- `ifa_archive_futures_60m`: `7`
- `ifa_archive_index_1m`: `6`
- `ifa_archive_limit_up_down_status_daily`: `2`
- `ifa_archive_highfreq_intraday_signal_state_daily`: `1`
- `ifa_archive_highfreq_leader_candidate_daily`: `1`
- `ifa_archive_highfreq_limit_event_stream_daily`: `1`
- `ifa_archive_highfreq_sector_breadth_daily`: `1`
- `ifa_archive_highfreq_sector_heat_daily`: `1`
- `ifa_archive_index_15m`: `1`
- `ifa_archive_index_60m`: `1`

## Archive V2 evidence/control cleanup
- `ifa_archive_completeness_manual_only`: `298`
- `ifa_archive_repair_queue_manual_dates`: `202`
- `ifa_archive_run_items_manual`: `1,292`
- `ifa_archive_runs_manual_orphan`: `125`

## Legacy archive test evidence cleanup
- `archive_runs_test_legacy`: `0`

Direct DB verification after cleanup:
- remaining manual Archive V2 runs: `0`
- remaining manual Archive V2 run_items: `0`
- remaining manual-linked completeness rows: `0`
- remaining legacy test/validation `archive_runs`: `0`

---

## Remaining Archive V2 rows after cleanup — why they were left

After cleanup, remaining scoped rows were:
- `ifa_archive_equity_daily`: `5,497`
- `ifa_archive_index_daily`: `8`
- `ifa_archive_etf_daily`: `1,946`
- `ifa_archive_non_equity_daily`: `1,076`
- `ifa_archive_macro_daily`: `3`
- `ifa_archive_completeness`: `3`
- `ifa_archive_run_items`: `99`

These were **not** treated as residue.
They remain because they are protected production-overlap truth/evidence, not manual/dev/test residue.

---

## Tables intentionally not touched

Not touched by cleanup:
- Business Layer truth/config
- trading calendar / trade-day truth
- runtime schedule truth
- runtime worker state truth
- canonical retained source history truth
- production-triggered Archive V2 protected pairs

Reason:
- this batch was strictly pre-production cleanup of Archive development/testing residue only
- it was not a truth reset of the running system

---

## Final judgment

### Is archive development/testing residue cleaned out?
**Yes**, for manual/dev/test Archive V2 residue.

### Is there any meaningful test residue left that would pollute the next formal production run?
**No**.

### Can the system enter the next formal production run from a cleanup perspective?
**Yes**.
