# Trailblazer Upgrade Plan for iFA Data Platform

> **Document status:** Historical baseline planning document. Superseded by later canonical current-state documents, especially TRAILBLAZER_FINAL_EVIDENCE_PACKAGE_2026-04-15.md, TRAILBLAZER_RUNTIME_RUNBOOK_2026-04-15.md, TRAILBLAZER_REPRO_SMOKE_2026-04-15.md, and TRAILBLAZER_COLLECTION_READINESS_GAP_CLOSURE_2026-04-15.md.
_Date: 2026-04-14_

## 1. Background and why this upgrade is needed

The Data Platform is no longer operating in a vacuum.
A new Business Layer now exists and defines explicit, owner-scoped target sets such as:

- `key_focus`
- `focus`
- `archive_targets`
- `tech_key_focus`
- `tech_focus`

This changes the architectural contract.
The platform should no longer choose collection targets primarily through full-universe scanning, ad hoc symbol pools, or dataset-local hardcoding. Instead, the Business Layer should become the upstream selector of **what** to collect, while the Data Platform remains the execution engine that decides **how**, **when**, and **with which worker** that collection occurs.

The correct direction is therefore not:
- blindly continue the current lowfreq/midfreq/archive implementation as-is, nor
- rewrite the entire platform from scratch.

The correct direction is a **Trailblazer-style upgrade**:
- preserve and reuse the strongest parts of the existing ingestion/runtime substrate,
- retire duplicated runtime paths where appropriate,
- formalize a unified daemon/worker operating model,
- align target selection to the Business Layer,
- and explicitly define archive/backfill as a related but distinct operating concern.

This document is a planning/review artifact only. It does **not** redesign the Business Layer and does **not** start implementation.

---

## 2. Current-state repository assessment

### 2.1 Repository reality observed

Repository inspected:
- `/Users/neoclaw/repos/ifa-data-platform`

Observed major areas:
- `src/ifa_data_platform/lowfreq/*`
- `src/ifa_data_platform/midfreq/*`
- `src/ifa_data_platform/archive/*`
- `src/ifa_data_platform/runtime/*`
- `src/ifa_data_platform/db/*`
- `src/ifa_data_platform/config/*`
- `alembic/versions/*`
- `scripts/*`
- `tests/*`
- multiple top-level design/runbook markdown files

### 2.2 What is already implemented

#### Low-frequency line
Lowfreq is the most mature runtime line in the repository.
It already has:
- dataset registry
- runner
- daemon
- daemon config
- daemon health
- daemon/group state persistence
- raw fetch persistence
- version persistence
- current/history table patterns for many slow-moving datasets
- integration tests and validation scripts

This is not just a stub. It is a real, production-leaning first-generation collection line.

#### Mid-frequency line
Midfreq is implemented as a second line that mirrors lowfreq patterns:
- separate daemon
- separate config module
- separate orchestrator
- separate schedule memory/state
- separate dataset registry
- separate runner
- separate execution summary table

It is real enough to run, but architecturally it duplicates lowfreq structure heavily.

#### Archive line
Archive has become a third runtime family with meaningful implementation depth:
- archive daemon
- archive config
- archive orchestrator
- archive run store
- archive job store
- archive checkpoint store
- archive summary
- archive daemon state
- stock/macro/futures-specific archivers

Archive is not just a draft. It already has a concept of windows, runs, checkpoints, and summary persistence.

#### Shared substrate pieces
The repo already has useful cross-cutting components:
- SQLAlchemy engine factory (`db/engine.py`)
- central settings module (`config/settings.py`)
- Alembic-managed schema evolution
- basic runtime/job state infrastructure
- Tushare client with timeout handling
- symbol universe support

### 2.3 What is partial

#### Shared runtime layer
There is a `src/ifa_data_platform/runtime/*` area, but it is still skeletal.
It appears to be a placeholder runtime abstraction rather than the actual unified runtime substrate.
For example:
- `runtime/scheduler.py` still uses a dummy worker path
- `job_runs` exists but is not the canonical state path for lowfreq/midfreq/archive today

So the repository already hints at a unified runtime direction, but the actual runtime logic remains split across lowfreq/midfreq/archive implementations.

#### Config discipline
There is a central settings layer, but operating defaults are still partly scattered across:
- daemon config modules
- archive config
- inline code defaults
- scripts
- docs

This is workable at current scale, but not strong enough for a unified multi-mode daemon architecture.

#### Schema/init ownership clarity
There are real Alembic migrations and many real tables, but the overall control-plane/schema ownership model is still fragmented by domain line:
- lowfreq owns some state tables
- midfreq owns its own state tables
- archive owns its own state tables
- runtime has a generic `job_runs` path that is not the real operational backbone

The result is a partially evolved system, not yet a clean platform-wide execution model.

### 2.4 What is duplicated

This is the most important architectural observation.

There are three parallel runtime families:
- lowfreq daemon family
- midfreq daemon family
- archive daemon family

Each family independently implements some combination of:
- daemon loop
- schedule window matching
- run orchestration
- health logic
- state persistence
- retry/fallback handling
- summary persistence

That duplication is currently tolerable because each line was developed incrementally, but it is not the right long-term operating model.

The specific duplication patterns include:
- lowfreq and midfreq both implement near-isomorphic daemon loop structures
- lowfreq and midfreq both implement independent schedule memory/state concepts
- archive repeats daemon-state concepts with a third naming/style lineage
- multiple lines implement their own run summary state instead of converging on a shared execution record contract

### 2.5 What is obsolete or likely should be retired

#### Separate long-term lowfreq daemon and midfreq daemon as primary architecture
These should be treated as transitional implementations, not the target architecture.
The future shape should be one unified runtime daemon with pluggable worker lanes.

#### Symbol-universe-only target selection as the main upstream selector
The old A/B/C `symbol_universe` logic is still useful, but it should no longer be treated as the sole source of truth for target selection.
It becomes a supporting asset pool / eligibility set / fallback validation source.
Business Layer focus lists should become the primary collection target selector.

#### Generic runtime placeholder as-is
The current generic runtime module is too thin to serve as the final abstraction. It should either be upgraded into the real unified runtime substrate or retired as dead-end scaffolding.

### 2.6 What can be reused cleanly

#### Reuse strongly recommended
1. **DB engine/settings base**
   - `config/settings.py`
   - `db/engine.py`

2. **Lowfreq runner/dataset registry patterns**
   - the separation of dataset config, runner, adaptor, raw/current/history/version is worth preserving conceptually

3. **Archive checkpoint/run/summary ideas**
   - archive already models long-running resumable work better than lowfreq/midfreq do

4. **Existing Alembic migration chain**
   - should remain the schema authority

5. **Tushare client timeout/retry call patterns**
   - should be consolidated and standardized, not rewritten from zero

6. **Tests and validation scripts as acceptance seeds**
   - current tests are not sufficient for the future plan, but they are useful anchors

### 2.7 What should likely be rewritten or heavily refactored

