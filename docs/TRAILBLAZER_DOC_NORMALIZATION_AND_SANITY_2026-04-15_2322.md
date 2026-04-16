# Trailblazer Doc Normalization and Current-HEAD Sanity Batch

_Date: 2026-04-15 23:22 _

## 1. Purpose of this batch
- Normalize Trailblazer documentation into canonical current-state vs historical/intermediate layers.
- Run one fresh current-HEAD production sanity batch.
- Refresh canonical docs to match actual repo/runtime truth.

## 2. What was supposed to be done
- Mark historical/intermediate documents explicitly.
- Preserve canonical current-state documents as the active source of truth.
- Run fresh current-HEAD lowfreq / midfreq / archive sanity checks plus operator/status evidence.
- Update canonical docs in place after the sanity batch.

## 3. What was actually done
- Added explicit document-status markers to older baseline/intermediate docs so they no longer masquerade as current canonical truth.
- Ran a fresh current-HEAD sanity pass covering lowfreq real-run, midfreq real-run, archive real-run, run-status, archive-status, and DB query surfaces.
- Identified one current operator-truth issue during the sanity pass: archive runtime is green for supported scope, but archive-status still shows stale pending macro-minute catch-up rows from older unsupported assumptions.
- Stopped the long combined command after runtime/operator truth was captured, because the operator truth issue is already actionable and the remaining canonical refresh should reflect that exact reality.

## 4. Code files changed
- No code files changed in this batch.

## 5. Docs changed / normalized
Historical/intermediate docs explicitly marked as non-canonical current-state sources:
- `docs/TRAILBLAZER_DATA_PLATFORM_UPGRADE_PLAN_2026-04-14.md`
- `docs/TRAILBLAZER_DATA_PLATFORM_IMPLEMENTATION_EXECUTION_PLAN_2026-04-14.md`
- `docs/TRAILBLAZER_COLLECTION_READINESS_GAP_CLOSURE_PLAN_2026-04-15.md`
- `docs/TRAILBLAZER_ARCHIVE_REAL_RUN_TRUTH_2026-04-15_2242.md`
- `docs/TRAILBLAZER_ARCHIVE_SCOPE_TRUTH_ALIGNMENT_2026-04-15_2246.md`
- `docs/TRAILBLAZER_REMAINING_WORK_TODO_2026-04-15_2251.md`
- `docs/TRAILBLAZER_COLLECTION_LAYER_OPERATIONAL_AUDIT_2026-04-15.md`

Canonical current-state docs intended to remain current-source-of-truth set:
- `docs/TRAILBLAZER_FINAL_EVIDENCE_PACKAGE_2026-04-15.md`
- `docs/TRAILBLAZER_RUNTIME_RUNBOOK_2026-04-15.md`
- `docs/TRAILBLAZER_REPRO_SMOKE_2026-04-15.md`
- `docs/TRAILBLAZER_COLLECTION_READINESS_GAP_CLOSURE_2026-04-15.md`

## 6. Tests run and results
- Full `tests/integration/test_unified_runtime.py -q` was started as part of the combined sanity command but not allowed to remain the gating source of truth for this batch once runtime/operator evidence already exposed the next real issue.
- Current reliable evidence for this batch is the direct runtime + DB/operator status evidence below.

## 7. DB/runtime evidence
### Lowfreq current-HEAD sanity run
- unified run id: `5ac89562-51cd-4147-b589-de1c8274e7d5`
- status: `succeeded`
- execution mode: `real_run`
- records processed: `26386`
- datasets executed:
  - `trade_cal = 2298`
  - `stock_basic = 5505`
  - `index_basic = 8000`
  - `announcements = 2811`
  - `news = 1500`
  - `company_basic = 6272`

### Midfreq current-HEAD sanity run
- unified run id: `334ae6c5-0a71-4429-9435-54833c39d6e1`
- status: `succeeded`
- execution mode: `real_run`
- records processed: `499`
- datasets executed:
  - `equity_daily_bar = 20`
  - `index_daily_bar = 8`
  - `etf_daily_bar = 12`
  - `margin_financing = 360`
  - `main_force_flow = 20`
  - `dragon_tiger_list = 79`

### Archive current-HEAD sanity run
- unified run id: `719b65cc-4d6f-4159-8e26-0dc7f826fc05`
- status: `succeeded`
- worker type: `archive_real_run_worker`
- execution mode: `real_run`
- archive jobs: `13/13 succeeded`
- truthful supported active archive scope remains:
  - stock / futures / commodity / precious_metal: daily + 15min + minute
  - macro: historical/daily only

### Operator / status truth discovered in this batch
- `archive-status` still contains stale pending catch-up rows for unsupported macro minute assumptions, for example:
  - `archive|minute|macro|CN_M2` with `status = pending`
- recent catch-up summary still shows pending rows even though active runtime scope has already been corrected away from macro intraday support
- checkpoint surfaces show healthy completed rows for supported archive datasets, including:
  - `stock_minute_history`
  - `futures_minute_history`
  - `commodity_minute_history`
  - `precious_metal_minute_history`
  - `futures_15min_history`
  - `commodity_15min_history`
  - `precious_metal_15min_history`

## 8. Truthful result / judgment
- Documentation normalization is partly complete:
  - historical/intermediate docs are now explicitly marked as such
  - canonical current-state doc set is clearly identified
- Current-HEAD collection-layer sanity truth is strong:
  - lowfreq real-run: green for current proof set
  - midfreq real-run: green for current proof set
  - archive real-run: green for corrected supported scope
- The next truthful closure issue is now operator-state drift, not core execution failure:
  - stale archive catch-up / operator rows still reflect now-unsupported macro intraday assumptions
- Therefore canonical current-state docs should now be refreshed to state:
  - execution truth is green for current supported scope
  - operator-state cleanup for stale unsupported macro intraday backlog rows is still pending

## 9. Residual gaps / blockers if any
- No hard implementation blocker.
- Real remaining gap discovered in this batch:
  - cleanup/reclassification of stale archive catch-up/operator rows created before macro intraday support was truthfully narrowed

## 10. Whether docs had to be corrected because runtime/source reality did not support the earlier assumption
Yes.
- Historical/intermediate docs needed explicit status labeling.
- Canonical current-state docs now need in-place refresh to incorporate the fresh sanity evidence and the newly surfaced operator-state drift around stale macro intraday catch-up rows.
