# FSJ P3-4a Live DB Touchpoint Inventory — 2026-04-24

## Scope

Thin landing for roadmap item `P3-4a` from `docs/PRODUCTION_GRADE_A_SHARE_SYSTEM_ROADMAP_2026-04-23.md`:

- roadmap target: **prevent tests from polluting live production truth**
- this slice: inventory current canonical/live DB touchpoints and identify the **first codable isolation seam**
- non-goal: broad hardening refactor across archive/highfreq/lowfreq/midfreq

## Executive verdict

Current FSJ delivery/publish surfaces already have a meaningful pytest-only live-isolation guard:

- `src/ifa_data_platform/fsj/test_live_isolation.py`
- `src/ifa_data_platform/fsj/store.py`
- FSJ publish/send scripts that call `enforce_non_live_test_roots(...)`

That guard materially reduces the highest-risk accidental write path inside FSJ.

The remaining truthful risk is **not zero**:

1. several FSJ read/write entrypoints still instantiate `FSJStore()` implicitly, so their safety depends on the store constructor guard rather than explicit call-site intent
2. outside FSJ, multiple scripts/tests still hardcode `ifa_db` and therefore remain live-truth reachable by default
3. canonical artifact root protection exists for publish flows, but not every DB-backed operator/status path carries explicit test-intent signaling at the call site

## Authoritative roadmap reference

Roadmap section `P3-4. Test/live isolation hardening` states:

- isolate integration test DB from live DB
- isolate fixture writes
- add destructive-test guardrails
- review current tests touching canonical tables

Source: `docs/PRODUCTION_GRADE_A_SHARE_SYSTEM_ROADMAP_2026-04-23.md:440-448`

## Canonical/live truth surfaces proven in repo

### 1) FSJ canonical DB table — write surface

`FSJStore.ensure_schema()` creates canonical artifact tables under schema `ifa2`, including:

- `ifa2.ifa_fsj_report_artifacts`
- `ifa2.ifa_fsj_report_links`
- related FSJ bundle/object/evidence tables

Evidence:

- `src/ifa_data_platform/fsj/store.py:249-274`

The canonical artifact table is the main operator truth surface for report delivery lifecycle and review state.

### 2) FSJ canonical artifact DB writes

`FSJStore.register_report_artifact(...)` performs:

- `UPDATE ifa2.ifa_fsj_report_artifacts ... status='superseded'`
- `INSERT INTO ifa2.ifa_fsj_report_artifacts ...`
- upsert into `metadata_json`

Evidence:

- `src/ifa_data_platform/fsj/store.py:648-717`

`FSJStore.persist_report_workflow_linkage(...)` updates `metadata_json` on the same canonical table.

Evidence:

- `src/ifa_data_platform/fsj/store.py:2799-2849`

`FSJStore.persist_report_dispatch_receipt(...)` updates the same canonical artifact row with dispatch receipt truth.

Evidence:

- `src/ifa_data_platform/fsj/store.py:2851-2897`

### 3) FSJ canonical artifact filesystem root — live-ish truth surface

FSJ delivery publishers write delivery manifests/packages under the canonical repo artifact root unless an explicit non-live root is supplied.

Evidence:

- canonical artifact root constant: `src/ifa_data_platform/fsj/test_live_isolation.py:10`
- main package publish writes manifest/zip + registers artifact: `src/ifa_data_platform/fsj/report_rendering.py:571-769`
- support package publish writes manifest/zip: `src/ifa_data_platform/fsj/report_rendering.py:1169-1305`

These filesystem artifacts are not the DB of record, but they are operator-visible truth inputs and therefore should be treated as **live-ish truth surfaces**.

## Existing guardrails already landed

### Guard 1 — explicit non-live DB required under pytest

`require_explicit_non_live_database_url(...)` blocks under pytest when:

- `DATABASE_URL` is absent
- `DATABASE_URL == postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp`

Evidence:

- `src/ifa_data_platform/fsj/test_live_isolation.py:24-43`

`FSJStore.__init__(...)` calls that guard before creating its engine.

Evidence:

- `src/ifa_data_platform/fsj/store.py:311-317`

### Guard 2 — explicit non-live artifact root required under pytest for publish flows

`require_explicit_non_live_artifact_root(...)` and `enforce_non_live_test_roots(...)` block when artifact output resolves inside repo canonical artifact root.