1. **Daemon layer unification**
   - lowfreq daemon
   - midfreq daemon
   - shared runtime placeholder
   
   These should converge toward one real orchestrator/worker daemon model.

2. **Target selection plumbing**
   - any dataset-local or universe-local hardcoded target choice logic should be refactored to consume Business Layer selection inputs

3. **Execution/audit model**
   - the system should move toward one shared run-control contract for daemon/worker execution records, while still allowing archive-specific fields where needed

4. **Config topology**
   - defaults should move out of scattered code branches and into explicit configuration files with narrow CLI overrides

---

## 3. Current-state DB/schema/init assessment

### 3.1 Live database context used

Inspected against:
- `DATABASE_URL='postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'`
- schema: `ifa2`

### 3.2 Data Platform-related tables already present in live DB

Observed present and populated tables relevant to Data Platform include:

#### Runtime/registry/state
- `symbol_universe` (85)
- `dataset_versions` (1352)
- `lowfreq_datasets` (69)
- `lowfreq_runs` (2814)
- `lowfreq_raw_fetch` (381)
- `lowfreq_daemon_state` (1)
- `lowfreq_group_state` (1)
- `midfreq_datasets` (8)
- `midfreq_daemon_state` (1)
- `midfreq_execution_summary` (2)
- `archive_jobs` (3)
- `archive_runs` (3)
- `archive_checkpoints` (3)
- `archive_summary_daily` (1)
- `archive_daemon_state` (1)

#### Historical/archive assets
- `stock_daily_history` (4846)
- `macro_history` (1223)
- `futures_history` (778)
- `stock_history_checkpoint` (1)

#### Lowfreq current/history families
Present for many lowfreq datasets, including for example:
- `stock_basic_current` / `stock_basic_history`
- `company_basic_current` / `company_basic_history`
- `index_basic_current` / `index_basic_history`
- `etf_daily_basic_current` / `etf_daily_basic_history`
- `share_float_current` / `share_float_history`
- `news_current` / `news_history`
- `research_reports_current` / `research_reports_history`
- `investor_qa_current` / `investor_qa_history`
- `forecast_current` / `forecast_history`
- `margin_current` / `margin_history`
- `top10_holders_current` / `top10_holders_history`
- `top10_floatholders_current` / `top10_floatholders_history`
- and others

#### Midfreq market state/current/history families
Present in DB:
- `equity_daily_bar_current` / `equity_daily_bar_history`
- `index_daily_bar_current` / `index_daily_bar_history`
- `etf_daily_bar_current` / `etf_daily_bar_history`
- `northbound_flow_current` / `northbound_flow_history`
- `limit_up_down_status_current` / `limit_up_down_status_history`

### 3.3 Code-implied but missing tables

From code references vs live DB inspection, the following were referenced but not present:
- `stock_fund_forecast_current`
- `stock_fund_forecast_history`

This is a concrete schema/init gap.
It means at least one dataset path or persistence path is implied by code but not actually materialized in the live DB.
That should be treated as a required work item.

### 3.4 Present but unclear / stale-ish tables

Two noteworthy cases:
- `job_runs` exists but row count is `0`
- `midfreq_window_state` exists but row count is `0`

Interpretation:
- `job_runs` is currently not the real shared runtime audit backbone, despite the generic runtime code implying it might be
- `midfreq_window_state` may be structurally present but not meaningfully active yet, or only active in certain runtime paths not recently exercised

These are not necessarily wrong, but they are evidence of unfinished runtime consolidation.

### 3.5 Schema/init discipline assessment

Positive:
- there is a real Alembic chain
- many runtime and archive tables do have explicit migrations
- archive control in particular has a reasonably coherent migration (`017_archive_control`)

Weak points:
- the repository has evolved in domain slices rather than a fully unified platform plan
- some tables are implied by code without confirmed live presence
- schema ownership for unified runtime/audit records is not yet settled
- current migrations reflect incremental delivery history, not yet a clean Trailblazer target-state model

### 3.6 Business Layer table interaction stance

Business Layer tables are live in the same schema (`ifa2`) but are not Data Platform-owned:
- `focus_lists`
- `focus_list_items`
- `focus_list_rules`

Data Platform should **consume** these tables as upstream selectors.
It should not redesign them here.

---

## 4. Business-layer-driven collection model

### 4.1 Principle

Future collection target selection should primarily be derived from Business Layer lists, not directly from whole-market scanning and not from dataset-local hardcoding.

The contract must be explicit enough that:
- Business Layer remains the selector of business intent,
- Data Platform remains the selector of execution mechanics,
- ownership boundaries stay clean,
- and target resolution is reproducible and auditable.

### 4.2 Business Layer -> Data Platform contract

The Data Platform should treat the Business Layer as a **read-only upstream selector**.

#### What Data Platform reads from Business Layer
At minimum, Data Platform reads from:
- `ifa2.focus_lists`
- `ifa2.focus_list_items`
- `ifa2.focus_list_rules`

Using only fields needed for collection targeting, such as:
- owner scope: `owner_type`, `owner_id`
- list identity: `list_type`, `name`
- list orientation: `asset_type`, `frequency_type`, `is_active`
- item identity: `symbol`, `name`, `asset_category`, `priority`, `is_active`
- list rules: `rule_key`, `rule_value`

#### What Data Platform must treat as read-only
The following are read-only from the Data Platform perspective:
- Business Layer list definitions
- Business Layer membership
- Business Layer list rules
- Business Layer owner semantics
- Business Layer default seed logic

Data Platform must **not** mutate Business Layer state in normal runtime operation.
If future workflows need synchronization, that should be designed as explicit control-plane/admin behavior, not hidden inside collection workers.

#### What Data Platform may enrich locally
Data Platform may derive or enrich **its own execution metadata** outside Business Layer tables, for example:
- resolved execution lane
- source adapter choice
- worker type
- manifest generation timestamp
- target resolution hash/version
- eligibility check status
- archive catch-up requirement
- dedupe/merge classification
- target last-seen / first-seen timestamps

That enrichment should live in Data Platform-owned runtime state or manifest records, not by mutating Business Layer rows.

### 4.3 Intended interpretation

#### Runtime production target families
Business Layer should determine the target object sets for production collection lanes:
- `key_focus`
- `focus`
- theme-specific overlays such as `tech_key_focus`, `tech_focus`

These become the upstream selectors for A/B-style collection intent.

#### Archive target families
Business Layer should determine archive/backfill target sets primarily via:
- `archive_targets`
- with `frequency_type` distinctions such as `minute`, `15min`, `daily`

### 4.4 Mapping from Business Layer lists into runtime intent

The mapping should be explicit.

#### `key_focus`
Default interpretation:
- highest-priority production runtime target pool
- candidate upstream source for future A-lane / high-priority midfreq / selective lowfreq enrichments
- should resolve to the smallest, highest-conviction runtime manifest set

#### `focus`
Default interpretation:
- broader production runtime pool
- primary B-style runtime collection scope for non-archive collection lanes
- suitable for lowfreq and midfreq lane resolution depending on dataset and asset type

