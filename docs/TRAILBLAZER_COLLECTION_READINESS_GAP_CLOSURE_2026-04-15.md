# Collection Layer Operational Readiness Gap Closure Audit

> **Canonical current-state status:** Canonical current-state document. Refreshed against current HEAD sanity evidence after doc normalization. This remains the current accepted readiness-gap closure report, with truth updated in place.

> **Current truth snapshot:** archive is operationally green for corrected supported scope (stock/futures/commodity/precious_metal daily+15min+minute; macro historical/daily only); lowfreq and midfreq are operationally green for the currently proven proof sets; minute data is explicitly real only for supported archive categories above; highfreq remains deferred; remaining closure gap is operator-state cleanup/reclassification for stale macro intraday catch-up rows created under older assumptions.

_Date: 2026-04-15_

## Final accepted phase judgments (Milestones A-C)

### Archive (Milestone A)
**Accepted for this phase** at the strongest truthful level achieved, but the current repo/runtime truth is now stronger and more specific than this earlier frozen wording.

Current truthful state after later validation:
- unified archive lane now executes implemented archive jobs in `real_run` mode
- implemented archive window currently contains 14 jobs, not the older smaller review-state count
- real execution is present for implemented daily / 15min / minute jobs across stock / futures / commodity / precious_metal, plus daily macro
- the current truthful failing path is `macro_15min_archive`, which raises `NotImplementedError` because no real source/storage path exists in the current repo

Current residuals retained for future work:
- `macro_15min_archive` — not truthfully supported in current source/storage/runtime reality
- any category/frequency pair without a real source/storage/runtime path must be classified explicitly rather than treated as implicitly supported

### Lowfreq (Milestone B)
**Accepted for this phase** with the required proof set materially closed.

Closed in this phase:
- required proof datasets executed with real non-dry-run evidence:
  - `trade_cal`
  - `stock_basic`
  - `index_basic`
  - `fund_basic_etf`
  - `sw_industry_mapping`
  - `news_basic`
- required non-dry-run subset satisfied for:
  - `trade_cal`
  - `stock_basic`
- service-mode smoke proven on the lowfreq daemon path
- unified runtime lowfreq mode corrected from forced dry-run to explicit `real_run`

### Midfreq (Milestone C)
**Accepted for this phase** at the strongest truthful level achieved.

Closed in this phase:
- mandatory proof-set runnable evidence for:
  - `equity_daily_bar`
  - `index_daily_bar`
  - `etf_daily_bar`
  - `northbound_flow`
  - `limit_up_down_status`
- safe non-dry-run proof established for:
  - `northbound_flow`
  - `limit_up_down_status`
  - `index_daily_bar`
- mandatory registry truth reconciled to `source_name='tushare'`
- real daemon-state persistence bug fixed in `midfreq_window_state.succeeded_today`
- service-mode smoke exposed broader configured-set drift instead of hiding it

Explicit residuals retained for future work:
- `southbound_flow` is not production-runnable: missing `ifa2.southbound_flow_history`
- `turnover_rate`, `sector_performance`, and `limit_up_detail` remain weaker/zero-row proof paths in this phase
- `equity_daily_bar` runnable path returned zero rows in this phase and should not be overstated

### Highfreq
Explicitly deferred to a future phase. No highfreq implementation expansion was performed in this readiness-gap closure round.

## Scope

This report is a factual audit/update focused on operational-readiness gaps in the current collection layer reality for:
- lowfreq
- midfreq
- archive

Explicitly out of scope for this phase:
- highfreq implementation work
- reopening broad Trailblazer architecture/blueprint work

This report distinguishes between:
- manifest/selector coverage
- registered dataset/config coverage
- actual runnable collection coverage
- actual backfill/update volume

---

## Commands run in this phase

### Repo/runtime inspection
```bash
cd /Users/neoclaw/repos/ifa-data-platform
rg -n "daemon|run_forever|while True|loop_interval|ArchiveOrchestrator|LowFreqRunner|MidfreqRunner|highfreq|UnifiedRuntime|scheduler|worker" -S src scripts tests
find src/ifa_data_platform -maxdepth 3 -type f | sort
find scripts -maxdepth 2 -type f | sort
```

### Manual validation runs
```bash
cd /Users/neoclaw/repos/ifa-data-platform
source .venv/bin/activate
export PYTHONPATH=src
export DATABASE_URL='postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
export IFA_DB_SCHEMA=ifa2

/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane archive --owner-type default --owner-id default --list-type archive_targets
```

