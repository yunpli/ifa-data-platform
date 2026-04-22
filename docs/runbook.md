# Runbook

## 1. Purpose

This runbook covers the current minimum-operational workflow for the backend skeleton supporting **iFA 2.0**.

At the current phase, the repository is not the complete product system. It is the minimum runnable backend foundation that should already be:
- startable
- inspectable
- migratable
- testable
- minimally debuggable

## 2. Prerequisites

- Python 3.11+
- PostgreSQL reachable for `ifa_db`
- local ability to create/use schema `ifa2`
- virtual environment support

## 3. Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## 4. Database setup

Current DB target is the existing `ifa_db` database with a new `ifa2` schema.

### Run migrations
```bash
alembic upgrade head
```

### Check whether schema exists
```bash
python - <<'PY'
from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp', future=True)
with engine.begin() as conn:
    print(conn.execute(text("select schema_name from information_schema.schemata where schema_name='ifa2'" )).fetchall())
PY
```

### Check whether core tables exist
```bash
python - <<'PY'
from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp', future=True)
with engine.begin() as conn:
    print(conn.execute(text("select table_name from information_schema.tables where table_schema='ifa2' order by table_name")).fetchall())
PY
```

## 5. Official runtime entry

The official long-running production-style runtime entry is now:

```bash
python -m ifa_data_platform.runtime.unified_daemon --loop
```

One-shot evaluation / operator inspection:
```bash
python -m ifa_data_platform.runtime.unified_daemon --once
python -m ifa_data_platform.runtime.unified_daemon --status
```

Manual per-worker execution through the unified daemon:
```bash
python -m ifa_data_platform.runtime.unified_daemon --worker lowfreq --runtime-budget-sec 1800
python -m ifa_data_platform.runtime.unified_daemon --worker midfreq --runtime-budget-sec 1800
python -m ifa_data_platform.runtime.unified_daemon --worker highfreq --runtime-budget-sec 900
python -m ifa_data_platform.runtime.unified_daemon --worker archive --runtime-budget-sec 3600
```

### Trade calendar operational policy

`trade_cal` normal maintenance is now owned by the lowfreq worker itself.

1. **Automatic lowfreq gate**
- every normal lowfreq worker start checks `ifa2.trade_calendar_sync_state`
- if the last successful trade-calendar sync is older than ~1 month (31 days), lowfreq refreshes `trade_cal` first
- otherwise lowfreq skips calendar maintenance and continues with the regular lowfreq dataset batch

2. **Manual exact-range repair/backfill**
```bash
python scripts/trade_calendar_maintenance.py sync \
  --start-date 2026-01-01 \
  --end-date 2026-12-31
```
This remains the operator path for targeted repair/backfill and promotes the refreshed version by default.

3. **Optional explicit monthly maintenance trigger**
```bash
python scripts/runtime_manifest_cli.py run-once \
  --lane lowfreq \
  --trigger-mode trade_calendar_monthly_maintenance \
  --owner-type default --owner-id default
```
This still executes only `trade_cal` through the normal lowfreq runner/version path when an operator wants a dedicated maintenance run.

4. **Preflight check without auto-sync**
```bash
python scripts/trade_calendar_maintenance.py health-check
python scripts/runtime_preflight.py --out artifacts/service/runtime_preflight_latest.json
```
The preflight path validates calendar coverage/version freshness for runtime/archive consumers but never auto-syncs the calendar.

Optional bounded validation mode:
```bash
python -m ifa_data_platform.runtime.unified_daemon --worker highfreq --dry-run-manifest-only
```

### Important runtime truth
- `lowfreq.daemon`, `midfreq.daemon`, and `highfreq.daemon` still exist, but their long-running `--loop` path is no longer the official production runtime model.
- They are compatibility/manual wrappers and should not be treated as equal alternatives to the unified daemon.

## 6. Tests

```bash
pytest
```

## 7. What this proves at current stage

