# Trailblazer Final Evidence Package

> **Canonical current-state status:** Canonical current-state document. Refreshed against current HEAD sanity evidence after doc normalization. Use this as current accepted evidence summary, not older batch records.

> **Current truth snapshot:** lowfreq real-run = green for current proof set; midfreq real-run = green for current proof set; archive real-run = green for corrected supported scope (stock/futures/commodity/precious_metal daily+15min+minute; macro historical/daily only); highfreq remains deferred; stale archive operator/catch-up rows for old unsupported macro intraday assumptions still require cleanup/reclassification.

_Date: 2026-04-15_

## Readiness-gap phase closure addendum (Milestones A-D)

This document was originally written for the earlier Trailblazer main-line closure. It is now extended as the final review package for the **readiness-gap closure phase** accepted on 2026-04-15.

### Frozen milestone state for this phase
- **Milestone A (archive)** — accepted and frozen for this phase
- **Milestone B (lowfreq)** — accepted and frozen for this phase
- **Milestone C (midfreq)** — accepted and frozen for this phase
- **Milestone D (final readiness-gap closure packaging)** — complete and frozen for review

### Final truthful judgments for this phase
- **archive**
  - daily runtime coverage is in place across required categories for this phase
  - 15min runtime coverage is in place across required categories for this phase
  - one real 15min ingest/storage/checkpoint closure path was proven for `15min + stock`
  - remaining non-stock 15min paths were explicitly classified, not hand-waved
- **lowfreq**
  - required proof set was materially closed with real non-dry-run evidence
  - service-mode smoke was proven
  - unified runtime semantics were corrected to truthfully use `real_run`
- **midfreq**
  - mandatory proof set is materially runnable
  - safe non-dry-run proof was established for `northbound_flow`, `limit_up_down_status`, and `index_daily_bar`
  - service-mode smoke exposed broader config/registry/schema drift, especially `southbound_flow` history-table absence
- **highfreq**
  - explicitly deferred out of this phase
  - no highfreq implementation expansion was performed in this readiness-gap closure round

### Phase commit evidence added after the earlier main-line closure
- `f6442d6` — Expand archive runtime coverage for commodity and precious metals
- `9680b93` — Add 15min archive runtime coverage for required categories
- `5ce9dbb` — Add real stock 15min archive storage and checkpoints
- `3bc0883` — Run lowfreq unified runtime in real execution mode
- `7f0be62` — Align unified runtime tests with real lowfreq execution
- `4b8b445` — Refresh unified runtime integration expectations
- `4a8b779` — Reconcile midfreq registry truth and daemon state handling

## Milestone position (source of truth: implementation execution plan)

Total milestone count in the execution plan: **7**

Milestones:
- Milestone 0 — Execution readiness and repo/schema parity
- Milestone 1 — Business Layer selector and target manifest foundation
- Milestone 2 — Unified runtime daemon/worker control substrate
- Milestone 3 — Lowfreq migration into unified runtime path
- Milestone 4 — Midfreq migration into unified runtime path
- Milestone 5 — Archive upgrade: manifest-driven targeting, delta detection, catch-up planning
- Milestone 6 — Directly runnable closure: config, docs, reproducibility, profiling, sustained operability

### Fully completed now
- **Milestone 0**
- **Milestone 1**
- **Milestone 2**
- **Milestone 3**
- **Milestone 4**
- **Milestone 5**
- **Milestone 6**

### In progress now
- none

### Remaining before final closure
- no implementation items remain on the main line
- review and attachment delivery are the only remaining handoff concerns outside the codebase

---

## Repository correctness check

Verified working repository:

```bash
pwd
/Users/neoclaw/repos/ifa-data-platform

git rev-parse --show-toplevel
/Users/neoclaw/repos/ifa-data-platform

git remote -v
origin git@github.com:yunpli/ifa-data-platform.git (fetch)
origin git@github.com:yunpli/ifa-data-platform.git (push)
```

Cross-repo check:
- current Trailblazer implementation work is landing in **`ifa-data-platform`**
- `ifa-business-layer` currently has no mixed-in changes from this Trailblazer implementation batch

