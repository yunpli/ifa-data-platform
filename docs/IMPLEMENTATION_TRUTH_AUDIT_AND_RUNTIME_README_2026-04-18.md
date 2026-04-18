# iFA Data Platform — Implementation Truth Audit & Runtime README (2026-04-18)

## 1. Purpose

This document is a fresh implementation-truth pass across the repository and live `ifa2` database.
It is **not** a summary of old docs.
It is based on:
- current code in `/Users/neoclaw/repos/ifa-data-platform`
- live DB truth in `ifa_db / ifa2`
- current runtime/operator paths actually present in the repo

The goal is to let another engineer answer, concretely:
- what each layer does
- what it pulls from source
- what it writes locally
- how it is run manually
- how the unified runtime/daemon runs it
- how status/evidence are recorded
- how Archive V2 fits into the system
- what is still ambiguous or mismatched

---

## 2. Executive summary

### Current system shape
The repository currently has five practical execution layers:
- **lowfreq** — slow/reference/fundamental/history ingestion
- **midfreq** — daily/close-ish market and business dataset ingestion
- **highfreq** — current-session intraday working truth + derived signal state
- **unified runtime / daemon** — official long-running scheduler/dispatcher/governance layer
- **Archive V2** — durable finalized archive layer with completeness + repair model

### Official runtime truth
The official long-running runtime entry is:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --loop
```

The lane-specific daemon wrappers remain, but their own `--loop` mode is explicitly demoted to compatibility/manual-wrapper status.

### Archive V2 production truth
**Code intent:** Archive V2 is the intended nightly production archive path.

**Live DB/runtime truth right now:** there is still an operational mismatch:
- code schedule policy says `archive_v2` should be the nightly production lane and legacy `archive` should be disabled/fallback-only
- live `ifa2.runtime_worker_schedules` still contains enabled rows for `archive`
- live `ifa2.runtime_worker_schedules` currently has **no `archive_v2` rows**
- live `ifa2.runtime_worker_state` has **no `archive_v2` worker state row**

So the truthful statement is:

> **Archive V2 is the intended nightly production path in code and dedicated production CLI, but the live unified-daemon schedule DB is still wired to legacy `archive`, not `archive_v2`.**

This is the single most important runtime/control mismatch currently present.

---

## 3. System overview

### Data lifecycle model
At a practical level, the repo currently implements this pipeline:

```text
source APIs / source truth
  -> lowfreq / midfreq / highfreq collection
  -> local retained truth or working truth tables
  -> unified runtime orchestration + evidence
  -> Archive V2 finalization into durable archive tables
  -> completeness / repair / operator inspection
```

### Semantic roles
- **lowfreq** stores durable retained history for slow/reference/business data families
- **midfreq** stores durable retained history for daily trading/business families
- **highfreq** stores intraday working truth and derived state, not long-term final archive by itself
- **Archive V2** turns retained/working truth into finalized archive facts with operator-grade status tracking

---

## 4. Layer responsibilities

## 4.1 Lowfreq

### Responsibility
Lowfreq is the slow/reference/fundamental/history ingestion layer.
It creates durable retained-history truth used later by reporting, runtime, and archive.

### Main code paths
- runner: `src/ifa_data_platform/lowfreq/runner.py`
- registry: `src/ifa_data_platform/lowfreq/registry.py`
- source adaptors: `src/ifa_data_platform/lowfreq/adaptors/`
- persistence/history writers: `src/ifa_data_platform/lowfreq/version_persistence.py`
- runtime wrapper: `src/ifa_data_platform/lowfreq/daemon.py`

### Source-side path
Lowfreq uses Tushare-backed adaptors.
Examples visible in code include source calls for datasets such as:
- `trade_cal`
- `stock_basic`
- `index_basic`
- `fund_basic`
- `anns_d`
- `news`
- `stock_company`
- `stk_managers`
- `new_share`
- `namechange`
- `top10_holders`
- `top10_floatholders`
- `pledge_stat`
- `stk_holdernumber`
- `margin`
- `moneyflow_hsgt`

### Local write model
Lowfreq writes three kinds of local state:

#### 1) dataset config
- `ifa2.lowfreq_datasets`
- live count observed: **69** datasets

#### 2) run/evidence state
- `ifa2.lowfreq_runs`
- `ifa2.lowfreq_raw_fetch`
- `ifa2.dataset_versions`

#### 3) retained history tables
Representative retained-history tables populated in DB:
- `ifa2.trade_cal_history` — **133,202** rows
- `ifa2.stock_basic_history` — **313,713** rows
- `ifa2.announcements_history` — **133,291** rows
- `ifa2.news_history` — **55,501** rows
- `ifa2.research_reports_history` — **810** rows
- `ifa2.investor_qa_history` — **9,528** rows
- `ifa2.company_basic_history` — materially populated

### What these written tables mean
- `*_history` tables are durable retained local truth, not temporary staging
- `dataset_versions` tracks candidate/promoted versions
- `lowfreq_raw_fetch` is raw fetch evidence for debugging/provenance
- `lowfreq_runs` is run-state history for individual dataset executions

### Manual run commands
Single dataset runner:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.lowfreq.runner --dataset <dataset_name>
```

