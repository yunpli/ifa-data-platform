# Archive V2 Production Runbook

## Production truth

Archive V2 is now the intended nightly production path for daily/final archive truth.

Legacy `archive` lane:
- retained for coexistence/manual fallback only
- not the default nightly production path anymore

Archive V2 nightly lane:
- runtime lane: `archive_v2`
- profile name: `archive_v2_production_nightly_daily_final`
- default scope: implemented daily/final families only
- automatic cadence: trading-day nightly run

## Paths

### 1) Automatic nightly production
Preferred production entrypoints:

```bash
.venv/bin/python scripts/archive_v2_production_cli.py nightly --business-date YYYY-MM-DD
```

or through unified runtime:

```bash
.venv/bin/python scripts/runtime_manifest_cli.py run-once --lane archive_v2 --owner-type default --owner-id default
```

Expected trigger sources:
- `production_nightly_archive_v2` when running via production CLI
- `runtime_archive_v2_nightly` when running via unified runtime lane

### 2) Manual bounded backfill / replay
```bash
.venv/bin/python scripts/archive_v2_production_cli.py backfill --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

or bounded backfill window:

```bash
.venv/bin/python scripts/archive_v2_production_cli.py backfill --backfill-days 3 --end-date YYYY-MM-DD
```

Expected trigger source:
- `manual_archive_v2_backfill`

Operational note:
- manual backfill defaults to retained-history-backed daily/final families
- nightly production remains the path for full steady-state daily truth generation
- targeted holes after nightly runs should normally use operator `repair-batch`, not broad backfill

### 3) Manual/operator repair batches
Use operator CLI only:

```bash
.venv/bin/python scripts/archive_v2_operator_cli.py repair-batch ...
```

Expected trigger source:
- `operator_repair_batch`

## Default nightly scope
Nightly production default scope includes implemented daily/final families:
- tradable/final daily
- business/event daily/final
- selected highfreq finalized daily families

It intentionally excludes non-actionable/placeholder families from the nightly production path.

## How to verify nightly success

### Archive V2 run evidence
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py recent-runs --limit 10
```

### Unified runtime run evidence
```bash
.venv/bin/python scripts/runtime_manifest_cli.py run-status --lane archive_v2 --limit 10
```

### Completeness / backlog inspection
```bash
.venv/bin/python scripts/archive_v2_operator_cli.py summary --days 14 --limit 10
.venv/bin/python scripts/archive_v2_operator_cli.py gaps --days 14
.venv/bin/python scripts/archive_v2_operator_cli.py actionable-backlog --limit 20
.venv/bin/python scripts/archive_v2_operator_cli.py claimed-backlog --limit 20
.venv/bin/python scripts/archive_v2_operator_cli.py suppressed-backlog --limit 20
```

## Legacy path supersession truth
- Nightly production truth path: `archive_v2`
- Legacy `archive` path: coexistence/manual fallback only for now
- No destructive migration or old-table deletion in this step

## Current limitations
- claim/lease model is first-pass, not full multi-worker orchestration
- repair remains operator/manual unless future automation is explicitly added
- 60m / 15m / 1m are still not the main production scope here