### Dataset/config evidence
```bash
python3 - <<'PY'
import sqlalchemy as sa
from sqlalchemy import text
engine=sa.create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp', future=True)
with engine.connect() as conn:
    rows=conn.execute(text('select dataset_name, market, source_name, job_type, enabled, runner_type, watermark_strategy, description from ifa2.lowfreq_datasets order by dataset_name')).mappings().all()
    for r in rows: print(dict(r))
    rows=conn.execute(text('select dataset_name, market, source_name, job_type, enabled, runner_type, watermark_strategy, description from ifa2.midfreq_datasets order by dataset_name')).mappings().all()
    for r in rows: print(dict(r))
PY
```

### Runtime/DB evidence
```bash
python3 - <<'PY'
import sqlalchemy as sa
from sqlalchemy import text
engine=sa.create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp', future=True)
with engine.connect() as conn:
    tables=['job_runs','unified_runtime_runs','target_manifest_snapshots','archive_target_catchup','archive_checkpoints','archive_runs','archive_summary_daily','lowfreq_daemon_state']
    for t in tables:
        cnt=conn.execute(text(f"select count(*) from ifa2.{t}")).scalar_one()
        print(t, cnt)
PY
```

---

# 1. Lowfreq readiness gap closure

## 1.1 What lowfreq datasets are actually runnable now?

### Registered lowfreq datasets (real DB registry)
The lowfreq registry contains many enabled datasets, including real non-test entries such as:
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
- `stk_holdernumber`
- `name_change`
- plus deeper weekly datasets such as:
  - `top10_holders`
  - `top10_floatholders`
  - `pledge_stat`
  - `forecast`
  - `margin`
  - `north_south_flow`
  - `management`
  - `stock_equity_change`

### Real daemon-config group coverage
From `lowfreq/daemon_config.py`:
- `daily_light` group includes 17 real datasets
- `weekly_deep` group includes 24 real datasets

This means lowfreq has **substantial real framework/config surface**, not just a toy single-dataset daemon.

## 1.2 What lowfreq categories are truly covered in real execution now?

### Manifest-level category presence
The latest canonical lowfreq real-run evidence still shows manifest categories:
- `stock`
- `futures`
- `macro`
- `commodity`
- `precious_metal`

### Actual manual collection execution evidence in the latest final state
Latest canonical run inspected from `ifa2.unified_runtime_runs`:
```bash
python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default
```

Returned fields from the latest canonical persisted row:
- `run_id = 76192792-2641-4b1f-8f8a-b36c87bd50cd`
- `execution_mode = real_run`
- `planned_dataset_names = ["trade_cal", "stock_basic", "index_basic", "fund_basic_etf", "sw_industry_mapping", "news_basic"]`
- `executed_dataset_count = 6`
- dataset results:
  - `trade_cal` → `succeeded` → `records_processed = 2297`
  - `stock_basic` → `succeeded` → `records_processed = 5502`
  - `index_basic` → `succeeded` → `records_processed = 8000`
  - `fund_basic_etf` → `succeeded` → `records_processed = 10000`
  - `sw_industry_mapping` → `succeeded` → `records_processed = 3000`
  - `news_basic` → `succeeded` → `records_processed = 1500`
- `records_processed = 30299`

### Actual lowfreq collection coverage proven by this latest run
- **stock**: yes, proven by executed datasets `trade_cal`, `stock_basic`, `index_basic`, `fund_basic_etf`, `sw_industry_mapping`, `news_basic`

### Categories present in manifest logic but NOT separately proven collected by this latest run
- **futures**: manifest-visible, not separately proven collected by a futures-specific lowfreq dataset in this run
- **macro**: manifest-visible, not separately proven collected by a macro-specific lowfreq dataset in this run
- **commodity**: manifest-visible, not separately proven collected by a commodity-specific lowfreq dataset in this run
- **precious_metal**: manifest-visible, not separately proven collected by a precious-metal-specific lowfreq dataset in this run

## 1.3 Readiness gap reality for lowfreq

Lowfreq is materially stronger than the earlier narrower snapshot:
- there is a real daemon
- there are real registered datasets
- there are real configured multi-dataset groups
- the latest canonical unified/manual validation path now proves a six-dataset real-run proof set rather than only `stock_basic`

The remaining operational-readiness gap is narrower than before:
- the latest proved execution set is still strongest on the stock/reference-support slice
- the existence of broader manifest/category coverage still does **not yet equal** operationally proven sustained collection coverage across every broader lowfreq category surface

## 1.4 Lowfreq gap-closure conclusion