Evidence:

- `src/ifa_data_platform/fsj/test_live_isolation.py:55-105`

### Guard 3 — key FSJ CLI publish paths call guard explicitly

Protected pytest-facing scripts include:

- `scripts/fsj_main_report_publish.py:50`
- `scripts/fsj_main_report_morning_delivery.py:80`
- `scripts/fsj_support_report_publish.py:59`
- `scripts/fsj_support_batch_publish.py:107`
- `scripts/fsj_support_bundle_persist.py:60`
- `scripts/fsj_main_early_publish.py:46`
- `scripts/fsj_main_late_publish.py:46`

## Current touchpoint inventory

### A. FSJ touchpoints that can touch canonical/live DB or live-ish truth

| touchpoint | proof | surface | risk | current control | note |
|---|---|---|---|---|---|
| `FSJStore()` constructor | `src/ifa_data_platform/fsj/store.py:311-317` | DB engine acquisition | High | pytest blocks missing/live `DATABASE_URL` | core gate; all implicit default-store paths depend on this |
| `FSJStore.register_report_artifact(...)` | `src/ifa_data_platform/fsj/store.py:648-717` | `ifa2.ifa_fsj_report_artifacts` write | High | only safe if store guard already enforced | canonical write path |
| `FSJStore.persist_report_workflow_linkage(...)` | `src/ifa_data_platform/fsj/store.py:2799-2849` | `ifa2.ifa_fsj_report_artifacts.metadata_json` update | High | same as above | mutates operator truth after publish |
| `FSJStore.persist_report_dispatch_receipt(...)` | `src/ifa_data_platform/fsj/store.py:2851-2897` | `ifa2.ifa_fsj_report_artifacts.metadata_json` update | High | same as above | mutates dispatch truth |
| main delivery publisher | `src/ifa_data_platform/fsj/report_rendering.py:571-769` | artifact files + DB registration | High | explicit non-live artifact root under pytest | dual surface: FS + DB |
| support delivery publisher | `src/ifa_data_platform/fsj/report_rendering.py:1169-1305` | artifact files + DB registration | High | explicit non-live artifact root under pytest | dual surface: FS + DB |
| morning/main/support publish scripts | script refs above | CLI entrypoints that construct store/publisher | High | `enforce_non_live_test_roots(...)` | caller-visible barrier already exists |
| operator/status/read helpers using default `FSJStore()` | `src/ifa_data_platform/fsj/report_dispatch.py:129,146`; `scripts/fsj_main_delivery_status.py:36,59`; `scripts/fsj_support_delivery_status.py:38,61`; `scripts/fsj_operator_board.py:29,35,42,69,91`; `scripts/fsj_send_dispatch_failure_status.py:275`; `scripts/fsj_support_dispatch_failure_status.py:126`; `src/ifa_data_platform/fsj/report_sender.py:169` | DB read surfaces; some sender paths later persist receipts | Medium to High | indirect via `FSJStore()` constructor guard | safe today in pytest, but call-site intent is implicit |
| producer classes defaulting to `FSJStore()` | `src/ifa_data_platform/fsj/early_main_producer.py:782`; `mid_main_producer.py:962`; `late_main_producer.py:1032`; `ai_tech_support_producer.py:719,733`; `macro_support_producer.py:692,706`; `commodities_support_producer.py:346,359` | DB-backed runtime surfaces | Medium | indirect via `FSJStore()` constructor guard | integration tests pass explicit test DB; production paths remain default-live by design |

### B. Tests proven safe within the FSJ seam

Integration tests that explicitly route to test DB:

- `tests/integration/test_fsj_main_early_producer_integration.py:15-20,78`
- `tests/integration/test_fsj_main_mid_producer_integration.py:15-20,88`
- `tests/integration/test_fsj_main_late_producer_integration.py:15-20,96`
- `tests/integration/test_ai_tech_support_producer_integration.py:20-25,107-108`
- `tests/integration/test_commodities_support_producer_integration.py:16-21,103-104`
- `tests/integration/test_macro_support_producer_integration.py:17-22,104-105`
- `tests/integration/test_fsj_phase1.py` uses explicit `DB_URL` test store construction at multiple points

Unit tests proving the guard exists today:

