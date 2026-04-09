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

## 5. Runtime demo

Current minimal runtime demo is designed to prove:
- scheduler skeleton exists
- worker skeleton exists
- job state can be written
- health can be queried

Run:
```bash
python scripts/demo_runtime.py
```

Expected behavior:
- dummy job transitions through lifecycle states
- writes into `ifa2.job_runs`
- prints health summary

## 6. Tests

```bash
pytest
```

## 7. What this proves at current stage

A successful run currently proves only the minimum closure needed for the backbone stage:
- database reachable
- migrations applied
- runtime/job loop can write/read state
- schema and code path are aligned

It does **not** yet prove complete iFA 2.0 production readiness.

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

## 10. Known limitations at this phase

- provider integrations are not complete
- Redis integration is reserved but not yet mandatory
- slot/material input serving is still minimal
- report generation and delivery are not yet implemented here
- the runtime demo proves backbone direction, not final production throughput
