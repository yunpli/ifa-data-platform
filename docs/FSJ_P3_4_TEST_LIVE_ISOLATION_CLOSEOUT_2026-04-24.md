# FSJ P3-4 Test/Live Isolation Closeout — 2026-04-24

## Scope

This is the closeout proof for roadmap item `P3-4` at the current roadmap scope defined in:

- `docs/PRODUCTION_GRADE_A_SHARE_SYSTEM_ROADMAP_2026-04-23.md`

Scope is intentionally narrow:
- prove whether the current FSJ seam is materially hardened against pytest-time live-truth pollution
- do not claim repo-wide isolation across unrelated archive/highfreq/lowfreq/midfreq surfaces

## Verdict

`P3-4` is **materially closed for current roadmap scope** at the FSJ seam.

No new production code seam was required for honest closeout.
The remaining gap was roadmap/document truth, not missing FSJ guard behavior.

## What is already enforced

### 1) Explicit non-live DB is required under pytest

`src/ifa_data_platform/fsj/test_live_isolation.py` defines:
- canonical/live DB constant: `postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp`
- `require_explicit_non_live_database_url(...)`
- pytest-time failure when:
  - `DATABASE_URL` is absent
  - `DATABASE_URL` points at canonical/live DB

`src/ifa_data_platform/fsj/store.py` calls that guard in `FSJStore.__init__(...)` before engine creation.

This means any FSJ path that falls back to default `FSJStore()` is blocked under pytest unless a non-live DB is explicit.

### 2) Explicit non-live artifact root is required for publish flows under pytest

`src/ifa_data_platform/fsj/test_live_isolation.py` also defines:
- `require_explicit_non_live_artifact_root(...)`
- `enforce_non_live_test_roots(...)`
- `enforce_artifact_publish_root_contract(...)`

These block publish flows when artifact output resolves inside the canonical repo artifact root.

### 3) Default-store operator/helper/status paths are now regression-pinned

The earlier `P3-4a` inventory identified the main residual risk as implicit `FSJStore()` fallback at helper/status/operator entrypoints.

That seam is now explicitly covered by pytest regression tests in all of the current canonical FSJ operator paths that matter for roadmap-close scope:

- `tests/unit/test_fsj_report_dispatch.py`
  - default-store helper entrypoints fail fast with missing/live `DATABASE_URL`
- `tests/unit/test_fsj_main_delivery_status_script.py`
  - main status default-store entrypoints fail fast with missing/live `DATABASE_URL`
- `tests/unit/test_fsj_support_delivery_status_script.py`
  - support status default-store entrypoints fail fast with missing/live `DATABASE_URL`
- `tests/unit/test_fsj_operator_board_script.py`
  - canonical board payload default-store path fails fast with missing/live `DATABASE_URL`
- `tests/unit/test_fsj_support_dispatch_failure_status_script.py`
  - support dispatch-failure path fails fast with missing/live `DATABASE_URL`

### 4) Store-level and publish-root guardrails are also directly tested

- `tests/unit/test_fsj_store_live_isolation.py`
- `tests/unit/test_fsj_report_rendering.py`
- publish-script guard tests already referenced from `docs/FSJ_P3_4A_LIVE_DB_TOUCHPOINT_INVENTORY_2026-04-24.md`

## Evidence map

### Guard implementation
- `src/ifa_data_platform/fsj/test_live_isolation.py`
- `src/ifa_data_platform/fsj/store.py`

### Inventory / touchpoint review
- `docs/FSJ_P3_4A_LIVE_DB_TOUCHPOINT_INVENTORY_2026-04-24.md`

### Explicit regression coverage
- `tests/unit/test_fsj_store_live_isolation.py`
- `tests/unit/test_fsj_report_dispatch.py`
- `tests/unit/test_fsj_main_delivery_status_script.py`
- `tests/unit/test_fsj_support_delivery_status_script.py`
- `tests/unit/test_fsj_operator_board_script.py`
- `tests/unit/test_fsj_support_dispatch_failure_status_script.py`
- `tests/unit/test_fsj_report_rendering.py`

## Exact roadmap claims now justified

At current scope, the following roadmap asks are satisfied inside the FSJ seam:

1. **isolate integration test DB from live DB**
   - satisfied by pytest-time explicit non-live `DATABASE_URL` enforcement in `FSJStore`
2. **isolate fixture writes**
   - satisfied for canonical FSJ publish flows by explicit non-live artifact-root enforcement
3. **add destructive-test guardrails**
   - satisfied for default-store helper/status/operator entrypoints and FSJ publish/store paths under pytest
4. **review current tests touching canonical tables**
   - satisfied by the P3-4a inventory with canonical touchpoint classification and evidence references

## What is intentionally not claimed

This closeout does **not** claim repo-wide isolation hardening outside the current FSJ seam.

Still out of scope for this closure:
- archive/highfreq/lowfreq/midfreq scripts that hardcode live DB paths
- repo-wide CI/lint policy for destructive DB usage
- broad refactor of all non-FSJ scripts to adopt the same contract

Those are valid future hardening tasks, but they are **optional expansion** relative to the current roadmap-close seam.

## Close status

- `P3-4a` inventory: done
- first codable helper/status/operator guard seam: already landed and covered
- current closeout result: **`P3-4` materially closed for current roadmap scope**