Compatibility wrapper through unified daemon:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.lowfreq.daemon --once
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.lowfreq.daemon --health
```

Official manual worker execution via unified daemon:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker lowfreq
```

### Unified runtime behavior
Lowfreq is one official runtime lane handled by the unified daemon.
The wrapper module explicitly says lowfreq `--loop` is no longer the primary production model.

### Operator inspection
Key places to inspect lowfreq:
- `ifa2.lowfreq_datasets`
- `ifa2.lowfreq_runs`
- `ifa2.lowfreq_raw_fetch`
- `ifa2.dataset_versions`
- retained `*_history` tables
- unified layer status:
  - `ifa2.unified_runtime_runs`
  - `ifa2.runtime_worker_state`

---

## 4.2 Midfreq

### Responsibility
Midfreq owns the daily/close-ish market and business dataset ingestion layer.
It produces retained local truth for reporting and archive families.

### Main code paths
- runner: `src/ifa_data_platform/midfreq/runner.py`
- registry: `src/ifa_data_platform/midfreq/registry.py`
- source adaptors: `src/ifa_data_platform/midfreq/adaptors/`
- runtime wrapper: `src/ifa_data_platform/midfreq/daemon.py`

### Source-side path
Midfreq uses Tushare-backed midfreq adaptors.
Representative dataset families registered in code:
- `equity_daily_bar`
- `index_daily_bar`
- `etf_daily_bar`
- `northbound_flow`
- `limit_up_down_status`
- `margin_financing`
- `turnover_rate`
- `limit_up_detail`
- `southbound_flow`
- `main_force_flow`
- `sector_performance`
- `dragon_tiger_list`

### Local write model
#### 1) dataset config
- `ifa2.midfreq_datasets`
- live count observed: **12** datasets

#### 2) retained history / canonical truth
Representative populated tables:
- `ifa2.equity_daily_bar_history` — **420** rows
- `ifa2.index_daily_bar_history` — **247** rows
- `ifa2.etf_daily_bar_history` — **360** rows
- `ifa2.sector_performance_history` — **788** rows
- `ifa2.dragon_tiger_list_history` — **2,175** rows
- `ifa2.limit_up_detail_history` — **82,975** rows
- `ifa2.limit_up_down_status_history` — **16** rows

#### 3) summary / daemon state
DB tables present:
- `ifa2.midfreq_execution_summary`
- `ifa2.midfreq_daemon_state`
- `ifa2.midfreq_window_state`

### What these tables mean
- midfreq retained tables are durable local truth for later use, including Archive V2
- `midfreq_execution_summary` is a summary-level evidence surface, not a per-dataset full run ledger
- current schema is leaner than some docs may imply; it does **not** currently expose fields like `dataset_name` or full per-dataset status rows

### Manual run commands
Runner-level use:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.midfreq.runner
```

Compatibility/manual wrapper:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.midfreq.daemon --once
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.midfreq.daemon --health
```