- `tests/unit/test_fsj_store_live_isolation.py:18-40`
- publish-script guard tests in:
  - `tests/unit/test_fsj_main_report_publish_script.py:112-130`
  - `tests/unit/test_fsj_support_report_publish_script.py:188-208`
  - `tests/unit/test_fsj_support_batch_publish_script.py:218-237`
  - `tests/unit/test_fsj_main_early_publish_script.py:180-197`
  - `tests/unit/test_fsj_main_late_publish_script.py:180-197`
  - `tests/unit/test_fsj_support_bundle_persist_script.py:122-138`

### C. Adjacent repo-level live DB risks outside FSJ

The repo still contains many direct hardcoded live DB entrypoints outside the current FSJ guard envelope, for example:

- `scripts/archive_real_run_snapshot.py:8-9`
- `scripts/check_archive_and_commodity_lists.py:7-8`
- `scripts/runtime_preflight.py:14`
- `scripts/runtime_24h_report.py:9`
- `scripts/archive_preprod_cleanup.py:12`
- `src/ifa_data_platform/archive_v2/db.py:5`
- multiple integration tests in `tests/integration/` still bind directly to `ifa_db`

This is out of scope for the current thin landing but is important context: **FSJ is partially hardened; repo-wide live/test isolation is not yet uniformly hardened.**

## Risk classification

### High risk

Conditions that can mutate canonical operator truth or canonical artifact outputs:

- `FSJStore.register_report_artifact(...)`
- `FSJStore.persist_report_workflow_linkage(...)`
- `FSJStore.persist_report_dispatch_receipt(...)`
- publish flows that emit under canonical artifact root and then register DB artifacts

### Medium risk

Conditions that do not necessarily write immediately but can resolve canonical truth by default and are one step away from write paths:

- helper classes/scripts using `store = store or FSJStore()`
- producers defaulting to `FSJStore()` rather than explicit injected store

### Low risk

Tests already pinned to explicit `ifa_test` URLs and pure unit tests using stub stores.

## First codable isolation seam

### Recommended next step (smallest safe production-grade seam)

**Codify and test that every FSJ helper/CLI path that falls back to `FSJStore()` remains blocked under pytest unless a non-live DB is explicit.**

Why this is the first seam:

1. it is already compatible with current architecture
2. it leverages the guard that already exists instead of inventing a new isolation model
3. it closes the “implicit default store” gap at operator/helper entrypoints without broad refactor
4. it is testable with narrow unit coverage and no production behavior change outside pytest

### Concrete first implementation target

Add/retain narrow tests around default-store helper entrypoints such as:

- `MainReportDeliveryDispatchHelper.load_active_published_candidate(...)`
- `MainReportDeliveryDispatchHelper.list_db_delivery_candidates(...)`
- one operator/status script path that constructs `FSJStore()` implicitly

Expected behavior under pytest:

- missing `DATABASE_URL` ⇒ fail fast
- canonical/live `DATABASE_URL` ⇒ fail fast
- explicit non-live/test `DATABASE_URL` ⇒ allowed

This is the smallest codable seam because it converts today’s indirect safety assumption into explicit regression coverage without reopening publisher/orchestrator design.

## Commands used for this inventory

```bash
rg -n "P3-4a|P3-4|live|canonical|isolation|test/live|production|DB" docs/PRODUCTION_GRADE_A_SHARE_SYSTEM_ROADMAP_2026-04-23.md tests src scripts

rg -n "sqlite|duckdb|postgres|mysql|database|db_path|knowledge.sqlite|connect\(|create_engine|sqlalchemy|sqlite3|to_sql|read_sql|INSERT INTO|UPDATE .* FROM|DELETE FROM|workflow_handoff|report_artifact|unified_runtime_runs|canonical|live" src/ifa_data_platform/fsj tests scripts /Users/neoclaw/repos/ifa-business-layer

rg -n "ifa_db\?host=/tmp|DATABASE_URL', 'postgresql\+psycopg2://neoclaw@/ifa_db\?host=/tmp|create_engine\(DB_URL\)|DB_URL = 'postgresql\+psycopg2://neoclaw@/ifa_db\?host=/tmp" scripts src tests
```

## Truthful close status for P3-4a slice

- inventory: **done for FSJ seam, with adjacent repo risk called out**
- first codable isolation seam: **identified**
- broad implementation across archive/highfreq/lowfreq/midfreq: **not started in this slice**
- roadmap item P3-4 overall: **still open risk**
