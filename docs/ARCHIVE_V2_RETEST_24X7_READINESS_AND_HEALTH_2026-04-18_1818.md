# Archive V2 Re-test / 24x7 Readiness / Run-Evidence / Archive-Health Report

Generated: 2026-04-18 18:18 PDT
Repo: `/Users/neoclaw/repos/ifa-data-platform`
Environment: `/Users/neoclaw/repos/ifa-data-platform/.venv`
DB: `postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp` / schema `ifa2`

## 1. Scope of this batch

This batch executed four things only:
1. Archive V2 **Run A** re-test: one January 2026 trading day, normal daily/final scope plus `60m`
2. Archive V2 **Run B** re-test: 10 consecutive trading days in December 2025, production-relevant daily/final scope
3. 24x7 production-readiness review for lowfreq / midfreq / highfreq / unified runtime / Archive V2
4. Verification of DB run evidence + archive health/completeness reporting, with missing reporting surfaces added where needed

No redesign work was done here.

---

## 2. Helper scripts added in this batch

### 2.1 `scripts/archive_v2_measured_batch.py`
Purpose:
- run an exact Archive V2 target batch over an explicit date list
- perform narrow cleanup only for the requested archive scope
- measure before/after rows and rough table storage deltas
- capture run id, run items, touched tables, rows written, and evidence-table changes

### 2.2 `scripts/archive_v2_health_report.py`
Purpose:
- produce a read-only archive health/completeness report directly from DB
- show family/frequency coverage windows
- show recent date health summaries
- show incomplete/gap rows
- show repair backlog and recent archive runs

These were added because existing Archive V2 operator surfaces were helpful but still awkward for this exact measurement/reporting batch.

---

## 3. Test date selection truth

### Run A requested constraint
User requested one **actual trading day in January 2026**.
Selected date:
- **2026-01-30**

### Run B requested constraint
User requested **10 consecutive trading days in December 2025**.
Selected dates:
- `2025-12-18`
- `2025-12-19`
- `2025-12-22`
- `2025-12-23`
- `2025-12-24`
- `2025-12-25`
- `2025-12-26`
- `2025-12-29`
- `2025-12-30`
- `2025-12-31`

Trading-day selection was verified from market-calendar source, not guessed.

Important truth:
- these are real trading days
- but the local retained-history coverage for these windows is incomplete in the current DB
- therefore Archive V2 re-tests for these windows were expected to be partially constrained by upstream retained-truth availability

---

## 4. Run A — one-day Archive V2 with daily/final + 60m

## 4.1 Exact run scope
Date:
- `2026-01-30`

Family scope used:
- production daily/final families:
  - `equity_daily`
  - `index_daily`
  - `etf_daily`
  - `non_equity_daily`
  - `macro_daily`
  - `announcements_daily`
  - `news_daily`
  - `research_reports_daily`
  - `investor_qa_daily`
  - `dragon_tiger_daily`
  - `limit_up_detail_daily`
  - `limit_up_down_status_daily`
  - `sector_performance_daily`
  - `highfreq_event_stream_daily`
  - `highfreq_limit_event_stream_daily`
  - `highfreq_sector_breadth_daily`
  - `highfreq_sector_heat_daily`
  - `highfreq_leader_candidate_daily`
  - `highfreq_intraday_signal_state_daily`
- plus `60m` families:
  - `equity_60m`
  - `index_60m`
  - `futures_60m`
  - `commodity_60m`
  - `precious_metal_60m`
  - `proxy_60m`

## 4.2 Exact cleanup scope before Run A
Only the exact Archive V2 scope for `2026-01-30` was cleared.
No unrelated dates were touched.
No unrelated archive tables were touched.

Tables cleaned by exact date scope:
- `ifa_archive_announcements_daily`
- `ifa_archive_commodity_60m`
- `ifa_archive_dragon_tiger_daily`
- `ifa_archive_equity_60m`
- `ifa_archive_equity_daily`
- `ifa_archive_etf_daily`
- `ifa_archive_futures_60m`
- `ifa_archive_highfreq_event_stream_daily`
- `ifa_archive_highfreq_intraday_signal_state_daily`
- `ifa_archive_highfreq_leader_candidate_daily`
- `ifa_archive_highfreq_limit_event_stream_daily`
- `ifa_archive_highfreq_sector_breadth_daily`
- `ifa_archive_highfreq_sector_heat_daily`
- `ifa_archive_index_60m`
- `ifa_archive_index_daily`
- `ifa_archive_investor_qa_daily`
- `ifa_archive_limit_up_detail_daily`
- `ifa_archive_limit_up_down_status_daily`
- `ifa_archive_macro_daily`
- `ifa_archive_news_daily`
- `ifa_archive_non_equity_daily`
- `ifa_archive_precious_metal_60m`
- `ifa_archive_proxy_60m`
- `ifa_archive_research_reports_daily`
- `ifa_archive_sector_performance_daily`