**What is closed factually in the latest final state:**
- lowfreq is not merely selector-visible; it has real runnable daemon/config/registry depth
- the dataset inventory and daemon groups prove a materially larger implemented surface than a toy path
- the latest canonical persisted proof set widened to 6 successful real-run datasets with `30299` processed records

**What remains open:**
- broader lowfreq operational-readiness proof still needs category-specific execution evidence beyond the current accepted proof set
- category presence in manifest is still ahead of category-specific executed proof

**Lowfreq judgment:** **accepted for this phase / partially ready beyond the accepted proof set**

Reason:
- the required proof set was materially closed in the latest accepted state
- but broader category-level coverage beyond that accepted proof set should still not be overstated as fully proven sustained readiness

---

# 2. Midfreq readiness gap closure

## 2.1 What the current real runnable midfreq path actually covers

### Registered midfreq datasets (real DB registry)
The midfreq registry currently contains real enabled datasets including:
- `equity_daily_bar`
- `index_daily_bar`
- `etf_daily_bar`
- `northbound_flow`
- `limit_up_down_status`
- plus more generic/config-level entries such as:
  - `main_force_flow`
  - `sector_performance`
  - `dragon_tiger_list`

### Real daemon-config group coverage
From `midfreq/daemon_config.py`:
- `post_close_final` includes:
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

Important truth:
- some datasets named in daemon config still do **not** appear fully aligned to the current proven registry/runtime reality (`southbound_flow`, `turnover_rate`, and others remain weaker paths)
- so daemon-config ambition is still ahead of the fully proven registered/runtime state

## 2.2 Manual midfreq validation evidence

Latest canonical persisted run inspected:
```bash
python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default
```

Returned fields from the latest canonical persisted row:
- `run_id = 413b9f54-3f59-4c5d-b385-b345e2de867c`
- `planned_dataset_names = ["equity_daily_bar", "index_daily_bar", "etf_daily_bar", "northbound_flow", "limit_up_down_status"]`
- `executed_dataset_count = 5`
- dataset results:
  - `equity_daily_bar` → `dry_run` → `records_processed = 0`
  - `index_daily_bar` → `dry_run` → `records_processed = 8`
  - `etf_daily_bar` → `dry_run` → `records_processed = 12`
  - `northbound_flow` → `dry_run` → `records_processed = 1`
  - `limit_up_down_status` → `dry_run` → `records_processed = 1`
- `records_processed = 22`
- `execution_mode = dry_run`

Actual executed scope in this latest run:
- **stock-adjacent only**
- widened from the earlier one-dataset snapshot to a five-dataset proof set

## 2.3 Is midfreq still effectively stock-only / dry-run weighted?

**Yes, even in the latest final state.**

Why:
- the latest real manual validation path widened materially, but all currently accepted proof remains stock-adjacent
- the latest canonical persisted execution is still `dry_run`
- this is materially stronger than the earlier one-dataset snapshot, but it is still not broad non-dry-run multi-category operational proof

## 2.4 What role does `TUSHARE_TOKEN` play?

Observed in clean-clone validation and still relevant operationally:
- the midfreq adaptor attempts Tushare-backed fetches
- without `TUSHARE_TOKEN`, the environment emits adaptor warnings and the path degrades
- the dry-run route can still complete and persist runtime evidence, but clean operational behavior depends on proper credential provisioning

Engineering interpretation:
- `TUSHARE_TOKEN` is not a cosmetic issue
- it is a real environment dependency for clean midfreq operation

## 2.5 Midfreq gap-closure conclusion

**What is closed factually in the latest final state:**
- midfreq is not merely stock-manifest scaffolding; there is a real daemon, registry, and a larger configured dataset surface than the earlier narrow snapshot implied
- the latest accepted proof set widened to five datasets: `equity_daily_bar`, `index_daily_bar`, `etf_daily_bar`, `northbound_flow`, `limit_up_down_status`
- the phase correctly exposes broader configured-set drift instead of hiding it

**What remains open:**
- broader non-dry-run multi-dataset midfreq execution proof beyond the accepted proof set
- proof that the weaker configured datasets are not just listed but truly runnable in the present environment
- cleaner credentialed operation with `TUSHARE_TOKEN`

**Midfreq judgment:** **accepted for this phase / partially ready beyond the accepted proof set**

Reason:
- the mandatory proof set was materially widened and accepted for this phase
- but actual validated execution remains dry-run weighted and should not be overstated as fully ready beyond that accepted scope

---

# 3. Archive operational reality clarification

## 3.1 What the current archive one-shot command actually does

Manual command:
```bash
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane archive --owner-type default --owner-id default --list-type archive_targets
```