Official manual worker execution via unified daemon:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker midfreq
```

### Unified runtime behavior
Midfreq is an official unified runtime lane.
The wrapper module explicitly says midfreq `--loop` is no longer the primary production model.

### Operator inspection
- `ifa2.midfreq_datasets`
- `ifa2.midfreq_execution_summary`
- retained history tables listed above
- `ifa2.unified_runtime_runs`
- `ifa2.runtime_worker_state`

---

## 4.3 Highfreq

### Responsibility
Highfreq owns the intraday working-truth layer and derived intraday signal/state layer.
It is **not** the durable final archive by itself.
It captures current-session or near-session data and materializes derived state for downstream usage.

### Main code paths
- runner: `src/ifa_data_platform/highfreq/runner.py`
- source adaptor: `src/ifa_data_platform/highfreq/adaptor_tushare.py`
- persistence: `src/ifa_data_platform/highfreq/persistence.py`
- derived signals: `src/ifa_data_platform/highfreq/derived_signals.py`
- runtime wrapper: `src/ifa_data_platform/highfreq/daemon.py`

### Source-side endpoints / paths seen in code
- `stk_mins`
- `stk_auction_o`
- `stk_auction_c`
- `major_news`
- `anns_d`
- `ths_daily`
- `fut_basic`
- `ft_mins`

### Local write model
#### Working truth tables
- `ifa2.highfreq_stock_1m_working` — **6** rows
- `ifa2.highfreq_index_1m_working` — **6** rows
- `ifa2.highfreq_proxy_1m_working` — **1** row
- `ifa2.highfreq_futures_minute_working` — **40** rows
- `ifa2.highfreq_open_auction_working` — **1** row
- `ifa2.highfreq_close_auction_working` — **1** row
- `ifa2.highfreq_event_stream_working` — **4,000** rows

#### Derived signal/state tables
- `ifa2.highfreq_limit_event_stream_working` — **10** rows
- `ifa2.highfreq_sector_breadth_working` — **10** rows
- `ifa2.highfreq_sector_heat_working` — **10** rows
- `ifa2.highfreq_leader_candidate_working` — **60** rows
- `ifa2.highfreq_intraday_signal_state_working` — **10** rows

#### Scope-management tables
- `ifa2.highfreq_active_scope`
- `ifa2.highfreq_dynamic_candidate`

#### Run/state tables
- `ifa2.highfreq_runs`
- `ifa2.highfreq_execution_summary`
- `ifa2.highfreq_daemon_state`
- `ifa2.highfreq_window_state`

### What these tables mean
- `*_working` tables are current working truth or current-state materialization
- they are input to Archive V2 finalization, not the final archive themselves
- highfreq derived tables represent transformed or summarized state, not raw source copies

### Manual run commands
Compatibility/manual wrapper:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.highfreq.daemon --once
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.highfreq.daemon --status
```

Official manual worker execution via unified daemon:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker highfreq
```

### Unified runtime behavior
Highfreq is an official unified runtime lane.
The wrapper explicitly says highfreq `--loop` is no longer the primary production model.

### Operator inspection
- `ifa2.highfreq_runs`
- `ifa2.highfreq_execution_summary`
- working truth tables
- derived state tables
- `ifa2.unified_runtime_runs`
- `ifa2.runtime_worker_state`

---

## 4.4 Unified runtime / unified daemon

### Responsibility
The unified runtime is the official scheduler/dispatcher/governance surface for the repo.
It centralizes:
- schedule policy
- trading-day / day-type handling
- per-worker execution
- run-state evidence
- worker heartbeat/state
- runtime budget / overlap / governance fields

### Main code paths
- runtime engine: `src/ifa_data_platform/runtime/unified_runtime.py`
- daemon: `src/ifa_data_platform/runtime/unified_daemon.py`
- schedule policy: `src/ifa_data_platform/runtime/schedule_policy.py`
- target manifest: `src/ifa_data_platform/runtime/target_manifest.py`
- manifest/ops CLI: `scripts/runtime_manifest_cli.py`

### Supported lanes in code
- `lowfreq`
- `midfreq`
- `highfreq`
- `archive`
- `archive_v2`

### Official long-running command

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --loop
```

### Manual commands
Status:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --status
```

Manual worker run:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker lowfreq
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker midfreq
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker highfreq
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker archive
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker archive_v2
```