Evidence state cleaned by exact date+family scope:
- `ifa_archive_completeness`
- `ifa_archive_repair_queue`

Exact command used:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_measured_batch.py \
  --profile-name runA_archive_v2_prod_daily_plus_60m_2026_01_30 \
  --dates 2026-01-30 \
  --family-groups \
    equity_daily index_daily etf_daily non_equity_daily macro_daily \
    announcements_daily news_daily research_reports_daily investor_qa_daily \
    dragon_tiger_daily limit_up_detail_daily limit_up_down_status_daily sector_performance_daily \
    highfreq_event_stream_daily highfreq_limit_event_stream_daily \
    highfreq_sector_breadth_daily highfreq_sector_heat_daily \
    highfreq_leader_candidate_daily highfreq_intraday_signal_state_daily \
    equity_60m index_60m futures_60m commodity_60m precious_metal_60m proxy_60m \
  --trigger-source manual_retest_run_a \
  --notes 'Run A measured archive v2 production daily plus 60m' \
  --output artifacts/runA_archive_v2_prod_daily_plus_60m_2026_01_30.json
```

## 4.3 Run A measured times
- run id: `3ffb4c3a-2095-46e7-95d5-b68e3d0d91c1`
- start time: `2026-04-18 18:15:36.829223-07:00`
- end time: `2026-04-18 18:15:39.604909-07:00`
- duration: **2.79 sec**

## 4.4 Run A truthful status
- overall status: **partial**

This is truthful, not hidden.

Why partial:
- for `2026-01-30`, several daily/final retained families do not currently have local retained truth in the DB for that date
- for `2026-01-30`, requested `60m` families also do not currently have retained intraday truth in local source tables for that date

Families that remained incomplete in Run A:
- `commodity_60m`
- `equity_60m`
- `futures_60m`
- `index_60m`
- `precious_metal_60m`
- `proxy_60m`
- `announcements_daily`
- `dragon_tiger_daily`
- `highfreq_event_stream_daily`
- `highfreq_intraday_signal_state_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_limit_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `index_daily`
- `investor_qa_daily`
- `limit_up_detail_daily`
- `limit_up_down_status_daily`
- `news_daily`
- `research_reports_daily`
- `sector_performance_daily`

## 4.5 Run A touched tables / rows added / rough storage added
Tables with real scope-row additions:
- `ifa_archive_equity_daily` -> **5,462** rows added, rough storage +**1,859,584** bytes
- `ifa_archive_etf_daily` -> **1,890** rows added, rough storage +**622,592** bytes
- `ifa_archive_non_equity_daily` -> **1,066** rows added, rough storage +**450,560** bytes
- `ifa_archive_macro_daily` -> **3** rows added, rough storage +**0** bytes (below page-growth threshold)

Evidence-table deltas:
- `ifa_archive_runs` -> +1 row
- `ifa_archive_run_items` -> +25 rows
- `ifa_archive_completeness` -> +25 scoped rows written/updated
- `ifa_archive_repair_queue` -> +21 scoped rows written/updated for incomplete families

Requested/touched destination tables with zero added rows (truthful no-source/incomplete outcome):
- `ifa_archive_index_daily`
- `ifa_archive_announcements_daily`
- `ifa_archive_news_daily`
- `ifa_archive_research_reports_daily`
- `ifa_archive_investor_qa_daily`
- `ifa_archive_limit_up_detail_daily`
- `ifa_archive_limit_up_down_status_daily`
- `ifa_archive_sector_performance_daily`
- all requested `60m` archive tables in this run
- highfreq-derived daily archive tables in this run

Total rough storage added across watched tables:
- **2,973,696 bytes** (~2.84 MiB)

---

## 5. Run B — 10 consecutive trading days in December 2025

## 5.1 Exact run scope
Dates:
- `2025-12-18`
- `2025-12-19`
- `2025-12-22`
- `2025-12-23`
- `2025-12-24`
- `2025-12-25`
- `2025-12-26`
- `2025-12-29`
- `2025-12-30`
- `2025-12-31`

