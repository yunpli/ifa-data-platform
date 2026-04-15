# Trailblazer Repro Smoke Evidence

_Date: 2026-04-15_

## Goal

Provide a docs-following reproducibility path aligned to Milestone 6 closure requirements.

## Commands

```bash
source .venv/bin/activate
export PYTHONPATH=src
export DATABASE_URL='postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
export IFA_DB_SCHEMA=ifa2
alembic upgrade head
python scripts/runtime_manifest_cli.py manifest --owner-type default --owner-id default
python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default
python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default
python scripts/runtime_manifest_cli.py run-once --lane archive --owner-type default --owner-id default --list-type archive_targets
python scripts/runtime_manifest_cli.py run-status --limit 5
python scripts/runtime_manifest_cli.py archive-status --limit 10
pytest tests/integration/test_unified_runtime.py -q
```

## Expected evidence

- migrations reach head
- manifest generation is non-empty
- unified lowfreq one-shot produces a persisted run row
- unified midfreq one-shot produces a persisted run row
- unified archive one-shot produces a persisted run row
- archive catch-up / checkpoint state is queryable
- integration tests pass

## Evidence fields to retain in final package

- `run_id`
- `lane`
- `manifest_hash`
- `manifest_snapshot_id`
- persisted `summary`
- archive catch-up status summary
- archive checkpoint rows if present
- test output transcript

## Closure note

This is not yet the final clean-clone proof, but it is now a concrete docs-driven local smoke path rather than an implicit engineering-only workflow.
