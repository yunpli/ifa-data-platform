# Trailblazer Repro Smoke Evidence

> **Canonical current-state status:** Canonical current-state document. Refreshed against current HEAD sanity evidence after doc normalization. Use this as the current repro/smoke reference, not older intermediate batch docs.
> **Final accepted truth refresh:** final repro/smoke truth is now the unified manual acceptance batch at current HEAD: lowfreq succeeded across the widened 19-dataset scope, midfreq succeeded across the widened 12-dataset scope, archive succeeded across the corrected 13-job supported scope.


> **Current truth snapshot:** current HEAD sanity passes showed lowfreq real-run success, midfreq real-run success, archive real-run success for the corrected supported scope. Any residual non-green operator surface is currently from stale macro intraday archive backlog rows, not from active supported-path execution failure.

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

This document reflects the frozen final review state for the accepted **readiness-gap closure phase**.

Final-state markers:
- archive / lowfreq / midfreq phase judgments are frozen for review
- no further implementation expansion is continuing right now
- highfreq remains explicitly deferred

This remains a real clean-clone / init / migrate / smoke / validation evidence artifact, with explicit caveats recorded:
- fresh-clone midfreq runs are materially cleaner when `TUSHARE_TOKEN` is configured
- clean-clone repro should not be overstated as proof of unresolved broader midfreq configured-set schema completeness