#### `tech_key_focus`
Default interpretation:
- same execution semantics as `key_focus`
- additional business theme dimension: `technology`
- should not create a new runtime subsystem; it should resolve into the same normalized manifest with a theme marker

#### `tech_focus`
Default interpretation:
- same execution semantics as `focus`
- additional business theme dimension: `technology`
- overlap with broad `focus` is acceptable and should be handled via manifest dedupe rules rather than business-layer redesign

#### `archive_targets`
Default interpretation:
- upstream archive/backfill scope
- `frequency_type` determines archive lane targeting:
  - `minute` -> minute-level archive workload
  - `15min` -> 15-minute archive workload
  - `daily` -> daily archive workload

### 4.5 How this should coexist with asset-type-specific logic

The Business Layer selects the target objects.
The Data Platform still decides the asset-specific worker implementation.

So the target-selection flow should become:

`business-layer list membership -> normalized collection target manifest -> asset-type-specific worker routing -> source fetch -> persistence`

That means:
- stocks still route to stock workers
- macro still routes to macro workers
- futures/commodity/precious metal still route to their workers

But the system should no longer let each worker independently decide the universe of symbols/series to collect.

### 4.6 Relationship to `symbol_universe`

`symbol_universe` should not simply disappear.
It should shift roles.

Recommended future role of `symbol_universe`:
- supporting eligibility pool
- optional broad asset registry
- fallback/default pool source
- validation source for certain stock universes

Recommended primary selector role:
- Business Layer focus/archive lists

### 4.7 Normalized target manifest concept

The Data Platform should introduce an internal, computed target manifest layer that resolves Business Layer lists into a normalized execution set.
This should become the canonical contract between Business Layer intent and worker execution.

#### Conceptual manifest grain
Recommended grain:
- one row/object per resolved target per execution lane per frequency semantics

#### Required manifest fields
At minimum, the normalized target manifest should contain:
- `manifest_id` or manifest hash/version
- `generated_at`
- `source_owner_type`
- `source_owner_id`
- `source_list_name`
- `source_list_type`
- `source_frequency_type`
- `source_asset_type`
- `source_rule_map` or equivalent resolved rule bundle
- `symbol_or_series_id`
- `display_name`
- `asset_category`
- `priority`
- `theme_tags` (for example `technology`)
- `resolved_lane` (`lowfreq`, `midfreq`, `archive`, future `highfreq`)
- `resolved_worker_type`
- `resolved_granularity`
- `source_adapter_policy`
- `is_active`
- `dedupe_key`
- `selection_reason`
- optional `validation_status` against `symbol_universe` or other eligibility registries

#### Ownership boundary for manifest
- Business Layer owns list intent
- Data Platform owns manifest resolution and execution metadata
- Manifest rows/objects should be treated as **derived execution artifacts**, not business truth

#### Read-only vs enrichable summary
- read-only from Business Layer: list identity, item membership, rules, owner scope
- enrichable by Data Platform: lane resolution, dedupe, worker selection, validation, catch-up requirement, source policy, execution metadata

### 4.8 Manifest materialization strategy

Recommended phased approach:

#### Phase A
- in-memory manifest generation for one-shot/manual runs
- logged and printable for audit

#### Phase B
- persisted manifest snapshot for service runs and archive diffing
- enables deterministic replay, run linkage, and membership delta handling

This is the cleanest place to reason about overlap, dedupe, lane mapping, and future theme expansion.

---

## 5. Proposed unified runtime daemon architecture

### 5.1 Target architecture

The long-term runtime direction should be:
- **one lightweight unified runtime daemon**
- **multiple short-lived workers**
- daemon = schedule/orchestrate
- worker = execute one round and exit

This daemon should eventually cover:
- low frequency
- mid frequency
- future high frequency

Archive may share some substrate but should remain a distinct execution concern at the planning level because it has different semantics.

### 5.2 Why the daemon should remain lightweight

The daemon should not become a giant always-live in-process system holding all collection logic.
That would make:
- testing harder
- timeouts harder
- crash containment worse
- operability blurrier

Instead, the daemon should focus on:
- evaluating time/calendar mode
- loading config
- loading Business Layer target intent
- deciding which worker round should run now
- creating a run record
- spawning the worker
- collecting result/exit status
- updating run state
- sleeping until next loop or next window

### 5.3 Worker responsibilities

A worker should:
- accept a specific workload contract
- load the relevant targets for one round
- execute the concrete collection logic
- persist data
- persist result summary / metrics / status
- exit

Workers should not behave like hidden daemon loops.
Each worker should be explicit, bounded, and auditable.

### 5.4 Recommended runtime shape

Recommended shape:

- `runtimed` (unified daemon)
  - loop / schedule / dispatch / supervise
- `workers/lowfreq_round.py`
- `workers/midfreq_round.py`
- future `workers/highfreq_round.py`
- archive line can reuse common execution scaffolding but keep its own policy path

### 5.5 Why not merge archive fully into the same daemon immediately

Archive is different enough to justify a separate policy plane:
- different runtime windows
- different backlog/catch-up semantics
- different success criteria
- different time horizon
- checkpoint/resume as core, not optional

The correct direction is:
- unify shared execution substrate and patterns,
- but do not prematurely collapse archive semantics into the same exact scheduling policy as production runtime.

---

## 6. Daemon vs worker responsibility split

### 6.1 Daemon responsibilities

The unified runtime daemon should own:
- schedule evaluation
- mode resolution (service vs one-shot)
- target-manifest loading
- deciding which lane to trigger
- run record creation
- worker subprocess launch
- timeout supervision
- retry / degrade / skip policy
- loop continuation
- top-level health/status reporting

### 6.2 Worker responsibilities

Workers should own:
- one-round execution for one lane/job
- asset-type-specific routing
- source calls
- persistence into current/history/archive/raw/version tables
- worker-level metrics
- structured result output

### 6.3 Why this split is correct

This split gives:
- clear testability
- bounded failure domains
- easier one-shot development mode
- better timeout control
- cleaner run audit trail
- cleaner future process supervision (systemd/launchd/container)

---

## 7. Service mode vs one-shot/manual mode

### 7.1 Service/default mode

Requirements:
- long-running
- loops forever
- evaluates schedule/calendar continuously
- triggers the correct worker when a window is active
- updates daemon state and run records

This is the production operating mode.

### 7.2 One-shot/manual/test mode

Requirements:
- run one specified workload only
- exit after completion
- support timeout/max-runtime controls
- support selecting a lane or specific worker type
- support development/testing without requiring a resident daemon

This is essential.
Without it, development becomes operationally expensive and hard to reason about.

### 7.3 Recommended one-shot examples

Examples the future platform should support:
- one lowfreq round
- one midfreq round
- one archive daily backfill step
- one archive minute catch-up shard
- one dry-run target-manifest resolution

---

## 8. Logging / run records / auditability requirements

### 8.1 Why this matters