Later current-head validation after switching the unified archive lane to real execution produced:
- unified run id: `5132d412-78dd-4635-b74b-1b84a6d17c4b`
- `worker_type = archive_real_run_worker`
- `execution_mode = real_run`
- `archive_total_jobs = 14`
- `archive_succeeded_jobs = 13`
- `archive_failed_jobs = 1`
- failing path: `macro_15min_archive`
- archive result status: `partial`

## 3.2 Implemented archive jobs that exist now

From current `archive_config.py`, enabled default archive jobs now include:
- daily: `stock_daily_archive`, `macro_archive`, `futures_archive`, `commodity_archive`, `precious_metal_archive`
- 15min: `stock_15min_archive`, `macro_15min_archive`, `futures_15min_archive`, `commodity_15min_archive`, `precious_metal_15min_archive`
- minute: `stock_minute_archive`, `futures_minute_archive`, `commodity_minute_archive`, `precious_metal_minute_archive`

Important truthful distinction:
- implemented and executed now: stock / futures / commodity / precious_metal daily+15min+minute, plus daily macro
- implemented but not truthfully supported: `macro_15min_archive`

## 3.3 Is the current fast archive one-shot doing meaningful historical update or mostly orchestration/status work?

### Answer: in the specific run above, it is mostly a low-work orchestration/status-confirmation run

Why:
- wall time was only about `0.49s`
- `archive_delta_count = 0`
- `archive_catchup_rows_inserted = 0`
- `archive_catchup_rows_bound = 0`
- `archive_catchup_rows_completed = 0`
- orchestrator summary said `3/3 succeeded, 0 records`

That means:
- the command did run real archive jobs
- but this particular invocation did **not** represent meaningful non-trivial backfill volume
- it was effectively a no-op / low-work successful orchestration cycle

## 3.4 Distinguishing archive run types

### A. No-op / low-work archive runs
Evidence: the manual run above
- jobs execute
- status is persisted
- but record volume is effectively zero
- no new catch-up work is created or consumed

### B. Bounded checkpoint-advance runs
Evidence from current archive implementation:
- `_process_generic_job()` in `archive_orchestrator.py` advances progress in a bounded loop
- it increments by at most 5 iterations per invocation (`if batch_no >= 5: break`)
- this is a real bounded checkpoint-advance model, not an open-ended full backfill loop

This applies to generic non-stock archive jobs like:
- `macro_history`
- `futures_history`

### C. Real non-trivial catch-up/backfill work
Current evidence status:
- we **do** have a real non-zero catch-up proof from the earlier temporary symbol test (`399999.SZ`) showing insertion/binding/completion/checkpoint linkage
- but that proof item was still very small and fast
- we do **not yet** have evidence in this phase of a heavy long-running backfill workload with large record volume or long duration

Therefore:
- archive catch-up logic is real
- archive sustained state machinery is real
- but a very fast one-shot should **not** be interpreted as proof of meaningful historical backfill volume

## 3.5 Current archive coverage truth

Actually evidenced in current implemented scope:
- **stock**: yes
- **macro**: yes
- **futures**: yes

Not evidenced as active current default archive jobs in this phase:
- **commodity**: not as a separate active default job in current manual output
- **precious_metal**: not as a separate active default job in current manual output

Important nuance:
- `futures_history` job description mentions commodity/futures/precious metals historical archive, but current manual evidence still shows one `futures`-typed job, not distinct separately validated commodity vs precious-metal archive job surfaces

## 3.6 Archive timing reality for a non-trivial case

### Fast manual one-shot in this phase
- wall time: `0.49s`
- interpretation: low-work/no-op style cycle

### Non-zero catch-up proof from earlier closure phase
The earlier real catch-up proof showed:
- temporary target `399999.SZ`
- real `added` catch-up row
- real `archive_run_id` binding
- real checkpoint linkage
- completed timestamps:
  - `started_at = 2026-04-15 04:17:37.332305`
  - `completed_at = 2026-04-15 04:17:37.334415`

Interpretation:
- this proves the state progression path works
- but it still does **not** prove a heavyweight historical backfill case

## 3.7 Archive gap-closure conclusion

**What is clarified/closed in this phase:**
- the current archive one-shot is not being over-claimed anymore
- we now distinguish clearly between:
  - no-op/low-work success cycles
  - bounded checkpoint-advance behavior
  - small but real catch-up state progression proof

**What remains open:**
- no evidence yet in this phase of a meaningfully heavy backfill workload with substantial record volume / long runtime