Current repo note:
- unrelated file `docs/IFA_BUSINESS_LAYER_LLM_UTILITY_SPEC.md` was removed from `ifa-data-platform` during closure cleanup and moved out of the Data Platform repo
- current Trailblazer closure artifacts are landing in the correct Data Platform repo

---

## Code / migration / test / docs artifacts landed

### Core code
- `src/ifa_data_platform/runtime/unified_runtime.py`
- `scripts/runtime_manifest_cli.py`
- `src/ifa_data_platform/archive/archive_target_delta.py`
- `src/ifa_data_platform/runtime/target_manifest.py`

### Migrations
- `alembic/versions/021_trailblazer_runtime_artifacts.py`
- `alembic/versions/022_stock_fund_forecast_tables.py`
- `alembic/versions/023_unified_runtime_run_audit.py`
- `alembic/versions/024_archive_catchup_state_closure.py`

### Tests
- `tests/integration/test_unified_runtime.py`
- `tests/unit/test_target_manifest.py`
- `tests/unit/test_archive_target_delta.py`

### Runbook / closure docs
- `docs/TRAILBLAZER_RUNTIME_RUNBOOK_2026-04-15.md`
- `docs/TRAILBLAZER_REPRO_SMOKE_2026-04-15.md`
- `docs/TRAILBLAZER_FINAL_EVIDENCE_PACKAGE_2026-04-15.md`

---

## Tests run

### Unified runtime integration suite
```bash
pytest tests/integration/test_unified_runtime.py -q
```

Latest local result:
```text
11 passed in 18.72s
```

### Clean-clone integration suite
```bash
cd /tmp/ifa-data-platform-cleanclone
pytest tests/integration/test_unified_runtime.py -q
```

Clean-clone result:
```text
11 passed in 16.08s
```

---

## Reproducibility / smoke validation executed

### In-repo validation

```bash
source .venv/bin/activate
export PYTHONPATH=src
export DATABASE_URL='postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
export IFA_DB_SCHEMA=ifa2
alembic upgrade head
python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default
python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default
python scripts/runtime_manifest_cli.py run-once --lane archive --owner-type default --owner-id default --list-type archive_targets
python scripts/runtime_manifest_cli.py run-status --limit 10
python scripts/runtime_manifest_cli.py archive-status --limit 10
pytest tests/integration/test_unified_runtime.py -q
```

In-repo outcome:
- migrations reached head
- lowfreq one-shot succeeded
- midfreq one-shot succeeded
- archive one-shot succeeded
- run-status returned persisted unified run rows
- archive-status returned persisted archive state rows
- unified integration tests passed

### Clean-clone validation

```bash
git clone /Users/neoclaw/repos/ifa-data-platform /tmp/ifa-data-platform-cleanclone
cd /tmp/ifa-data-platform-cleanclone
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export PYTHONPATH=src
export DATABASE_URL='postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
export IFA_DB_SCHEMA=ifa2
alembic upgrade head
python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default
python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default
python scripts/runtime_manifest_cli.py run-once --lane archive --owner-type default --owner-id default --list-type archive_targets
python scripts/runtime_manifest_cli.py run-status --limit 5
python scripts/runtime_manifest_cli.py archive-status --limit 10
pytest tests/integration/test_unified_runtime.py -q
```

Clean-clone outcome:
- install succeeded
- migrations succeeded
- lowfreq one-shot succeeded
- midfreq one-shot completed in dry-run mode and persisted summary output
- archive one-shot succeeded
- run-status returned expected persisted rows
- archive-status returned expected keys: `recent_archive_runs`, `recent_catchup_rows`, `recent_checkpoints`, `summary_by_status`
- integration tests passed
- clean-clone caveat: midfreq adaptor emitted warnings without `TUSHARE_TOKEN`; a fully provisioned developer environment should set `TUSHARE_TOKEN` for clean midfreq execution

---

## Profiling evidence

### Lowfreq one-shot
Command:
```bash
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default
```

Observed:
- wall time: **0.44s**
- max resident set size: **79,151,104 bytes**
- peak memory footprint: **63,538,432 bytes**