Production-relevant daily/final family scope only:
- `equity_daily`
- `index_daily`
- `etf_daily`
- `non_equity_daily`
- `macro_daily`
- `announcements_daily`
- `news_daily`
- `research_reports_daily`
- `investor_qa_daily`
- `dragon_tiger_daily`
- `limit_up_detail_daily`
- `limit_up_down_status_daily`
- `sector_performance_daily`
- `highfreq_event_stream_daily`
- `highfreq_limit_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_intraday_signal_state_daily`

## 5.2 Exact cleanup scope before Run B
Only the exact Archive V2 scope for the 10 requested December trading days was cleared.
No unrelated dates were touched.
No unrelated tables were touched.

Archive tables cleaned by exact date scope:
- `ifa_archive_announcements_daily`
- `ifa_archive_dragon_tiger_daily`
- `ifa_archive_equity_daily`
- `ifa_archive_etf_daily`
- `ifa_archive_highfreq_event_stream_daily`
- `ifa_archive_highfreq_intraday_signal_state_daily`
- `ifa_archive_highfreq_leader_candidate_daily`
- `ifa_archive_highfreq_limit_event_stream_daily`
- `ifa_archive_highfreq_sector_breadth_daily`
- `ifa_archive_highfreq_sector_heat_daily`
- `ifa_archive_index_daily`
- `ifa_archive_investor_qa_daily`
- `ifa_archive_limit_up_detail_daily`
- `ifa_archive_limit_up_down_status_daily`
- `ifa_archive_macro_daily`
- `ifa_archive_news_daily`
- `ifa_archive_non_equity_daily`
- `ifa_archive_research_reports_daily`
- `ifa_archive_sector_performance_daily`

Evidence state cleaned by exact date+family scope:
- `ifa_archive_completeness`
- `ifa_archive_repair_queue`

Exact command used:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_measured_batch.py \
  --profile-name runB_archive_v2_prod_daily_10trading_2025_12 \
  --dates 2025-12-18 2025-12-19 2025-12-22 2025-12-23 2025-12-24 2025-12-25 2025-12-26 2025-12-29 2025-12-30 2025-12-31 \
  --family-groups \
    equity_daily index_daily etf_daily non_equity_daily macro_daily \
    announcements_daily news_daily research_reports_daily investor_qa_daily \
    dragon_tiger_daily limit_up_detail_daily limit_up_down_status_daily sector_performance_daily \
    highfreq_event_stream_daily highfreq_limit_event_stream_daily \
    highfreq_sector_breadth_daily highfreq_sector_heat_daily \
    highfreq_leader_candidate_daily highfreq_intraday_signal_state_daily \
  --trigger-source manual_retest_run_b \
  --notes 'Run B measured archive v2 production daily 10 trading days' \
  --output artifacts/runB_archive_v2_prod_daily_10trading_2025_12.json
```

## 5.3 Run B measured times
- run id: `711837e7-c4b5-4caa-adcf-0b967c2f00d1`
- start time: `2026-04-18 18:15:55.691562-07:00`
- end time: `2026-04-18 18:16:12.888196-07:00`
- duration: **17.21 sec**

## 5.4 Run B truthful status
- overall status: **partial**

This is truthful, not hidden.

Why partial:
- local retained coverage for the selected December 2025 window is strong for `equity_daily`, `etf_daily`, `non_equity_daily`, and `macro_daily`
- but retained source truth is missing in the current DB for the other production-relevant families across that full 10-day window

Families repeatedly incomplete across the 10-day range:
- `announcements_daily`
- `dragon_tiger_daily`
- `highfreq_event_stream_daily`
- `highfreq_intraday_signal_state_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_limit_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `index_daily`
- `investor_qa_daily`
- `limit_up_detail_daily`
- `limit_up_down_status_daily`
- `news_daily`
- `research_reports_daily`
- `sector_performance_daily`

## 5.5 Run B touched tables / rows added / rough storage added
Tables with real scope-row additions:
- `ifa_archive_equity_daily` -> **54,518** rows added, rough storage +**18,620,416** bytes
- `ifa_archive_etf_daily` -> **18,346** rows added, rough storage +**6,184,960** bytes
- `ifa_archive_non_equity_daily` -> **10,645** rows added, rough storage +**4,456,448** bytes
- `ifa_archive_macro_daily` -> **30** rows added, rough storage +**0** bytes (below page-growth threshold)

Evidence-table deltas:
- `ifa_archive_runs` -> +1 row
- `ifa_archive_run_items` -> +190 rows
- `ifa_archive_completeness` -> +190 scoped rows written/updated
- `ifa_archive_repair_queue` -> +150 scoped rows written/updated for incomplete families