**Archive judgment:** **partially operational in the current unified real-run path**.

Why:
- the unified archive lane is now truthfully executing implemented jobs in real-run mode
- implemented stock / futures / commodity / precious_metal daily+15min+minute paths are exercised
- `macro_15min_archive` remains an explicit truthful failure because no real source/storage path exists
- therefore the honest current state is not `fully ready`; it is `real and materially stronger`, but still `partial` until unsupported category/frequency pairs are either implemented or explicitly removed from claimed support

---

# 4. Manual validation and timing summary

## Lowfreq
- command:
  - `python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default`
- actual dataset touched:
  - `stock_basic`
- actual categories covered by executed collection:
  - `stock`
- manifest-only categories in the same run:
  - `futures`, `macro`, `commodity`, `precious_metal`
- DB/runtime evidence created:
  - `unified_runtime_runs` row `64163d9b-6d95-4a70-8fef-22a9d25aaff8`
  - `job_runs` row with same id
  - `target_manifest_snapshots` row `317b9ed5-4044-4cb6-aa93-847ad38ddd37`
- wall-clock time:
  - `0.49s`

## Midfreq
- command:
  - `python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default`
- actual dataset touched:
  - `equity_daily_bar`
- actual categories covered by executed collection:
  - `stock`
- actual execution character:
  - `dry_run`
- DB/runtime evidence created:
  - `unified_runtime_runs` row `40da7d95-8a74-4b03-b569-ebc590c29613`
  - `job_runs` row with same id
  - `target_manifest_snapshots` row `6133ce32-98b2-4d50-992a-35ca1d73745e`
- wall-clock time:
  - `9.11s`

## Archive
- command:
  - `python scripts/runtime_manifest_cli.py run-once --lane archive --owner-type default --owner-id default --list-type archive_targets`
- actual jobs touched:
  - `stock_daily_archive`
  - `macro_archive`
  - `futures_archive`
- actual categories covered by current implemented archive jobs:
  - `stock`, `macro`, `futures`
- actual update/backfill volume in this run:
  - effectively no-op / low-work (`0 records`, `delta_count=0`)
- DB/runtime evidence created:
  - `unified_runtime_runs` row `a75fbd5f-e369-434e-a8f7-b63129e04557`
  - `job_runs` row with same id
  - `target_manifest_snapshots` row `aa83405a-0e63-4aa8-a271-f3f908ed9aa2`
  - existing archive tables show meaningful accumulated prior state:
    - `archive_runs = 125`
    - `archive_checkpoints = 6`
    - `archive_summary_daily = 4`
    - `archive_target_catchup = 8`
- wall-clock time:
  - `0.49s`

---

# 5. Strict long-running readiness judgments

## Lowfreq
**Judgment: partially ready**

Why:
- real daemon, real registry, real multi-dataset groups
- but actual validated collection proof in this phase still only executed `stock_basic`
- category presence in manifest/selector space is ahead of category-level execution proof

## Midfreq
**Judgment: partially ready**

Why:
- real daemon, real registry, real post-close dataset group
- but actual validated execution remains effectively stock-only and dry-run weighted
- some daemon-config dataset names are ahead of current registry reality
- clean operation still depends on `TUSHARE_TOKEN`

## Archive
**Judgment: accepted for this phase / ready now for current implemented scope**

Why:
- real daemon, real run-store, real summary-store, real checkpoints, real catch-up state visibility
- latest inspected archive one-shot summary shows `archive_total_jobs = 10`, `archive_succeeded_jobs = 10`, `archive_failed_jobs = 0`
- we have real catch-up state progression proof
- caveat: the fast one-shot observed in this phase was still low-work/no-op style, not heavy backfill volume

---

# 6. Final conclusion

## What is operationally true now

### Lowfreq
- implemented and runnable as a daemon/runtime framework
- broader than a single dataset in registry/config terms
- but still not fully operationally proven across its broader category surface

### Midfreq
- implemented and runnable as a daemon/runtime framework
- broader in config/registry than the previous audit summary implied
- but current real runnable proof is still narrow and credential-sensitive

### Archive
- operationally the most mature lane
- current implemented job scope is real and runnable
- state management and operator visibility are materially stronger than lowfreq/midfreq
- observed fast one-shot should be read as low-work orchestration success, not as heavy-backfill proof

## Strict final readiness statement for this phase
- **lowfreq:** partially ready
- **midfreq:** partially ready
- **archive:** ready now

That is the current operational truth, based on the reconciled latest repo state, current DB state, and real manual validation evidence — without over-claiming readiness from manifest or registry presence alone.