Manifest utility:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py manifest
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane lowfreq
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane midfreq
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane highfreq
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane archive_v2
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-status --lane archive_v2
```

### Runtime control tables
#### Schedule + worker state
- `ifa2.runtime_worker_schedules`
- `ifa2.runtime_worker_state`

#### Unified run evidence
- `ifa2.job_runs`
- `ifa2.unified_runtime_runs`
- `ifa2.target_manifest_snapshots`

### What these tables mean
- `runtime_worker_schedules` = active schedule policy rows currently loaded into DB
- `runtime_worker_state` = last/active run state per worker
- `job_runs` = generic run ledger
- `unified_runtime_runs` = lane-aware, manifest-aware unified run ledger with summary JSON
- `target_manifest_snapshots` = persisted manifest snapshots used by the runtime

### Live DB truth observed
- `runtime_worker_schedules` exists and has schedule rows for:
  - `archive`
  - `highfreq`
  - `lowfreq`
  - `midfreq`
- `runtime_worker_state` has worker rows for:
  - `archive`
  - `highfreq`
  - `lowfreq`
  - `midfreq`
- **No `archive_v2` worker rows currently exist in either schedule or worker-state tables**
- `target_manifest_snapshots` exists and is populated
- `runtime_manifest_snapshots` does **not** exist; old docs/assumptions using that name are stale

### Important live mismatch
Code schedule policy in `runtime/schedule_policy.py` says:
- legacy `archive` should be disabled/fallback-only
- `archive_v2` should be the enabled nightly archive lane

But live `runtime_worker_schedules` currently shows the opposite operational truth:
- `archive` schedule rows are present and enabled
- `archive_v2` schedule rows are absent

This means the daemon-scheduled production path is not yet fully aligned with the current code intent.

---

## 4.5 Archive V2

### Responsibility
Archive V2 is the durable finalized archive/final-truth layer.
It is where retained history and working truth are transformed into archived daily/final or intraday archive facts, with completeness tracking and repair workflow.

### Main code paths
- schema/bootstrap: `src/ifa_data_platform/archive_v2/db.py`
- runner: `src/ifa_data_platform/archive_v2/runner.py`
- production profiles/logic: `src/ifa_data_platform/archive_v2/production.py`
- operator queries/state: `src/ifa_data_platform/archive_v2/operator.py`
- run CLI: `scripts/archive_v2_run.py`
- production CLI: `scripts/archive_v2_production_cli.py`
- operator CLI: `scripts/archive_v2_operator_cli.py`

### Core evidence / control tables
- `ifa2.ifa_archive_profiles` — profile registry/history
- `ifa2.ifa_archive_runs` — archive run ledger
- `ifa2.ifa_archive_run_items` — per-family per-date run evidence
- `ifa2.ifa_archive_completeness` — completeness state by family/frequency/date/scope
- `ifa2.ifa_archive_repair_queue` — operator backlog/repair queue

### Current live counts observed
- `ifa_archive_runs` — **127**
- `ifa_archive_run_items` — **1,357**
- `ifa_archive_completeness` — **111**
- `ifa_archive_repair_queue` — **47**
- `ifa_archive_profiles` — **21**

### Current archive tables populated
Representative populated destinations:
- `ifa_archive_index_daily`
- `ifa_archive_news_daily` — **5,599** rows
- `ifa_archive_sector_performance_daily` — **788** rows
- `ifa_archive_highfreq_event_stream_daily`
- `ifa_archive_highfreq_intraday_signal_state_daily`
- many intraday archive tables for supported families/frequencies

### Manual commands
Direct profile run:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_run.py --profile profiles/<profile>.json
```

Production nightly CLI:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_production_cli.py nightly --business-date YYYY-MM-DD
```

Manual backfill:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_production_cli.py backfill --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

Operator inspection:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py summary --days 14
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py recent-runs --limit 10
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py repair-backlog --limit 20
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py family-health --limit 30
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py date-health --days 14
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py repair-batch ...
```

### Relationship to the rest of the system
Archive V2 is not the collection layer itself.
It sits downstream of collection/runtime retained truth.
It reads retained history or working truth and writes operator-grade archive truth.

---

## 5. Source-to-local mapping guide

This section documents the important implemented mappings, not every tiny table.

## 5.1 Lowfreq mappings