The future system cannot be treated as “some scripts that happen to run.”
It needs platform-grade observability and operational records.

### 8.2 Unified runtime run-state / audit model

The platform should move toward a logically complete, explicit run-state model that covers:
- daemon lifecycle state
- worker execution records
- trigger mode
- manifest linkage
- retry/timeout semantics
- summary state

This section defines the conceptual model, even if final schema names are deferred.

### 8.3 Conceptual entities

#### A. Daemon state
Represents the live operating state of a daemon process or daemon lane.

Should include conceptually:
- daemon name / lane
- current mode (`service`, `once`, `manual`, `test`)
- last loop time
- last dispatch time
- currently running worker count
- current health status
- last success time
- last failure time
- last failure summary
- config version/hash loaded
- process identity / host identity if useful

#### B. Worker run record
Represents one bounded worker execution round.
This should become the primary audit object for actual collection work.

Should include conceptually:
- `run_id`
- optional `parent_run_id`
- optional `daemon_invocation_id`
- lane (`lowfreq`, `midfreq`, `archive`, future `highfreq`)
- worker type
- trigger mode (`auto`, `manual`, `test`, `retry`, `backfill`)
- manifest reference / manifest hash
- owner scope and source list references when Business Layer-driven
- start time
- end time
- elapsed duration
- final status
- retry attempt number
- timeout budget
- actual timeout hit flag
- target counts
- record counts
- error class / error summary
- summary payload pointer / structured JSON summary
- log pointer if externalized

#### C. Manifest snapshot / manifest reference
Represents the exact resolved target set used by a worker run.
This may begin as an in-memory hash/serialized payload and later become a persisted table.

Should include conceptually:
- manifest id/hash
- generation time
- source business-layer selector scope
- lane/granularity resolution
- target membership snapshot
- config version/hash

#### D. Run summary object
Represents the human/operator-friendly reduction of a worker run.
May be materialized in DB, emitted as JSON, or both.

Should include conceptually:
- run id
- lane
- worker type
- overall status
- counts
- major failures
- retry note
- timeout note
- source/target notes

### 8.4 Status model

Recommended canonical status vocabulary:
- `pending`
- `running`
- `succeeded`
- `failed`
- `partial`
- `timed_out`
- `killed`
- `skipped`
- `cancelled`

Recommended semantic distinctions:
- `failed` = execution completed with error
- `timed_out` = runtime budget exhausted
- `killed` = externally terminated
- `partial` = some targets succeeded, some failed, result still persisted as incomplete
- `skipped` = policy said do not run

### 8.5 Trigger mode model

Recommended trigger mode vocabulary:
- `auto_service`
- `manual_once`
- `manual_worker`
- `test_once`
- `retry`
- `backfill`
- `catchup`

This is important because a worker run should always be explainable later.
A run that happened automatically in service mode should be distinguishable from a developer one-shot test or an archive catch-up rerun.

### 8.6 Manifest-version linkage

Every worker run should conceptually link to the target set it actually used.
Without this, later debugging becomes ambiguous.

Recommended rule:
- no production worker run without a manifest reference or reproducible manifest hash

This is especially important once:
- Business Layer lists change over time
- archive target membership changes over time
- theme-specific lists overlap with broad lists

### 8.7 Minimum audit record requirements

For every daemon-triggered or manual-triggered run, the system should persist:
- run id
- parent daemon id / invocation id when applicable
- lane (`lowfreq`, `midfreq`, `archive`, future `highfreq`)
- worker type
- trigger type (`auto`, `manual`, `test`, `backfill`, `retry`)
- owner/list scope when driven by Business Layer
- manifest version/hash linkage
- start time
- end time
- status (`pending`, `running`, `succeeded`, `failed`, `timed_out`, `killed`, `partial`, `skipped`)
- retry count
- exit reason / error summary
- records processed
- target count attempted
- target count succeeded/failed/skipped
- log pointer / summary blob / trace pointer

### 8.8 Current-state assessment vs future requirement

Current system already has fragments of this:
- `lowfreq_runs`
- `archive_runs`
- `midfreq_execution_summary`
- daemon state tables
- summary tables

But these are fragmented.
The Trailblazer plan should introduce a clearer common execution record contract, even if domain-specific side tables remain.

### 8.9 Retry and re-run policy

The design should explicitly support:
- manual re-run of one failed worker round
- retry with bounded attempt count
- timeout classification separate from general failure
- optional replay from same manifest snapshot
- clear distinction between retrying current production work and catch-up/backfill re-execution

### 8.10 Logging discipline

Logs should be structured enough to correlate with run IDs.
At minimum:
- all worker logs should emit run ID
- all daemon logs should emit loop/run context
- error classification should distinguish source failure, target resolution failure, schema failure, timeout, and supervisor kill
- logs should make it possible to reconstruct which manifest and which selector scope were used

---

## 9. Archive architecture and archive-target-change handling

### 9.1 Archive should be treated as its own concern

Archive is not just another ordinary collection window.
It is a historical accumulation and backfill system.

Therefore archive must explicitly support:
- service/default loop mode
- one-shot/manual mode
- configurable progression parameters
- checkpoint/resume
- long-range catch-up

### 9.2 What should be shared with runtime daemon work

Archive should reuse shared substrate where reasonable:
- DB engine/config
- timeout/retry helpers
- process execution supervision
- run record conventions
- logging conventions

### 9.3 What should remain distinct in archive

Archive should keep distinct semantics for:
- checkpoint state
- backfill windows
- historical range planning
- target catch-up policy
- membership-diff handling

### 9.4 The archive target membership change problem

This is a critical design issue and must be handled explicitly.

Example:
- a daily archive target list has 200 members today
- 30 days later, one new target is added
- that new target needs historical backfill

The system therefore needs a principled answer to:
- where target-set changes are detected
- how newly-added targets are recognized
- whether historical backfill is required
- how catch-up is scheduled
- how to avoid silent long-term holes

### 9.5 Recommended solution pattern

#### Step 1: persist target-manifest snapshots
For archive-relevant target sets, the platform should persist or at least compute diffable manifest snapshots keyed by:
- owner
- list name
- frequency type
- asset category
- effective date / observation time

#### Step 2: detect membership deltas
On archive planning or daemon loop, compare the current resolved archive target set against the last known resolved target set.

Classify changes:
- additions
- removals
- metadata changes

#### Step 3: additions should create catch-up work
When a new archive target is added, create a backfill intent, for example:
- target id
- asset category
- required granularity
- desired backfill start date
- desired backfill end date
- current checkpoint state

#### Step 4: backfill should be incremental, not monolithic
Newly-added targets should not force a giant full-system restart.
They should create incremental catch-up workloads with:
- bounded shard size
- bounded day range per run
- resumable checkpoint state
- measurable progress

#### Step 5: completion should be auditable
There should be a clear way to answer:
- which archive targets are fully caught up
- which are partially caught up
- which were recently added and not yet complete

### 9.6 Archive membership delta handling policy matrix

