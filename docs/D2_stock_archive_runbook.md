# D2 Stock Archive Runbook

**Date:** 2026-04-13

## Overview

This runbook covers operations for the D2 stock daily historical archive layer.

## Running the Archive

### Manual Execution

```bash
# From project root
source .venv/bin/activate
python -m ifa_data_platform.archive.daemon --once

# Or via orchestrator
python -c "
from ifa_data_platform.archive.archive_config import get_archive_config
from ifa_data_platform.archive.archive_orchestrator import ArchiveOrchestrator

config = get_archive_config()
orch = ArchiveOrchestrator(config)
result = orch.run_window('night_window_1')
"
```

### Configuration

Default config in `archive_config.py`:
- Window: night_window_1 (21:30-22:30 Shanghai)
- Job: stock_daily_archive
- Universe: Top 20 active stocks (configurable in `stock_daily_archiver.py`)

## Monitoring

### Check Health Status

```bash
python -c "
from ifa_data_platform.archive.archive_config import get_archive_config
from ifa_data_platform.archive.archive_health import get_archive_health, check_archive_watchdog

config = get_archive_config()
health = get_archive_health(config)
print(f'Status: {health.status}')
print(f'checkpoint_advanced: {health.checkpoint_advanced}')

watchdog = check_archive_watchdog(config)
print(f'Watchdog: {watchdog.message}')
"
```

### Check Database Tables

```sql
-- Check stock archive data
SELECT COUNT(*) FROM ifa2.stock_daily_history;
SELECT ts_code, trade_date, close, pct_chg 
FROM ifa2.stock_daily_history 
ORDER BY trade_date DESC LIMIT 10;

-- Check checkpoints
SELECT * FROM ifa2.stock_history_checkpoint;

-- Check archive runs
SELECT job_name, status, records_processed, started_at 
FROM ifa2.archive_runs 
ORDER BY started_at DESC LIMIT 5;
```

## Checkpoint/Resume

Checkpoint tracks:
- `dataset_name`: stock_daily
- `last_completed_date`: Last date archived
- `last_ts_code`: Last stock processed
- `batch_no`: Number of stocks processed
- `status`: in_progress or completed

Resume behavior:
- If checkpoint exists, skips stocks already processed
- Checks `last_recorded_date` per stock before re-fetching
- Idempotent writes (no duplicates on re-run)

## Troubleshooting

### No data fetched
1. Check Tushare token: `.env` file should have `TUSHARE_TOKEN`
2. Check stock universe: `SELECT * FROM ifa2.symbol_universe LIMIT 5`

### Resume not working
1. Check checkpoint: `SELECT * FROM ifa2.stock_history_checkpoint`
2. Manually reset: `UPDATE ifa2.stock_history_checkpoint SET status='pending' WHERE dataset_name='stock_daily'`

### Health shows stale
- Archive daemon should run in nightly window
- Last run time tracked in `archive_daemon_state`

## Configuration Files

- `src/ifa_data_platform/archive/archive_config.py` - Job config
- `src/ifa_data_platform/archive/stock_daily_archiver.py` - Stock archiver settings
- `alembic/versions/018_stock_daily_history.py` - Table schema

## Maintenance

To rebuild from scratch:
```sql
-- Clear stock archive data
DELETE FROM ifa2.stock_daily_history;

-- Reset checkpoint
DELETE FROM ifa2.stock_history_checkpoint WHERE dataset_name='stock_daily';
```