### Reference / fundamental / filings style data
Typical flow:

```text
Tushare endpoint
  -> lowfreq adaptor fetch
  -> lowfreq_raw_fetch / dataset_versions
  -> retained *_history table
```

Representative mappings:
- `trade_cal` -> `trade_cal_history`
- `stock_basic` -> `stock_basic_history`
- `index_basic` -> `index_basic_history`
- ETF/fund reference endpoints -> `fund_basic_etf_history`
- `anns_d` -> `announcements_history`
- `news` -> `news_history`
- research report source path -> `research_reports_history`
- investor QA source path -> `investor_qa_history`
- company basic source path -> `company_basic_history`

Semantic shift:
- source API responses become versioned retained local truth
- this is more than raw copy; it is durable retained history tied to dataset versions

## 5.2 Midfreq mappings

Typical flow:

```text
Tushare daily / business endpoints
  -> midfreq adaptor fetch
  -> promoted retained history table
```

Representative mappings:
- equity daily bar endpoint -> `equity_daily_bar_history`
- index daily bar endpoint -> `index_daily_bar_history`
- ETF daily bar endpoint -> `etf_daily_bar_history`
- sector-performance endpoint -> `sector_performance_history`
- dragon-tiger endpoint -> `dragon_tiger_list_history`
- limit-up detail endpoint -> `limit_up_detail_history`
- limit-up/down status endpoint -> `limit_up_down_status_history`

Semantic shift:
- source data becomes retained daily/business local truth for downstream use

## 5.3 Highfreq mappings

### Direct intraday working truth
- `stk_mins` -> `highfreq_stock_1m_working`
- `stk_mins` (index path in current code) -> `highfreq_index_1m_working`
- `ths_daily` (proxy approximation path) -> `highfreq_proxy_1m_working`
- `ft_mins` + `fut_basic` -> `highfreq_futures_minute_working`
- `stk_auction_o` -> `highfreq_open_auction_working`
- `stk_auction_c` -> `highfreq_close_auction_working`
- `major_news` + `anns_d` -> `highfreq_event_stream_working`

Semantic shift:
- source intraday/current-session data is written into working truth tables, typically via versioned replace/insert

### Derived highfreq state
- `highfreq_event_stream_working` + related working inputs -> `highfreq_limit_event_stream_working`
- working truth + derived logic -> `highfreq_sector_breadth_working`
- working truth + derived logic -> `highfreq_sector_heat_working`
- working truth + derived logic -> `highfreq_leader_candidate_working`
- working truth + derived logic -> `highfreq_intraday_signal_state_working`

Semantic shift:
- raw/current-session inputs become summarized/derived intraday state

## 5.4 Archive V2 mappings

### Daily/final archive
- `index_daily_bar_history` -> `ifa_archive_index_daily`
- `announcements_history` -> `ifa_archive_announcements_daily`
- `news_history` -> `ifa_archive_news_daily`
- `research_reports_history` -> `ifa_archive_research_reports_daily`
- `investor_qa_history` -> `ifa_archive_investor_qa_daily`
- `dragon_tiger_list_history` -> `ifa_archive_dragon_tiger_daily`
- `limit_up_detail_history` -> `ifa_archive_limit_up_detail_daily`
- `limit_up_down_status_history` -> `ifa_archive_limit_up_down_status_daily`
- `sector_performance_history` -> `ifa_archive_sector_performance_daily`
- `highfreq_event_stream_working` -> `ifa_archive_highfreq_event_stream_daily`
- `highfreq_limit_event_stream_working` -> `ifa_archive_highfreq_limit_event_stream_daily`
- `highfreq_sector_breadth_working` -> `ifa_archive_highfreq_sector_breadth_daily`
- `highfreq_sector_heat_working` -> `ifa_archive_highfreq_sector_heat_daily`
- `highfreq_leader_candidate_working` -> `ifa_archive_highfreq_leader_candidate_daily`
- `highfreq_intraday_signal_state_working` -> `ifa_archive_highfreq_intraday_signal_state_daily`

Semantic shift:
- retained or working truth is transformed into durable finalized archive facts
- completeness state is recorded separately from the archive rows themselves