A successful unified-daemon run proves:
- database reachable
- migrations applied
- unified schedule/runtime state path is aligned with code
- centralized run evidence can be written to `ifa2.unified_runtime_runs`
- centralized worker state can be written to `ifa2.runtime_worker_state`
- worker execution can be dispatched through one official runtime entry
- scheduled slot-support runs can auto-persist replay evidence into `ifa2.slot_replay_evidence` / `ifa2.slot_replay_evidence_runs`

### Runtime slot replay auto-capture

For recognized scheduled report-support windows, the unified daemon now auto-captures slot replay evidence **after** the runtime row has been finalized, so the evidence reflects the completed execution state rather than a speculative pre-run snapshot.

Current rules:
- only `scheduled` unified-daemon runs participate
- only `lowfreq`, `midfreq`, `highfreq`, and `archive_v2` are eligible
- non-slot/manual/overlap-marker runs are ignored to avoid noisy evidence spam
- report artifact metadata stays on the existing placeholder contract when no real artifact path exists yet at execution time
- perspective is derived from the scheduled Beijing clock time:
  - `observed` = the scheduled support window lands by the slot cutoff
  - `corrected` = the same slot is refreshed after its observed cutoff

Slot families currently inferred from schedule time:
- `<= 09:30` → `early`
- `09:31 .. 13:30` → `mid`
- `> 13:30` → `late`

It still does **not** by itself prove complete iFA 2.0 production readiness; coverage truth, Business Layer scope truth, source limitations, and archive/backfill depth must also be interpreted correctly.

## 8. When a run fails

Check in this order:
1. virtualenv and dependency install
2. database connectivity
3. schema migration status
4. recent `job_runs` write/read path
5. stack trace / stderr from demo or worker entrypoint

## 9. Common current-stage issues

### PostgreSQL connection mismatch
Symptoms:
- alembic cannot connect
- migration fails before first table creation

Likely cause:
- local DSN or socket path not aligned with actual `ifa_db`

### Migration/runtime race
Symptoms:
- migration succeeds or is still running, but demo immediately errors on missing tables

Likely cause:
- demo started before migration finished when run in parallel

### Migration mismatch
Symptoms:
- schema exists but tables do not
- alembic history and actual DB diverge

Likely cause:
- early manual schema work before stable migration flow

### Dependency gap
Symptoms:
- demo/runtime imports fail

Likely cause:
- venv missing packages from `pyproject.toml`

## 10. Tushare setup (China-market low-frequency acquisition)

### 1. Obtain Tushare token

Register at https://tushare.pro and obtain your API token from the user dashboard.

### 2. Configure token

Add to your `.env` file:
```bash
TUSHARE_TOKEN=your_token_here
```

Or set as environment variable:
```bash
export TUSHARE_TOKEN=your_token_here
```

### 3. Test Tushare connection

Run the smoke test:
```bash
python3 - <<'PY'
import os
os.environ['TUSHARE_TOKEN'] = 'your_token_here'
from ifa_data_platform.tushare import get_tushare_client
client = get_tushare_client()
result = client.query('stock_basic', {'list_status': 'L', 'fields': 'ts_code,symbol'})
print(f'Tushare connection OK, returned {len(result)} records')
PY
```

Expected: Returns list of active stocks.

### 4. Error handling

If token is missing, raises `TushareTokenMissingError` with clear message.

## 11. Running tests

```bash
# Run all unit tests
pytest tests/unit/

# Run with integration tests (requires DB, Tushare token)
pytest tests/ -m "not integration"

# Run only integration tests
pytest tests/ -m integration
```

## 12. Known limitations at this phase

- provider integrations are not complete
- some runtime summary tables are not yet fully trustworthy as operator evidence surfaces on their own (`midfreq_execution_summary` / `highfreq_execution_summary` may not materialize rows even when runtime reports them in `tables_updated`)
- slot/material input serving is still minimal
- report generation and delivery are not yet implemented here
- Business Layer scope is still incomplete for some asset/theme classes (for example commodity / precious_metal focus-style lists are not yet seeded)
- archive backfill depth is uneven by category/frequency
- acceptance-run data should not be mistaken for final production baseline data
