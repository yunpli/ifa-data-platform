# D1 Archive Layer Framework Report

**Date**: 2026-04-13
**Status**: Complete

## 1. What Framework Was Built

D1 implements the Archive Layer framework - a separate line for long-term asset accumulation and backfill. This is NOT for same-day report production and must NOT compete with lowfreq/midfreq production windows.

### Core Components

| Component | File | Description |
|-----------|------|-------------|
| Config | `archive_config.py` | Night window configuration |
| Daemon | `archive_daemon.py` | Main entrypoint |
| Orchestrator | `archive_orchestrator.py` | Job execution orchestration |
| Health | `archive_health.py` | Health monitoring + watchdog |
| Checkpoint | `archive_checkpoint.py` | Resume capability |
| Summary | `archive_summary.py` | Daily summary persistence |
| Job Store | `archive_job_store.py` | Job definition persistence |
| Run Store | `archive_run_store.py` | Run state persistence |
| Daemon State | `archive_daemon_state.py` | Daemon state persistence |
| Models | `models.py` | Data models |

## 2. Tables Created

All tables are in schema `ifa2`:

### archive_jobs
- `id` (UUID, PK)
- `job_name` (VARCHAR, UNIQUE)
- `dataset_name` (VARCHAR)
- `asset_type` (VARCHAR)
- `pool_name` (VARCHAR)
- `scope_name` (VARCHAR)
- `is_enabled` (BOOLEAN)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### archive_runs
- `id` (UUID, PK)
- `run_id` (VARCHAR, UNIQUE)
- `job_name` (VARCHAR)
- `dataset_name` (VARCHAR)
- `asset_type` (VARCHAR)
- `window_name` (VARCHAR)
- `started_at` (TIMESTAMP)
- `completed_at` (TIMESTAMP)
- `status` (VARCHAR)
- `records_processed` (INTEGER)
- `error_summary` (TEXT)
- `error_message` (TEXT)
- `created_at` (TIMESTAMP)

### archive_checkpoints
- `id` (UUID, PK)
- `dataset_name` (VARCHAR)
- `asset_type` (VARCHAR)
- `backfill_start` (DATE)
- `backfill_end` (DATE)
- `last_completed_date` (DATE)
- `shard_id` (VARCHAR)
- `batch_no` (INTEGER)
- `status` (VARCHAR)
- `updated_at` (TIMESTAMP)
- `created_at` (TIMESTAMP)
- UNIQUE constraint: (dataset_name, asset_type)

### archive_summary_daily
- `id` (UUID, PK)
- `date` (DATE)
- `window_name` (VARCHAR)
- `total_jobs` (INTEGER)
- `succeeded_jobs` (INTEGER)
- `failed_jobs` (INTEGER)
- `total_records` (INTEGER)
- `status` (VARCHAR)
- `created_at` (TIMESTAMP)
- UNIQUE constraint: (date, window_name)

### archive_daemon_state
- `id` (UUID, PK)
- `daemon_name` (VARCHAR, UNIQUE)
- `last_loop_at_utc` (TIMESTAMP)
- `last_run_job` (VARCHAR)
- `last_run_status` (VARCHAR)
- `last_success_at_utc` (TIMESTAMP)
- `is_running` (BOOLEAN)
- `updated_at_utc` (TIMESTAMP)

## 3. How Windows Are Defined

Business time standard: **Asia/Shanghai**

Default archive windows:
- **window_1**: 21:30 - 22:30 Asia/Shanghai (Shanghai night)
- **window_2**: 02:00 - 03:00 Asia/Shanghai (Shanghai early morning)

Max duration: 1 hour each, 2 hours total budget per day.

```python
ArchiveWindow(
    window_name="night_window_1",
    start_time="21:30",
    end_time="22:30",
    timezone=ZoneInfo("Asia/Shanghai"),
    max_duration_minutes=60,
    is_enabled=True,
)
```

## 4. How Checkpoint/Resume Works

Checkpoint persistence tracks progress per dataset:

1. **Initialize checkpoint**: Set backfill_start, backfill_end, initial last_completed_date
2. **Update progress**: After each batch, update last_completed_date, batch_no
3. **Resume**: On next run, read last_completed_date and continue from that point
4. **Mark complete**: When backfill complete, mark status as "completed"

```python
checkpoint_store.upsert_checkpoint(
    dataset_name="stock_daily",
    asset_type="stock",
    backfill_start=date(2025, 1, 1),
    backfill_end=date(2025, 12, 31),
    last_completed_date=date(2025, 6, 15),
    shard_id="shard_001",
    batch_no=5,
    status="in_progress",
)
```

## 5. How Summary/Watchdog Works

### Summary Persistence
- Daily summary per window tracks: total_jobs, succeeded_jobs, failed_jobs, total_records, status
- Persisted to `ifa2.archive_summary_daily`
- Query with: `summary_store.get_recent_summary()`

### Health Query
- Check daemon state for: is_running, last_loop_time, latest_run_status
- Check checkpoint advancement: any checkpoint has last_completed_date
- Status values: "ok", "stale", "running", "no_runs", "unknown"

### Watchdog
- Checks if archive is alive (last run < 2 hours)
- Checks if archive is stale (last run > 2 hours)
- Returns: is_alive, is_stale, last_run_time, message

## 6. What Was Proven in Tests

| Test | Result |
|------|--------|
| Window match | PASS |
| archive_runs writes | PASS |
| archive_checkpoints writes | PASS |
| summary persists | PASS |
| health query | PASS |
| checkpoint/resume chain | PASS |
| orchestrator run | PASS |

All 7 tests pass, proving:
1. Archiver can start
2. Window matching works
3. archive_runs persistence works
4. archive_checkpoints persistence works
5. Summary persistence works
6. Health/watchdog queries work
7. Checkpoint/resume chain works end-to-end

## 7. What Is NOT Done Yet (D2+)

- **D2**: Stock archive actual implementation
- **D3**: Macro archive
- **D4**: Commodity/futures/precious metals archive
- **D5**: Standalone ops independence beyond basic framework
- **D6**: Full-scale testing
- **D7**: Runtime snapshot archival
- Large-scale real historical backfill
- New lowfreq/midfreq dataset expansion

## 8. Migration

Alembic migration `017_archive_control` creates all control tables:

```bash
alembic upgrade head
# Creates: archive_jobs, archive_runs, archive_checkpoints, 
#         archive_summary_daily, archive_daemon_state
```

## 9. Usage

### Start daemon
```bash
python -m ifa_data_platform.archive.daemon --once
python -m ifa_data_platform.archive.daemon --loop
```

### Check health
```bash
python -m ifa_data_platform.archive.daemon --health
```

### Configuration
```bash
export ARCHIVE_DAEMON_CONFIG=/path/to/config.yaml
python -m ifa_data_platform.archive.daemon --config /path/to/config.yaml
```