### Intraday archive
Representative supported patterns:
- direct retained intraday history -> archive intraday table
- 1m working truth -> direct 1m archive table
- 1m working truth -> rollup 15m/60m archive table

Examples:
- `highfreq_index_1m_working` -> `ifa_archive_index_1m`
- `highfreq_index_1m_working` -> rollup -> `ifa_archive_index_15m`
- `highfreq_index_1m_working` -> rollup -> `ifa_archive_index_60m`
- `highfreq_proxy_1m_working` -> `ifa_archive_proxy_1m`
- `highfreq_proxy_1m_working` -> rollup -> `ifa_archive_proxy_15m`
- `highfreq_proxy_1m_working` -> rollup -> `ifa_archive_proxy_60m`
- retained equity/futures/commodity/precious-metal intraday history -> matching `ifa_archive_*_{1m,15m,60m}` tables

Semantic shift:
- direct copy where retained truth already exists
- rollup where only truthful 1m retained truth exists

---

## 6. Local table meaning by layer

## 6.1 Collection layer retained truth
These are local retained truth tables, not archive tables:
- lowfreq `*_history`
- midfreq `*_history`
- highfreq `*_working`
- highfreq derived working/state tables

## 6.2 Working vs retained vs archive
- **working** = current session / replaceable operational state
- **history / retained** = durable local retained source-aligned truth
- **archive** = finalized operator-facing durable archive truth with completeness/repair model

This distinction matters. Archive V2 should not be confused with the collection write path itself.

---

## 7. Runtime and daemon model

## 7.1 Official production runtime path
Official long-running runtime path:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --loop
```

This is the repo’s official production-style process supervisor.

## 7.2 Demoted wrappers
These remain for compatibility/manual use:
- `ifa_data_platform.lowfreq.daemon`
- `ifa_data_platform.midfreq.daemon`
- `ifa_data_platform.highfreq.daemon`

They should not be treated as peer production loop processes anymore.

## 7.3 Schedule model
Code schedule policy distinguishes:
- `trading_day`
- `non_trading_weekday`
- `saturday`
- `sunday`

Schedule entries are stored in:
- `ifa2.runtime_worker_schedules`

Worker runtime state is stored in:
- `ifa2.runtime_worker_state`

Unified run evidence is stored in:
- `ifa2.unified_runtime_runs`
- `ifa2.job_runs`

Manifest snapshots are stored in:
- `ifa2.target_manifest_snapshots`

## 7.4 Current official production path vs live runtime DB
### For lowfreq/midfreq/highfreq
The live runtime DB is aligned enough to say these are in the unified-daemon model.
There are schedule rows and worker-state rows present.

### For archive / archive_v2
There is still a divergence:
- code intent -> `archive_v2` should be the nightly production lane
- live DB schedule rows -> legacy `archive` is still what the daemon is scheduled to run

So another engineer should not assume the daemon has already fully switched over just because the code supports `archive_v2`.

---

## 8. Operator inspection model

## 8.1 Unified runtime status
Status:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --status
```

Manifest/runtime status:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-status --lane lowfreq --limit 10
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-status --lane midfreq --limit 10
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-status --lane highfreq --limit 10
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-status --lane archive_v2 --limit 10
```

DB inspection tables:
- `ifa2.runtime_worker_schedules`
- `ifa2.runtime_worker_state`
- `ifa2.unified_runtime_runs`
- `ifa2.job_runs`
- `ifa2.target_manifest_snapshots`

## 8.2 Archive V2 status
Archive V2 operator CLI:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py recent-runs --limit 10
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py summary --days 14 --limit 10
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py gaps --days 14
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py repair-backlog --limit 20
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py family-health --limit 30
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py date-health --days 14
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py claimed-backlog --limit 20
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py suppressed-backlog --limit 20
```

DB inspection tables:
- `ifa2.ifa_archive_runs`
- `ifa2.ifa_archive_run_items`
- `ifa2.ifa_archive_completeness`
- `ifa2.ifa_archive_repair_queue`
- `ifa2.ifa_archive_profiles`

---

## 9. Archive V2 production model

## 9.1 How Archive V2 differs from collection/runtime retained truth
Collection/runtime layers write:
- retained history tables
- intraday working tables
- derived intraday state