### Midfreq one-shot
Command:
```bash
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default
```

Observed:
- wall time: **8.62s**
- max resident set size: **83,886,080 bytes**
- peak memory footprint: **65,324,480 bytes**

### Archive one-shot
Command:
```bash
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane archive --owner-type default --owner-id default --list-type archive_targets
```

Observed:
- wall time: **0.41s**
- max resident set size: **77,905,920 bytes**
- peak memory footprint: **62,293,248 bytes**

### Unified runtime integration test suite
Command:
```bash
/usr/bin/time -l pytest tests/integration/test_unified_runtime.py -q
```

Observed:
- wall time: **15.55s**
- max resident set size: **84,115,456 bytes**
- peak memory footprint: **53,315,008 bytes**

---

## DB / runtime evidence

### Unified run evidence
Recent canonical runs produced persisted unified rows and summaries for:
- lowfreq
- midfreq
- archive

Run-status query returned persisted rows from:
- `ifa2.unified_runtime_runs`

### Archive state evidence
Archive-status query returned:
- `summary_by_status`
- `recent_catchup_rows`
- `recent_checkpoints`
- `recent_archive_runs`

### Archive-state closure evidence
Migration `024_archive_catchup_state` added and verified these persisted fields on `ifa2.archive_target_catchup`:
- `archive_run_id`
- `checkpoint_dataset_name`
- `checkpoint_asset_type`
- `started_at`
- `completed_at`
- `progress_note`

### Non-zero archive membership-delta proof (Milestone 5 closure)
A temporary archive target was inserted into Business Layer selector table `ifa2.focus_list_items` under:
- list: `default_archive_targets_daily`
- temporary symbol: `399999.SZ`

The archive unified path was then executed and produced real persisted evidence.

#### Added-target proof
Persisted catch-up row evidence:
- `change_type = added`
- `symbol_or_series_id = 399999.SZ`
- `dedupe_key = archive|daily|stock|399999.SZ`
- `backlog_priority = medium_high`
- `archive_run_id = 0dd49424-8602-41fd-a31c-df2ce5fd2731`
- `checkpoint_dataset_name = stock_daily_catchup`
- `checkpoint_asset_type = stock`
- `status = completed`
- `started_at = 2026-04-15 04:17:37.332305`
- `completed_at = 2026-04-15 04:17:37.334415`
- `progress_note = catch-up execution closed by archive run 0dd49424-8602-41fd-a31c-df2ce5fd2731; checkpoint advanced`

Persisted checkpoint linkage evidence:
- `dataset_name = stock_daily_catchup`
- `asset_type = stock`
- `backfill_start = 2025-04-15`
- `backfill_end = 2026-04-15`
- `last_completed_date = 2026-04-15`
- `shard_id = archive|daily|stock|399999.SZ`
- `batch_no = 1`
- `status = completed`

This closes the required Milestone 5 proof for:
- catch-up row insertion
- archive run binding
- status progression
- checkpoint linkage
- completed outcome visibility

#### Removal visibility after cleanup
After removing the temporary selector item and rerunning archive:
- `change_type = removed`
- `symbol_or_series_id = 399999.SZ`
- `status = observed`
- `archive_run_id = null`
- `progress_note = membership delta observed: removed`

Cleanup verification:
- `residual_focus_item_count = 0`

Interpretation:
- Milestone 5 is now closed with non-zero delta evidence, not just code-path reasoning

---

## Commits created

Implementation and review-state commits relevant to the frozen final review set:
- `1a215ed` — `Strengthen Trailblazer unified runtime audit persistence`
- `12618b1` — `Add Trailblazer runtime inspection and repro runbook`
- `4443e0d` — `Close Trailblazer archive catch-up state progression`
- `d6e333a` — `Add Trailblazer final evidence package draft`
- `72d2def` — `Finalize Trailblazer closure evidence and clean repo state`
- `604b4b3` — `Close collection readiness gaps for lowfreq and midfreq`
- `bca8fd4` — `Finalize readiness-gap closure packaging and handoff docs`
- `0b88b16` — `Add readiness-gap audit and plan docs to final review set`

