# Collection Layer Operational Readiness Gap Closure Audit

_Date: 2026-04-15_

## Final accepted phase judgments (Milestones A-C)

### Archive (Milestone A)
**Accepted for this phase** at the strongest truthful level achieved.

Closed in this phase:
- daily archive runtime coverage across required categories
- 15min archive runtime coverage across required categories
- real `archive_runs` evidence for all five required 15min combinations
- one real 15min ingest/storage/checkpoint closure path for `15min + stock`

Explicit residuals retained for future work:
- `15min + commodity` — runtime-covered only; blocker mix includes source limitation, schema/storage limitation, and implementation limitation
- `15min + futures` — runtime-covered only; blocker mix includes source limitation, schema/storage limitation, and implementation limitation
- `15min + precious_metal` — runtime-covered only; blocker mix includes source limitation, schema/storage limitation, and implementation limitation
- `15min + macro` — runtime-covered only; blocker is fundamentally source limitation under current source set, plus missing dedicated storage/archiver path

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
The manual unified lowfreq run produced manifest categories:
- `stock`
- `futures`
- `macro`
- `commodity`
- `precious_metal`

### Actual manual collection execution evidence in this phase
Manual command:
```bash
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default
```

Returned fields:
- `run_id = 64163d9b-6d95-4a70-8fef-22a9d25aaff8`
- `planned_dataset_names = ["stock_basic"]`
- `executed_dataset_count = 1`
- dataset result:
  - `dataset_name = stock_basic`
  - `status = succeeded`

### Actual lowfreq collection coverage proven by this run
- **stock**: yes, proven by executed dataset `stock_basic`

### Categories present in manifest logic but NOT proven collected by this manual runnable path
- **futures**: manifest-visible, not proven collected in this run
- **macro**: manifest-visible, not proven collected in this run
- **commodity**: manifest-visible, not proven collected in this run
- **precious_metal**: manifest-visible, not proven collected in this run

## 1.3 Readiness gap reality for lowfreq

Lowfreq is stronger than the previous audit made it sound in one dimension:
- there is a real daemon
- there are real registered datasets
- there are real configured multi-dataset groups

But the most important operational readiness gap remains:
- the currently exercised unified/manual validation path still proves only **very narrow actual collection coverage** (`stock_basic`)
- the existence of many registered/configured datasets does **not yet equal** operationally proven sustained collection coverage across the broader lowfreq category space

## 1.4 Lowfreq gap-closure conclusion

**What is closed factually in this phase:**
- lowfreq is not merely selector-visible; it has real runnable daemon/config/registry depth
- the dataset inventory and daemon groups prove a materially larger implemented surface than a one-dataset toy path

**What remains open:**
- broader lowfreq operational-readiness proof still needs actual execution evidence across more than `stock_basic`
- category presence in manifest is still ahead of category-level executed proof

**Lowfreq judgment:** **partially ready**

Reason:
- real daemon and many real datasets/groups exist
- but actual manually proven collection coverage is still too narrow to honestly call the lane fully ready now

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
- some datasets named in daemon config do **not** appear in the current registry dump from this environment (`margin_financing`, `southbound_flow`, `turnover_rate`, `limit_up_detail`)
- so daemon-config ambition is ahead of the registered dataset reality

## 2.2 Manual midfreq validation evidence

Command:
```bash
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default
```

Returned fields:
- `run_id = 40da7d95-8a74-4b03-b569-ebc590c29613`
- `planned_dataset_names = ["equity_daily_bar"]`
- `executed_dataset_count = 1`
- dataset result:
  - `dataset_name = equity_daily_bar`
  - `status = dry_run`
  - `watermark = 20260414`

Actual executed scope in this run:
- **stock only**
- specifically one stock dataset path: `equity_daily_bar`

## 2.3 Is midfreq still effectively stock-only / dry-run weighted?

**Yes, based on current runnable evidence.**

Why:
- the real manual validation path executed only `equity_daily_bar`
- that is a stock dataset
- the returned dataset result was `dry_run`
- this is better than “not runnable”, but it is not yet broad multi-category operational proof

## 2.4 What role does `TUSHARE_TOKEN` play?

Observed earlier in clean-clone validation and still relevant operationally:
- the midfreq adaptor attempts Tushare-backed fetches
- without `TUSHARE_TOKEN`, the environment emits adaptor warnings and the path degrades
- the dry-run route can still complete and persist runtime evidence, but clean operational behavior depends on proper credential provisioning

Engineering interpretation:
- `TUSHARE_TOKEN` is not a cosmetic issue
- it is a real environment dependency for clean midfreq operation

## 2.5 Midfreq gap-closure conclusion

**What is closed factually in this phase:**
- midfreq is not merely stock-manifest scaffolding; there is a real daemon, registry, and a larger configured dataset surface than the prior summary implied
- however, the current operationally proven runnable path remains narrow

**What remains open:**
- actual multi-dataset midfreq execution proof beyond `equity_daily_bar`
- proof that registered/configured non-stock-adjacent datasets are not just listed but truly runnable in current environment
- cleaner credentialed operation with `TUSHARE_TOKEN`

**Midfreq judgment:** **partially ready**

Reason:
- real daemon/framework/registry exist
- actual validated execution remains stock-only and dry-run weighted
- environment cleanliness depends on Tushare credentialing

---

# 3. Archive operational reality clarification

## 3.1 What the current archive one-shot command actually does

Manual command:
```bash
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane archive --owner-type default --owner-id default --list-type archive_targets
```

Returned fields:
- `run_id = a75fbd5f-e369-434e-a8f7-b63129e04557`
- `window_name = manual_archive`
- `archive_total_jobs = 3`
- `archive_succeeded_jobs = 3`
- `archive_failed_jobs = 0`
- `archive_delta_count = 0`
- `archive_catchup_rows_inserted = 0`
- `archive_catchup_rows_bound = 0`
- `archive_catchup_rows_completed = 0`

## 3.2 Implemented archive jobs that exist now

From `archive_config.py`, current enabled default jobs are exactly:
- `stock_daily_archive` → `stock_daily` → asset `stock`
- `macro_archive` → `macro_history` → asset `macro`
- `futures_archive` → `futures_history` → asset `futures`

This is the current real implemented default archive scope.

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

**Archive judgment:** **ready now** for current implemented operational scope, **with the explicit caveat** that the observed fast one-shot was low-work and should not be misread as proof of heavy backfill throughput

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
**Judgment: ready now** for current implemented scope

Why:
- real daemon, real run-store, real summary-store, real checkpoints, real catch-up state visibility
- current implemented default job scope is clear and runnable: stock/macro/futures
- we have real catch-up state progression proof
- caveat: the fast one-shot observed in this phase was low-work/no-op style, not heavy backfill volume

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

That is the current operational truth, based on current code, current DB state, and real manual validation evidence — without over-claiming readiness from manifest or registry presence alone.