This section upgrades the earlier principles into a more execution-grade policy matrix.

#### A. Newly added target

##### Daily archive target added
Default policy:
- create catch-up intent immediately
- default historical backfill target = **1 year** or current archive baseline, whichever is the current platform standard
- backlog execution priority = **medium-high**, but should not preempt current production runtime windows
- run as incremental catch-up batches until fully caught up

##### 15min archive target added
Default policy:
- create catch-up intent immediately
- default historical backfill target = **rolling 90 days** initially unless policy file says otherwise
- backlog execution priority = **medium**, because data volume is materially larger than daily
- catch-up should be shard-based and resumable

##### Minute archive target added
Default policy:
- create catch-up intent immediately
- default historical backfill target = **rolling 30 days** initially unless policy file says otherwise
- backlog execution priority = **guarded medium/low**, because minute data is expensive
- should not starve current archive freshness or runtime windows

These defaults should eventually be configurable, but the planning contract must define the default answer now.

#### B. Removed target
Default policy:
- do **not** delete existing historical records automatically
- mark target as no longer active in current archive membership snapshot
- stop future incremental archive work for that target unless an override policy says otherwise
- preserve previously archived history as historical asset unless retention policy explicitly requires cleanup

#### C. Metadata change without membership removal
Examples:
- display name changed
- theme tag changed
- priority changed
- non-identity list metadata changed

Default policy:
- do not trigger full historical backfill automatically
- update manifest snapshot and record metadata change event
- only create catch-up work if the metadata change implies a lane/granularity change or asset-routing change

#### D. Frequency/granularity change
Examples:
- target moves from daily archive set only into 15min archive set
- or newly becomes part of minute archive scope

Default policy:
- treat as new work for the newly-added granularity
- existing lower-cost history does not satisfy higher-granularity completeness
- create a new checkpoint/catch-up intent for the new granularity

### 9.7 Backlog priority vs current work policy

Recommended default scheduling policy:
1. protect current production runtime windows first
2. protect archive freshness for already-active current archive jobs second
3. consume backlog/catch-up capacity third
4. newly-added expensive minute catch-up should be rate-limited to avoid starving the rest of the archive line

This implies archive backlog should be a separately visible queue, not invisible implicit work.

### 9.8 Recommended target-change semantics

Recommended default assumption:
- additions are common enough to plan for
- removals should not automatically erase history
- replacements should be modeled as remove + add, but history remains as historical asset for old targets unless explicit retention policy says otherwise

### 9.9 Why this matters

Without this, archive target sets become logically inconsistent over time.
You would appear to have an archive target list, but newly-added members would silently lack long-range history.
That is unacceptable for a long-term asset platform.

---

## 10. Shared infra/config principles

### 10.1 Database access

All daemon/worker/archive paths should use shared DB engine construction and connection discipline.
No component should invent its own ad hoc connection style.

Recommendations:
- one shared engine factory
- transaction boundaries explicit at store/repository layer
- pool sizing configurable centrally
- schema explicit (`ifa2`)
- no silent fallback to `public`

### 10.2 Configuration / reproducibility model

System defaults should primarily live in configuration files, not scattered inline through daemon code.
CLI parameters are valid for:
- one-shot testing
- overrides
- manual maintenance

But not for the core operating defaults.

Recommended final config model:

#### Config files should own
- daemon schedules and window definitions
- lane enable/disable state
- worker timeout defaults
- retry budgets
- concurrency limits
- archive shard sizes and catch-up policies
- Business Layer selector defaults (canonical owner scope, allowed list names, lane mapping rules)
- source adapter policy per lane/asset class
- profiling/reporting toggles

#### Environment variables should own
- secrets and credentials
- DB connection URL
- optional environment identity (`dev`, `test`, `prod`)
- external API tokens
- host-specific overrides that should not be committed

#### CLI parameters should own
- one-shot/manual invocation scope
- temporary timeout override for testing
- explicit worker/lane selection for manual runs
- dry-run flags
- ad hoc replay/rerun controls

CLI should not become the place where permanent operating defaults live.

### 10.3 Dev / test / prod configuration stance

Recommended conceptual separation:

#### dev
- optimized for one-shot/manual iteration
- lower target counts allowed
- shorter timeouts acceptable
- verbose logging enabled

#### test
- deterministic fixtures and controlled windows
- fake or constrained target manifests
- source mocks or narrow integration targets

#### prod
- canonical schedules
- real Business Layer selector input
- strict timeout/retry policies
- stable logging/audit behavior

### 10.4 What a third-party developer should need to configure

A new developer should be able to run the platform by supplying only a clear, bounded set of configuration inputs:
- clone the repo
- install Python dependencies
- configure database URL
- run Alembic migrations
- provide Tushare or other source credentials
- select environment (`dev` / `test` / `prod` style)
- run one-shot validation commands

That means the platform should eventually document a cold-start path where nothing depends on hidden local state.

### 10.5 Concurrency control

This system should be conservative by default.
Do not assume unlimited parallelism.
Need explicit knobs for:
- max concurrent workers
- per-worker max target batch size
- per-source throttling
- archive shard size
- timeout budgets

### 10.6 Timeout/retry policy

Timeout and retry behavior should be standardized, not lane-specific guesswork.
At minimum:
- worker-level timeout
- source-call timeout
- bounded retries
- timeout classification in run records
- retry policy different for runtime vs archive where justified

### 10.7 Schema/init discipline

All Data Platform-owned tables must remain Alembic-managed or be clearly assigned to explicit SQL/init artifacts with documented authority.
No ghost tables implied by code but missing in DB.
No ad hoc production init drift.

---

## 11. Proposed work breakdown / to-do plan

This section is intentionally concrete and reviewable.

### T1. Produce authoritative runtime target-resolution contract
**Why needed**
- Business Layer must become the upstream selector of collection targets.
- Current system lacks a clean contract between Business Layer selection and Data Platform execution.

**Success looks like**
- a documented target manifest schema/object exists
- lane mapping rules are explicit
- Business Layer inputs map deterministically to runtime/archive workloads

**How to test**
- unit tests for manifest resolution from sample `focus_lists`/`focus_list_items`
- manual dry-run manifest generation against live DB
- diff test for `default_key_focus`, `default_focus`, `tech_key_focus`, `tech_focus`, `archive_targets`

### T2. Introduce unified runtime daemon plan and entrypoint
**Why needed**
- current lowfreq and midfreq daemon stacks are duplicated
- long-term architecture requires one scheduler/orchestrator daemon

**Success looks like**
- one canonical daemon entrypoint exists for production runtime lanes
- daemon decides lane/window and spawns one worker round
- lowfreq/midfreq old daemon paths are clearly transitional or compatibility wrappers

**How to test**
- unit tests for window matching and lane dispatch
- one-shot manual runs for lowfreq and midfreq lanes
- service-loop smoke test with mocked time windows

### T3. Define canonical worker contract
**Why needed**
- workers must become explicit one-round execution units
- current runners exist, but subprocess/worker contract is not unified