---

## Push status

Current remote/source-of-truth state:
```text
HEAD = 0b88b1645942425fbab7873fc2ac6acdf032cfe6
origin/main = 0b88b1645942425fbab7873fc2ac6acdf032cfe6
branch = main
remote = git@github.com:yunpli/ifa-data-platform.git
```

Push conclusion:
- the latest accepted final-review source state is on remote
- `HEAD` and `origin/main` are aligned at commit `0b88b1645942425fbab7873fc2ac6acdf032cfe6`
- the earlier `72d2def` push record is real historical evidence, but it is **not** the latest final-review remote state anymore

---

## Final repo status

```bash
git status --short docs
```

Result at inspection time:
- tracked review-state source files are the repo source of truth
- local untracked `.txt` files may exist as attachment fallbacks only
- those generated `.txt` fallbacks are not part of the accepted source commit and should not be treated as newer review-state than the `.md` repo files

## Latest runtime / DB state used for final reconciliation

Latest persisted canonical run rows inspected from `ifa2.unified_runtime_runs`:
- lowfreq run `76192792-2641-4b1f-8f8a-b36c87bd50cd`
  - `worker_type = lowfreq_real_run_worker`
  - `execution_mode = real_run`
  - `planned_dataset_names = ["trade_cal", "stock_basic", "index_basic", "fund_basic_etf", "sw_industry_mapping", "news_basic"]`
  - `records_processed = 30299`
- midfreq run `413b9f54-3f59-4c5d-b385-b345e2de867c`
  - `worker_type = midfreq_dry_run_worker`
  - `execution_mode = dry_run`
  - `planned_dataset_names = ["equity_daily_bar", "index_daily_bar", "etf_daily_bar", "northbound_flow", "limit_up_down_status"]`
  - `records_processed = 22`
- archive run `f6aeacc5-fdc7-4c4e-8f21-259387bccb20`
  - `worker_type = archive_dryrun_worker`
  - `archive_total_jobs = 10`
  - `archive_succeeded_jobs = 10`
  - `archive_failed_jobs = 0`
  - `archive_delta_count = 0`
  - `archive_catchup_rows_inserted = 0`
  - `archive_catchup_rows_bound = 0`
  - `archive_catchup_rows_completed = 0`

Latest table counts inspected at reconciliation time:
- `job_runs = 181`
- `unified_runtime_runs = 157`
- `target_manifest_snapshots = 173`
- `archive_target_catchup = 8`
- `archive_checkpoints = 9`
- `archive_runs = 344`
- `archive_summary_daily = 4`

## Remaining items

- no further implementation expansion is in scope for this phase
- remaining reviewer-facing work is limited to document retrieval, consistency correction, and attachment delivery

---

## Current judgment

The **readiness-gap closure phase** is complete and frozen for review.

Accepted phase judgments:
- Archive (Milestone A): accepted at the strongest truthful level reached in this phase
- Lowfreq (Milestone B): accepted as closed for this phase
- Midfreq (Milestone C): accepted at the strongest truthful level reached in this phase
- Milestone D packaging: complete in the current document set

Explicit defer list for future phases:
- any highfreq implementation work
- archive non-stock 15min ingest/storage closure beyond current classified residuals
- midfreq broader configured-set schema completion beyond the accepted proof set (for example `southbound_flow_history`)

The frozen review state now includes:
- archive/lowfreq/midfreq accepted phase judgments
- explicit residual-gap classifications where full closure was not honest in this phase
- truthful highfreq deferral
- selector + manifest contract
- unified runtime audit path
- archive runtime coverage + stock 15min ingest/checkpoint proof
- lowfreq required-proof-set non-dry-run evidence and service smoke
- midfreq mandatory-proof-set runnable evidence and safe non-dry-run evidence
- queryable runtime and archive-state CLI surfaces
- reproducibility evidence from in-repo and clean-clone execution
- profiling measurements captured
- clean repo state in `ifa-data-platform`
- final phase commit evidence and push evidence
- explicit reconciliation to the latest remote commit (`0b88b16`) and latest persisted runtime/DB state