Requested/touched destination tables with zero added rows in this range:
- `ifa_archive_index_daily`
- `ifa_archive_announcements_daily`
- `ifa_archive_news_daily`
- `ifa_archive_research_reports_daily`
- `ifa_archive_investor_qa_daily`
- `ifa_archive_limit_up_detail_daily`
- `ifa_archive_limit_up_down_status_daily`
- `ifa_archive_sector_performance_daily`
- all requested highfreq-derived daily archive tables in this run

Total rough storage added across watched tables:
- **29,458,432 bytes** (~28.09 MiB)

---

## 6. Run-evidence / DB logging truth

## 6.1 Archive V2 manual runs
This is already strongly evidenced in DB.
Manual Archive V2 runs record:
- `trigger_source`
- `profile_name`
- `mode`
- `start_time`
- `end_time`
- `status`
- `notes`

Manual examples present:
- `manual_retest_run_a`
- `manual_retest_run_b`
- `manual_profile`

Tables:
- `ifa_archive_runs`
- `ifa_archive_run_items`
- `ifa_archive_completeness`
- `ifa_archive_repair_queue`

Conclusion:
- **Archive V2 manual run evidence is already production-usable.**

## 6.2 Archive V2 automatic/runtime-triggered runs
Also already evidenced in DB.
Automatic examples present:
- `production_nightly_archive_v2`
- `runtime_archive_v2_nightly`

Conclusion:
- **Archive V2 runtime-triggered evidence is present and queryable.**

## 6.3 Unified runtime lane evidence
`ifa2.unified_runtime_runs` currently gives usable lane-level evidence for runtime-managed runs, including:
- `lane`
- `trigger_mode` (`scheduled` / `manual_once`)
- `status`
- `started_at`
- `completed_at`
- `records_processed`
- `schedule_key`
- summary/governance fields in JSON

Examples verified:
- scheduled `lowfreq`
- scheduled `midfreq`
- manual_once `highfreq`
- manual_once `archive_v2`

Conclusion:
- **unified runtime DB evidence exists and is usable** for distinguishing manual vs automatic at the lane level.

## 6.4 Layer-specific native evidence truth
### lowfreq
Verified:
- `lowfreq_runs` contains per-dataset rows with:
  - `dataset_name`
  - `run_type`
  - `status`
  - `started_at`
  - `completed_at`
  - `records_processed`
- scheduled/unified-runtime executions are visible as `run_type='unified_runtime'`

Conclusion:
- **usable native DB evidence exists**

### highfreq
Verified:
- `highfreq_runs` contains per-dataset rows with:
  - `run_id`
  - `dataset_name`
  - `status`
  - `created_at`
  - `records_processed`
- unified runtime also records lane-level evidence separately in `unified_runtime_runs`

Conclusion:
- **usable DB evidence exists**, though operator-friendly summary comes mainly from unified runtime + native run rows together

### midfreq
Truthful limitation:
- `midfreq_execution_summary` exists and is useful
- but it is leaner than ideal and does **not** carry the same rich manual/automatic trigger metadata as `unified_runtime_runs`
- fields such as direct `trigger_mode` and per-dataset status are not first-class there

Operational truth:
- if midfreq is run through the **official manual path** (`unified_daemon --worker midfreq`), `unified_runtime_runs` provides the manual/automatic distinction and status timing

Conclusion:
- **DB evidence is usable for the official runtime/manual path**, but **native midfreq evidence is thinner than lowfreq / highfreq / Archive V2**

## 6.5 Overall run-evidence judgment
The requirement is **mostly satisfied now** if operators use the official runtime/manual surfaces:
- lowfreq: yes
- midfreq: yes through unified runtime path, but native table is thin
- highfreq: yes
- Archive V2: yes

No additional logging schema change was made in this batch because:
- the evidence model is already sufficient for the official manual/runtime paths
- the bigger remaining issue is operational alignment, not missing core evidence rows

---

## 7. Archive health / completeness reporting truth

## 7.1 What already existed
Existing operator surfaces already present:
- `scripts/archive_v2_operator_cli.py summary`
- `recent-runs`
- `family-health`
- `date-health`
- `repair-backlog`
- `gaps`
- `claimed-backlog`
- `suppressed-backlog`

These are useful, but they have one operational sharp edge:
- concurrent CLI invocations can block each other because `ensure_schema()` still performs DDL-on-startup locking behavior

## 7.2 What was added now
Added read-only script:
- `scripts/archive_v2_health_report.py`

This provides a direct DB report for:
- family/frequency coverage windows
- earliest/latest seen dates
- earliest/latest completed dates
- recent date-level archive health
- latest incomplete/gap rows
- repair backlog snapshot
- recent archive runs