**Success looks like**
- worker input contract defined (lane, target manifest reference, timeout, trigger type)
- worker output contract defined (status, counts, summary, logs)

**How to test**
- worker contract serialization tests
- subprocess invocation tests
- failure/timeout tests

### T4. Consolidate run-record / audit schema
**Why needed**
- current audit state is fragmented across lowfreq/midfreq/archive-specific tables
- platform needs consistent operability

**Success looks like**
- shared execution record model defined
- existing domain-specific tables either map into it or are clearly layered around it

**How to test**
- schema migration test
- insert/update lifecycle tests
- manual run -> run record -> health/status verification

### T5. Refactor target selection away from dataset-local hardcoding
**Why needed**
- Business Layer should drive selection
- current code still relies heavily on symbol universe and dataset-local source logic

**Success looks like**
- stock/macro/futures workers consume resolved targets
- symbol universe becomes supporting registry, not primary selector

**How to test**
- manifest-driven one-shot runs
- comparison tests between old and new selected target sets where applicable
- no full-universe accidental scans

### T6. Archive target-change detection and catch-up planning
**Why needed**
- newly-added archive targets must not silently miss history

**Success looks like**
- archive target membership changes are detectable
- new targets create backfill intents/checkpoints
- catch-up can be resumed safely

**How to test**
- synthetic membership-add test
- one target added to daily archive list -> verify catch-up work item created
- checkpoint/resume tests across multiple partial runs

### T7. Resolve implied-missing schema gaps
**Why needed**
- code currently implies tables not present in live DB

**Success looks like**
- each code-referenced table is either:
  - present and migrated, or
  - removed from active code path, or
  - explicitly postponed with documentation

**How to test**
- schema parity audit script
- CI check comparing live migration metadata against referenced persistence tables

### T8. Config convergence
**Why needed**
- defaults are currently split across daemon config modules and code

**Success looks like**
- clear config topology for runtime + archive + source + Business Layer selector integration
- CLI overrides remain limited and explicit

**How to test**
- config load tests
- env/file precedence tests
- one-shot runs with and without overrides

### T9. Runtime/worker operability surface
**Why needed**
- system must be manageable, inspectable, restartable

**Success looks like**
- health/status commands are meaningful for unified runtime
- recent runs and failures are easy to query
- manual rerun of a failed workload is possible

**How to test**
- CLI/operator smoke tests
- watchdog freshness tests
- stale worker detection tests

### T10. Documentation deliverables package
**Why needed**
- this Trailblazer plan is not enough by itself for long-term operability
- the platform must eventually be understandable by another developer/operator without chat context

**Success looks like**
The repository eventually contains, at minimum:
- system overview / architecture document
- data flow explanation document
- table/business meaning documentation
- daemon/worker runtime runbook
- archive runbook
- configuration reference
- cold-start setup guide
- troubleshooting guide
- testing/acceptance guide

**How to test**
- docs completeness checklist
- another developer can follow setup/runbook docs without hidden steps
- docs stay aligned with actual commands and schema

### T11. Repo / Git / initialization / reproducibility hardening
**Why needed**
- another developer must be able to clone, initialize, migrate, configure, and run the system clearly
- Trailblazer quality requires reproducible startup and repository hygiene, not just correct code

**Success looks like**
- repo has clean initialization path
- migrations produce the required schema deterministically
- config/bootstrap steps are documented
- no hidden local-only assumptions remain in critical setup path

**How to test**
- cold-start environment test from clean clone
- database initialization test via documented commands only
- one-shot runtime smoke test after fresh setup
- schema/version check after migration

### T12. Repo/runtime hygiene follow-up
**Why needed**
- repository still contains transitional docs and domain-specific runtime duplication

**Success looks like**
- canonical design docs are identified
- deprecated runtime paths are marked or wrapped, not left ambiguous

**How to test**
- repo audit checklist
- docs consistency review
- no ambiguous “which daemon is canonical?” state

---

## 12. Reuse-vs-rewrite decisions and rationale

### 12.1 Reuse

#### Reuse: DB/settings foundation
Reason:
- already stable enough
- low cost to preserve
- important for consistency

#### Reuse: existing lowfreq/midfreq/archive runner/domain logic where sound
Reason:
- data fetch/persistence logic already encodes real source semantics
- throwing it away would slow progress and lose tested behavior

#### Reuse: archive checkpoint/run/summary concepts
Reason:
- archive line already models long-horizon execution more seriously than some other lines

#### Reuse: Alembic chain
Reason:
- migration-managed schema is the right authority model

### 12.2 Rewrite / heavy refactor

#### Rewrite/refactor: daemon layer
Reason:
- lowfreq and midfreq daemon families are too duplicated to remain canonical
- unified daemon is a core target of the new architecture

#### Rewrite/refactor: target resolution interface
Reason:
- Business Layer integration is a new upstream contract
- current target selection model is not adequate

#### Rewrite/refactor: execution/audit surface
Reason:
- current state is fragmented and domain-specific
- production manageability requires a clearer common contract

#### Rewrite/refactor: config topology
Reason:
- code-scattered defaults do not scale to unified runtime + archive policy

---

## 13. Approval gates, deliverable matrix, and testing/acceptance plan

The future work must have explicit gates, deliverables, and acceptance criteria.
The goal is to make implementation auditable and to prevent vague claims of completion.

### 13.1 Approval gates / milestone gates

#### Gate A — Contract and architecture freeze
Before implementation proceeds beyond foundation work, all of the following must be true:
- Business Layer -> Data Platform contract is approved
- normalized target manifest contract is approved
- unified daemon vs worker boundary is approved
- archive membership delta policy is approved
- config model is approved
- schema authority plan is approved

If any of these are still ambiguous, implementation should not be considered ready to scale.

#### Gate B — Foundation readiness
Before runtime unification work is considered ready for execution:
- schema/code parity audit is complete
- implied-missing table gaps are identified and dispositioned
- repo initialization path is documented
- reproducible local environment path exists
- migration path for new runtime/audit artifacts is defined

#### Gate C — Unified runtime first-pass readiness
Before saying the unified runtime foundation is done:
- one canonical daemon entrypoint exists
- worker contract exists
- one-shot lowfreq and one-shot midfreq both work through the new path
- run records and manifest linkage are visible
- old daemon paths are clearly marked as compatibility/transitional where appropriate

#### Gate D — Archive integration readiness
Before archive is considered upgraded enough to proceed:
- archive one-shot runs work through the intended control model
- checkpoint/resume is verified
- membership delta detection is verified
- catch-up creation policy is verified
- backlog priority policy is implemented and testable

#### Gate E — Operational readiness
Before approval for sustained independent running:
- service-mode runtime loop is stable
- run records/logs/state visibility are satisfactory
- another developer can cold-start the system from docs
- profiling outputs exist for core run modes
- runbooks and troubleshooting docs are present

### 13.2 Deliverable matrix