Archive V2 writes:
- durable archive tables intended for finalized archived truth
- completeness rows
- repair backlog rows
- per-run per-family archive evidence

So Archive V2 is a **finalization layer**, not the source acquisition layer itself.

## 9.2 Intended nightly production path
In code, the intended nightly production path is:
- profile name: `archive_v2_production_nightly_daily_final`
- entrypoint: `scripts/archive_v2_production_cli.py nightly`
- unified-runtime lane support: `archive_v2`

`src/ifa_data_platform/archive_v2/production.py` clearly defines this as the steady-state nightly production path.

## 9.3 What remains manual/operator-triggered
Still operator/manual oriented today:
- manual backfill
- repair-batch operations
- some bounded manual Archive V2 runs
- resolving live schedule DB mismatch for `archive_v2`

## 9.4 Legacy archive status
Legacy `archive` still exists in code and runtime.
Truthfully, it is in a coexistence/manual-fallback state **in code intent**, but in the live DB schedule it is still the daemon-scheduled archive worker.

That means:
- legacy archive is **not yet fully retired operationally**
- Archive V2 is **not yet unambiguously the live scheduled daemon path**

## 9.5 Final production-path truth statement
The most accurate statement today is:

> Archive V2 is the intended nightly production archive path in code, dedicated CLI, and operator flows. However, the live unified-daemon schedule database is still wired to legacy `archive`, so the production nightly path is not yet fully unambiguous in runtime scheduling.

---

## 10. Key commands cheat sheet

## 10.1 Unified runtime
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --loop
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --status
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker lowfreq
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker midfreq
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker highfreq
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker archive
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m ifa_data_platform.runtime.unified_daemon --worker archive_v2
```

## 10.2 Manifest/runtime ops
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py manifest
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane lowfreq
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane midfreq
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane highfreq
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane archive_v2
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/runtime_manifest_cli.py run-status --lane archive_v2 --limit 10
```

## 10.3 Archive V2
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_production_cli.py nightly --business-date YYYY-MM-DD
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_production_cli.py backfill --start-date YYYY-MM-DD --end-date YYYY-MM-DD
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_run.py --profile profiles/<profile>.json
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py recent-runs --limit 10
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py summary --days 14
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/archive_v2_operator_cli.py repair-backlog --limit 20
```

---

## 11. Known current limitations / partial areas

### 11.1 Archive V2 runtime scheduling mismatch
This is the main live operations mismatch:
- code intent: `archive_v2` nightly
- live DB schedule: `archive` nightly

### 11.2 Not every summary table is a full-fidelity operator surface
For example:
- `midfreq_execution_summary` is present but not a rich per-dataset run ledger

### 11.3 Highfreq scope tables are present but currently empty
Observed:
- `highfreq_active_scope = 0`
- `highfreq_dynamic_candidate = 0`

This does not invalidate highfreq working truth, but it means scope-dynamic behavior is not currently the primary active evidence surface.

### 11.4 Some old documentation names are stale
Examples:
- old references to `runtime_manifest_snapshots` are stale; live/code truth uses `target_manifest_snapshots`
- any doc claiming the daemon is already unambiguously switched to `archive_v2` is ahead of current DB truth

### 11.5 Direct ETF intraday archive truth is still not a first-class retained family
The system has proxy-style intraday truth and ETF daily paths, but direct retained ETF intraday truth is not yet a clean first-class retained source family.

---

## 12. Truthful final summary

### What is definitely true now
- lowfreq, midfreq, and highfreq all have real implemented code paths and live DB writes
- unified runtime daemon is the official long-running runtime model in code
- Archive V2 is real, populated, operator-inspectable, and actively used
- Archive V2 has run/completeness/repair evidence tables that materially exist in DB
- source -> retained/working -> archive flow is real for key families

### What is not yet fully aligned
- the live daemon schedule DB has not yet fully switched from legacy `archive` to `archive_v2`

### Engineering conclusion
Another engineer should understand the system as:
- **collection layers are real**
- **Archive V2 is real**
- **the unified runtime is the official orchestration model**
- **the remaining ambiguity is not whether Archive V2 exists, but whether live daemon scheduling has fully adopted it**

That is the current implementation truth.
