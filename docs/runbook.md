# Runbook

## 1. Purpose

This runbook covers the current minimum-operational workflow for the IFA Data Platform skeleton.

At this stage the system is still early, but the repository should already be:
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

Current intended DB target is the existing `ifa_db` database with a new `ifa2` schema.

### Run migrations
```bash
alembic upgrade head
```

### Check whether schema exists
```bash
psql -h /tmp -p 5432 -U neoclaw -d ifa_db -c "select schema_name from information_schema.schemata where schema_name='ifa2';"
```

### Check whether core tables exist
```bash
psql -h /tmp -p 5432 -U neoclaw -d ifa_db -c "select table_name from information_schema.tables where table_schema='ifa2' order by table_name;"
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

## 7. Health checks

At the current stage, health means:
- database reachable
- migrations applied
- worker/scheduler demo runnable
- recent `job_runs` rows are writable/readable

## 8. When a job fails

Check in this order:
1. virtualenv and dependency install
2. database connectivity
3. schema migration status
4. recent `job_runs` rows
5. stack trace / stderr from demo or worker entrypoint

## 9. Common current-stage issues

### PostgreSQL connection mismatch
Symptoms:
- alembic cannot connect
- migration fails before first table creation

Likely cause:
- local DSN or socket path not aligned with actual `ifa_db`

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
- slot query is contract-first, not yet full production serving
- object store/raw payload archive is future-facing, not fully implemented
- the runtime demo proves architecture direction, not final production throughput
