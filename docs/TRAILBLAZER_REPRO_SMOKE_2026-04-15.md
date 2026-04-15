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

## Final clean-clone validation evidence

A real clean-clone validation was executed from a freshly cloned repo at:
- `/tmp/ifa-data-platform-cleanclone`

Executed sequence:

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

Observed clean-clone outcome:
- install succeeded in fresh clone
- migrations succeeded
- lowfreq one-shot succeeded
- midfreq one-shot completed in dry-run mode and persisted summary output
- archive one-shot succeeded
- `run-status` and `archive-status` returned expected output structures
- integration tests passed: `11 passed in 16.08s`

Important reproducibility caveat discovered during clean-clone execution:
- midfreq adaptor emitted warnings when `TUSHARE_TOKEN` was not configured in the fresh clone environment
- the dry-run path still completed and produced persisted runtime evidence, but a fully provisioned developer environment should set `TUSHARE_TOKEN` to avoid degraded adaptor warnings

## Final closure note

This document reflects the frozen final review state after the successful main-line push.

Final-state markers:
- final closure commit: `72d2def`
- push to `origin/main` succeeded
- no further implementation work is continuing right now

This remains a real clean-clone / init / migrate / smoke / validation evidence artifact, with one explicit environment caveat recorded: fresh-clone midfreq runs are materially cleaner when `TUSHARE_TOKEN` is configured.
