# Archive V2 Production Runbook

## Production truth

Archive V2 is now the live nightly production path for daily/final archive truth in:
- code
- dedicated production CLI
- live runtime schedule DB

Current live runtime schedule truth:
- `archive_v2` trading-day nightly row is present and enabled
- active nightly schedule key: `archive_v2:trade_day_nightly_daily_final`
- active nightly cadence: `21:40` Beijing time on trading days
- legacy `archive` seeded rows remain in DB but are disabled
- `runtime_worker_state` now includes an `archive_v2` row

So the correct current statement is:

> Archive V2 is now the real scheduled nightly production archive lane. Legacy `archive` is no longer the active default scheduled path.

Legacy `archive` lane:
- retained for coexistence/manual fallback only
- still present in DB for non-destructive rollback/fallback semantics
- not enabled as the nightly default scheduled lane

Archive V2 nightly lane:
- runtime lane: `archive_v2`
- profile name: `archive_v2_production_nightly_daily_final`
- default scope: implemented daily/final families only
- active automatic cadence: trading-day nightly at `21:40` Beijing time

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
- manual backfill defaults to the primary daily/final Archive V2 truth families only
- current C-class highfreq-derived daily families are no longer part of the primary/default Archive V2 truth model
- targeted holes after nightly runs should normally use operator `repair-batch`, not broad backfill

### 3) Manual/operator repair batches
Use operator CLI only:

```bash
.venv/bin/python scripts/archive_v2_operator_cli.py repair-batch ...
```

Expected trigger source:
- `operator_repair_batch`

## Default nightly scope
Nightly production default scope includes the primary/default Archive V2 truth families only:
- tradable/final daily
- business/event daily/final
- no current C-class highfreq-derived daily families
- no proxy intraday families

For daily/final B-class families where direct source-side truth exists, Archive V2 now uses source-first fetch semantics in the runner instead of treating low/mid/high retained-history tables as the primary upstream truth.

It intentionally excludes:
- all current C-class derived daily families from the primary/default Archive V2 truth model
- proxy pseudo-intraday families from the valid raw family model entirely
- true source-side intraday families from nightly activation by default

Later-enable intraday support remains valid for the true source-side family groups:
- equity `1m / 15m / 60m`
- ETF `1m / 15m / 60m`
- index `1m / 15m / 60m`
- futures `1m / 15m / 60m`
- commodity `1m / 15m / 60m`
- precious_metal `1m / 15m / 60m`

These remain default-OFF unless explicitly enabled by profile/operator intent.

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