Example command:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_health_report.py --days 30 --limit 40 --output artifacts/archive_v2_health_report_20260418.json
```

Conclusion:
- **archive health/completeness reporting is now practical and readable**
- existing operator CLI is still valid
- the new read-only report script is the least-risk surface for batch reporting and avoids broadening into schema redesign

---

## 8. 24x7 production-readiness review

## 8.1 Lowfreq
Judgment: **mostly ready**

Why:
- scheduled runs exist
- unified-runtime evidence exists
- retained truth writes are real
- dataset-level run evidence exists

No immediate fatal blocker was found in this batch.

## 8.2 Midfreq
Judgment: **runnable, but evidence surface is thinner than ideal**

Why:
- scheduled runtime path exists
- retained truth writes are real
- unified-runtime evidence exists

Limitation:
- native summary table is lean and not as operator-rich as lowfreq/highfreq/archive_v2

## 8.3 Highfreq
Judgment: **runnable under current model, but still operationally supervised rather than bulletproof**

Why:
- manual_once and runtime evidence exist
- working truth + derived writes are real

Limitation:
- this is still working-truth/stateful intraday infrastructure; it is not the same as fully hardened autonomous 24x7 process supervision

## 8.4 Unified runtime / daemon
Judgment: **not yet cleanly 24x7-ready as a fully trusted single production control plane**

Main blockers:
1. **Archive V2 schedule mismatch**
   - code intent says nightly archive should be `archive_v2`
   - live `runtime_worker_schedules` still has enabled legacy `archive` rows
   - live schedule DB has **no `archive_v2` rows**

2. **Worker-state alignment gap**
   - `runtime_worker_state` has `archive`, `highfreq`, `lowfreq`, `midfreq`
   - **no `archive_v2` worker state row** currently exists

3. **Concurrency / DDL-on-startup sharp edge**
   - multiple archive/operator CLIs can deadlock or block each other because they all perform schema-ensure behavior on startup
   - this is acceptable for supervised/manual work, but it is a 24x7 operations smell

4. **Repeated partial nightly archive_v2 evidence**
   - recent `production_nightly_archive_v2` and `runtime_archive_v2_nightly` rows are repeatedly partial
   - this is truthful and expected when upstream retained truth is missing, but it means nightly success semantics are not yet cleanly green

## 8.5 Archive V2
Judgment: **production-usable for supervised/manual nightly path, not yet cleanly ready as an unattended 24x7 final nightly system**

Why:
- run/completeness/repair evidence is real
- manual and runtime-triggered runs are real
- operator reporting is real
- measured Run A / Run B executed correctly and truthfully recorded partial outcomes

But not yet fully 24x7-clean because:
- runtime schedule DB still points at legacy `archive`
- local retained-history coverage gaps drive many partial outcomes for historical windows
- CLI concurrency/startup locking still needs hardening

## 8.6 Overall 24x7 readiness judgment
Truthful answer:

> **The system is runnable and materially functional, but it is not yet cleanly ready for unattended 24x7 production with Archive V2 as the unambiguous nightly control-plane path.**

What is ready enough now:
- supervised/manual Archive V2 operation
- measurable archive runs
- DB run evidence
- archive completeness / repair reporting
- lowfreq/midfreq/highfreq scheduled/manual execution under supervision

What still blocks a clean 24x7 “set-and-forget” judgment:
- live daemon schedule still wired to legacy `archive`, not `archive_v2`
- repeated partial nightly Archive V2 outcomes because upstream retained coverage is incomplete
- concurrency/DDL-on-startup issue in operator/archive CLIs

---

## 9. Final judgment

### Run A
- executed successfully as a measured test
- truthful result: **partial**
- demonstrated that Archive V2 can run the requested daily/final + 60m scope and record exact incomplete families when retained truth is missing

### Run B
- executed successfully as a measured test over the requested 10 trading days
- truthful result: **partial**
- demonstrated real multi-date write volume and real completeness/repair evidence behavior

### Run evidence
- already materially present and production-usable for official runtime/manual paths
- strongest in Archive V2 and unified runtime
- adequate in lowfreq/highfreq
- thinner in native midfreq surface but still usable through unified runtime

### Archive health reporting
- now practical and readable via:
  - existing operator CLI
  - newly added read-only `scripts/archive_v2_health_report.py`

### 24x7 readiness
Final truthful call:

> **Not yet fully 24x7-ready for unattended production.**
>
> It is **supervised-production-capable**, but the system still needs runtime scheduling alignment (`archive_v2` vs legacy `archive`) and some operational hardening before it deserves a clean unattended 24x7-ready judgment.
