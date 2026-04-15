# Trailblazer Runtime Runbook

_Date: 2026-04-15_

## Purpose

This runbook is the operator-facing entrypoint for the current Trailblazer implementation state.
It focuses on the approved one-shot proof path and on the current query surfaces needed to inspect runtime evidence.

This document is specifically for:
- unified manifest generation
- one-shot lowfreq / midfreq / archive runs through the unified path
- runtime audit inspection
- archive catch-up / checkpoint visibility
- reproducible local smoke validation

---

## Canonical entrypoints

### Code
- manifest + unified runtime core:
  - `src/ifa_data_platform/runtime/target_manifest.py`
  - `src/ifa_data_platform/runtime/unified_runtime.py`
- CLI:
  - `scripts/runtime_manifest_cli.py`

### DB audit tables
- `ifa2.job_runs`
- `ifa2.unified_runtime_runs`
- `ifa2.target_manifest_snapshots`
- `ifa2.archive_target_catchup`
- `ifa2.archive_checkpoints`
- `ifa2.archive_runs`
- `ifa2.archive_summary_daily`

---

## Environment assumptions

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL='postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
export IFA_DB_SCHEMA=ifa2
export PYTHONPATH=src
```

Apply migrations:

```bash
alembic upgrade head
```

---

## Manifest dry-run

### Runtime selector scope
```bash
python scripts/runtime_manifest_cli.py manifest \
  --owner-type default \
  --owner-id default
```

### Archive selector scope
```bash
python scripts/runtime_manifest_cli.py manifest \
  --owner-type default \
  --owner-id default \
  --list-type archive_targets
```

Expected:
- non-empty `item_count`
- deterministic `manifest_hash`
- lane-mapped items in output payload

---

## One-shot unified runs

### Lowfreq
```bash
python scripts/runtime_manifest_cli.py run-once \
  --lane lowfreq \
  --owner-type default \
  --owner-id default
```

### Midfreq
```bash
python scripts/runtime_manifest_cli.py run-once \
  --lane midfreq \
  --owner-type default \
  --owner-id default
```

Note:
- for clean fresh-clone execution, set `TUSHARE_TOKEN` in the environment or `.env` to avoid adaptor warnings during midfreq dry-run fetch attempts

### Archive
```bash
python scripts/runtime_manifest_cli.py run-once \
  --lane archive \
  --owner-type default \
  --owner-id default \
  --list-type archive_targets
```

Expected summary fields:
- `run_id`
- `manifest_id`
- `manifest_hash`
- `manifest_snapshot_id`
- lane-specific execution summary fields

---

## Runtime audit inspection

### Recent unified runs
```bash
python scripts/runtime_manifest_cli.py run-status --limit 10
```

### Recent unified runs for one lane
```bash
python scripts/runtime_manifest_cli.py run-status --lane archive --limit 10
```

### Single run details
```bash
python scripts/runtime_manifest_cli.py run-status --run-id <uuid>
```

Expected:
- row from `ifa2.unified_runtime_runs`
- persisted `summary` payload
- manifest linkage visible via `manifest_snapshot_id`, `manifest_id`, `manifest_hash`

---

## Archive catch-up / checkpoint inspection

```bash
python scripts/runtime_manifest_cli.py archive-status --limit 20
```

Expected sections:
- `summary_by_status`
- `recent_catchup_rows`
- `recent_checkpoints`
- `recent_archive_runs`

Use this to validate:
- catch-up backlog visibility
- per-row status distribution
- checkpoint state visibility for resumable archive progress
- archive run linkage into catch-up rows via `archive_run_id`
- checkpoint linkage via `checkpoint_dataset_name` / `checkpoint_asset_type`

---

## Reproducible smoke path

Run this sequence from docs only:

```bash
alembic upgrade head
python scripts/runtime_manifest_cli.py manifest --owner-type default --owner-id default
python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default
python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default
python scripts/runtime_manifest_cli.py run-once --lane archive --owner-type default --owner-id default --list-type archive_targets
python scripts/runtime_manifest_cli.py run-status --limit 5
python scripts/runtime_manifest_cli.py archive-status --limit 10
pytest tests/integration/test_unified_runtime.py -q
```

This is the current minimal closure path for:
- migration clarity
- one-shot runtime proof
- audit visibility
- archive state visibility
- test-backed validation

---

## Current milestone mapping

- Milestone 2 advanced by:
  - `ifa2.unified_runtime_runs`
  - queryable unified runtime audit path
- Milestone 3/4 advanced by:
  - lowfreq/midfreq unified one-shot summaries with per-dataset planning/results
- Milestone 5 advanced by:
  - archive catch-up visibility through CLI status surface
  - persisted non-zero archive membership-delta proof with catch-up row insertion / binding / checkpoint linkage / status progression evidence
- Milestone 6 advanced by:
  - reproducible command path in one document
  - canonical operator entrypoints
  - fresh-clone init / migrate / smoke / validation evidence

---

## Not yet closed

Still pending before final Trailblazer closure:
- stronger non-dry-run unified worker execution semantics where appropriate
- final troubleshooting / acceptance docs pack
- final push-state confirmation in the evidence package