#### Workstream 1: Business Layer selector integration
Expected deliverables:
- code modules/components:
  - target-resolution module(s)
  - manifest data model / serializer
  - lane mapping logic
- DB/schema/init artifacts:
  - manifest snapshot tables if persisted
  - migration(s) or documented deferred decision
- tests:
  - unit tests for manifest resolution
  - selector/mapping tests
- runbooks/docs:
  - contract documentation
  - operator explanation of selector inputs
- profiling outputs:
  - manifest generation timing
- verification evidence:
  - sample manifest output for canonical lists
  - diff/check evidence from live Business Layer data

#### Workstream 2: Unified runtime daemon/worker foundation
Expected deliverables:
- code modules/components:
  - unified daemon entrypoint
  - worker launcher/supervision path
  - worker contract layer
- DB/schema/init artifacts:
  - runtime run/audit state artifacts
- tests:
  - unit tests for dispatch logic
  - integration tests for one-shot execution
  - timeout tests
- runbooks/docs:
  - daemon/worker runbook
  - service vs one-shot usage docs
- profiling outputs:
  - daemon idle overhead
  - worker spawn overhead
- verification evidence:
  - commands run
  - run record screenshots/queries
  - daemon/worker log references

#### Workstream 3: Lowfreq and midfreq execution migration
Expected deliverables:
- code modules/components:
  - lowfreq worker adapter
  - midfreq worker adapter
  - compatibility wrappers or retired paths plan
- DB/schema/init artifacts:
  - any run-state/audit mapping migration
- tests:
  - lowfreq one-shot test
  - midfreq one-shot test
  - service-mode dispatch smoke test
- runbooks/docs:
  - lane-specific execution notes
- profiling outputs:
  - lowfreq one-shot runtime numbers
  - midfreq one-shot runtime numbers
- verification evidence:
  - command transcripts
  - DB run results
  - summary outputs

#### Workstream 4: Archive upgrade and delta handling
Expected deliverables:
- code modules/components:
  - archive target snapshot/delta detector
  - catch-up/backfill planner
  - archive worker execution path
- DB/schema/init artifacts:
  - checkpoint/backlog/catch-up state artifacts as needed
- tests:
  - archive one-shot tests
  - checkpoint resume tests
  - membership addition tests
  - granularity-specific catch-up tests
- runbooks/docs:
  - archive runbook
  - delta handling guide
- profiling outputs:
  - 1-day backfill timing
  - multi-day backfill timing
  - shard throughput notes
- verification evidence:
  - checkpoint rows
  - backlog/catch-up rows or summaries
  - before/after membership diff evidence

#### Workstream 5: Config, reproducibility, and docs closure
Expected deliverables:
- code modules/components:
  - configuration loader cleanup/convergence
- DB/schema/init artifacts:
  - documented bootstrap/init sequence
- tests:
  - cold-start initialization test
  - config precedence tests
- runbooks/docs:
  - config docs
  - cold-start guide
  - troubleshooting guide
  - testing/acceptance guide
- profiling outputs:
  - none required beyond reporting existing measured results
- verification evidence:
  - clean-clone setup transcript
  - migration transcript
  - first successful one-shot run transcript

### 13.3 Unit tests
Must cover:
- target manifest resolution from Business Layer rows
- lane mapping logic
- schedule window matching
- worker timeout handling
- retry/degrade decisions
- archive membership delta detection
- checkpoint progression logic

### 13.4 Integration tests
Must cover:
- lowfreq one-shot worker run
- midfreq one-shot worker run
- archive one-shot run
- daemon dispatch of a matching window into one worker run
- DB persistence of run records and summary results

### 13.5 Manual one-shot daemon runs
Must cover:
- one lowfreq round, manual trigger
- one midfreq round, manual trigger
- one archive backfill step, manual trigger
- one dry-run target resolution execution

### 13.6 Timeout behavior tests
Must cover:
- worker exceeding configured max runtime
- source call timeout bubbling correctly to run status
- daemon marking run as timed out rather than generic failed
- safe retry behavior after timeout

### 13.7 Archive backfill tests
Must cover:
- backfill 1 day for one minute-level target
- backfill multiple days for one daily target
- backfill resume after interruption
- checkpoint correctness after partial run

### 13.8 Archive target membership change tests
Must cover:
- add one new target to archive list
- detect delta
- create catch-up work item or checkpoint row
- execute partial catch-up
- verify not yet complete vs complete state

### 13.9 DB init/schema reproducibility tests
Must cover:
- fresh schema from migrations
- schema parity with code references
- no missing implied tables
- no drift for canonical runtime tables

### 13.10 Operability/logging checks
Must cover:
- run record visibility
- recent failure visibility
- health endpoint/command consistency
- log lines include run IDs and lane/worker context

### 13.11 Hard acceptance criteria for directly runnable quality

The upgraded system should not be considered operationally ready until all of the following are demonstrably true:

#### Runtime lowfreq
- one-shot lowfreq run succeeds through the intended unified path
- produces run records/state/log visibility
- writes expected data/result rows

#### Runtime midfreq
- one-shot midfreq run succeeds through the intended unified path
- produces run records/state/log visibility
- writes expected data/result rows

#### Unified daemon service mode
- service mode starts cleanly
- matches windows correctly
- dispatches workers correctly
- remains observable while running
- leaves intelligible state after worker completion/failure

#### Archive/backfill
- one-shot archive run succeeds for at least one supported archive lane
- checkpoint/resume works
- archive run records and summaries are visible

#### Archive membership-change catch-up
- adding a target to archive membership creates the expected catch-up path
- catch-up can run incrementally
- completion state is visible and auditable

#### Reproducible initialization
- another developer can clone the repo, install dependencies, run migrations, configure the system, and execute a successful one-shot validation path from documentation only

#### Logs / run records / state visibility
- all core run modes produce visible run records
- logs are traceable to run IDs
- daemon state and worker outcomes are easy to inspect

#### Documentation completeness
- handoff-quality docs exist for setup, runtime operation, archive operation, troubleshooting, and test/acceptance execution

### 13.12 Execution evidence expectations

For each major implementation area, completion claims should be backed by explicit evidence.

#### Selector / manifest work
Evidence should include:
- exact commands run
- manifest output sample(s)
- DB selector input snapshot or query result
- tests passed

#### Unified runtime work
Evidence should include:
- exact daemon/worker commands run
- run record query results
- summary output
- timeout/retry demonstration if applicable
- relevant log excerpts or log file references

#### Lowfreq / midfreq migration work
Evidence should include:
- exact one-shot commands
- DB row counts or query outputs showing success
- run summaries
- test output
- profiling numbers

#### Archive work
Evidence should include:
- exact archive commands
- checkpoint query results
- catch-up/backfill state evidence
- archive summary/run evidence
- profiling numbers for sample backfills

#### Config / reproducibility work
Evidence should include:
- clean-clone initialization commands
- migration commands
- health check output
- first one-shot validation output
- docs file paths used

---

## 14. Performance / profiling plan

This upgrade should be designed with measurement in mind, not just correctness.

### 14.1 What should be measured

For each one-shot worker run:
- manifest resolution time
- source fetch time
- persistence time
- total wall-clock runtime
- per-target average time
- failure count / timeout count
- records processed

For daemon/service mode:
- loop overhead when idle
- scheduling latency
- worker spawn overhead
- time from window match -> worker start

For archive:
- records/sec or targets/sec by worker type
- day-range throughput for backfill
- checkpoint update overhead
- catch-up completion rate for newly added targets

### 14.2 Concrete profiling expectations to define later during implementation

The future implementation should report at least:
- approximate runtime of one lowfreq one-shot run
- approximate runtime of one midfreq one-shot run
- approximate runtime of one archive one-shot run by asset type
- minute-level archive backfill profiling for:
  - 1 day
  - multiple days
  - multiple targets

### 14.3 Suggested profiling deliverables

For each implemented worker lane, later work should produce:
- input target count
- records processed
- wall-clock runtime
- bottleneck split (fetch vs DB write vs orchestration)
- resource notes (CPU, memory, source throttling observations)

---

## 15. Documentation deliverables and reproducibility requirements

### 15.1 Documentation deliverables beyond this Trailblazer plan

This Trailblazer plan is the approval-level architecture and execution strategy document.
It is not sufficient by itself to run the platform long term.
The eventual documentation set should include:

1. **System overview**
   - what the platform is
   - which subsystems exist
   - how Business Layer and Data Platform relate

2. **Data flow explanation**
   - Business Layer selector -> target manifest -> daemon -> worker -> persistence -> audit records

3. **Table/business meaning docs**
   - business meaning of each major runtime/archive/current/history/state table
   - ownership boundaries (Business Layer vs Data Platform)

4. **Daemon/worker runbook**
   - how to start/stop service mode
   - how to run one-shot/manual mode
   - how to inspect state and recent runs

5. **Archive runbook**
   - how archive service mode works
   - how one-shot archive catch-up works
   - how checkpoint/resume is interpreted

6. **Configuration docs**
   - config file hierarchy
   - env var contract
   - CLI override contract
   - example dev/test/prod configuration layouts

7. **Cold-start setup guide**
   - clone repo
   - create environment
   - install dependencies
   - configure DB
   - run migrations
   - configure source credentials
   - perform first one-shot validation run

8. **Troubleshooting guide**
   - DB connection issues
   - migration drift
   - timeout failures
   - stale daemon/worker states
   - source credential issues

9. **Testing and acceptance guide**
   - which tests exist
   - how to run unit/integration/manual checks
   - acceptance criteria for runtime/archive upgrades

### 15.2 Repo / Git / initialization / reproducibility expectations

Trailblazer quality requires that another developer be able to:
- clone the repo
- install the environment
- initialize/migrate schema
- configure required credentials and runtime defaults
- run one-shot validation commands
- understand which docs are canonical

Therefore the work plan must include explicit reproducibility requirements:
- no hidden local-only initialization assumptions
- no undocumented required tables
- no silent schema drift
- no ambiguous canonical entrypoint
- no dependence on chat-only knowledge

### 15.3 Initialization expectations for future implementation

The future implementation should make the following operational path explicit and documented:
1. clone repo
2. create virtual environment
3. install project dependencies
4. configure environment file / env vars
5. run Alembic migrations
6. validate DB/schema health
7. run one-shot target resolution / one-shot worker test
8. inspect run record / output / logs

Only when this flow is reproducible should the runtime be considered operationally closed.

---

## 16. Long-running operability review criteria

Short tests are not enough.
Before declaring the upgraded system ready for sustained independent running, the following review should be performed:

- daemon can stay up over repeated loop cycles without losing state coherence
- failed workers do not leave ambiguous or stuck run state
- timeout behavior is intelligible and recoverable
- logs remain traceable and not excessively noisy
- retry/backoff behavior does not create runaway loops
- archive backlog does not starve current work
- newly-added archive targets enter catch-up without manual hidden steps
- health/status surfaces are sufficient for an operator to determine “what is running, what failed, and what needs intervention”
- documentation is sufficient for another developer/operator to restart or validate the system without chat-based tribal knowledge

This review should be treated as a formal readiness check, not an informal confidence statement.

---

## 17. Risks, open questions, and recommended sequencing

### 15.1 Risks

#### Risk: over-reusing duplicated daemon logic
If the team tries too hard to preserve existing daemon families unchanged, the architecture will stay fragmented.

#### Risk: over-rewriting source-specific ingest logic
If the team rewrites too aggressively, it may regress working fetch/persistence paths.

#### Risk: unresolved schema authority
If run/audit tables are added ad hoc without a clear migration strategy, the platform will get harder to operate.

#### Risk: Business Layer integration done too implicitly
If target resolution is hidden in ad hoc SQL inside workers, the platform will lose clarity and auditability.

#### Risk: archive membership changes handled informally
If newly-added archive targets are not given a formal catch-up path, the long-term asset layer will drift silently.

### 15.2 Open questions

1. Should the target manifest be persisted or remain computed-on-demand in the first implementation cut?
2. Should unified runtime use one shared execution table plus lane-specific side tables, or a layered model with a shared parent record?
3. How much of `symbol_universe` remains authoritative vs merely advisory?
4. What exact mapping should tie Business Layer list types to runtime lanes in edge cases (for example theme-specific focus lists used by both lowfreq and midfreq consumers)?
5. Should archive job definitions remain config-driven, DB-driven, or become partly manifest-driven from Business Layer archive sets?

### 15.3 Recommended sequencing

#### Sequence 1: design authority and schema parity
- finalize target-resolution contract
- audit schema/code parity
- resolve missing implied tables

#### Sequence 2: unified runtime foundation
- create real unified daemon/worker contract
- keep existing lowfreq/midfreq runners behind compatibility adapters where possible

#### Sequence 3: Business Layer integration
- connect canonical `default/default` Business Layer lists into target resolution
- prove lowfreq/midfreq one-shot runs against manifest-driven targets

#### Sequence 4: archive membership-delta handling
- add target snapshot/diff logic
- add catch-up/backfill intent handling

#### Sequence 5: observability hardening
- unify run records
- improve health/status tooling
- add profiling/reporting outputs

---

## 18. Final architectural recommendation

The best path forward is:

1. **Do not redesign the Business Layer here.**
2. **Do not keep lowfreq and midfreq as permanent separate daemon architectures.**
3. **Do not collapse archive into “just another normal collection window.”**
4. **Do introduce one real unified runtime daemon plus explicit workers.**
5. **Do make Business Layer the upstream selector of collection targets.**
6. **Do preserve and reuse the strongest existing runner/persistence logic.**
7. **Do formalize run records, target resolution, and archive membership-change handling before broadening implementation.**

This is the cleanest Trailblazer upgrade path because it preserves working substrate value while correcting the main long-term architectural fault line: duplicated runtime lines with insufficiently explicit target-selection and audit contracts.
