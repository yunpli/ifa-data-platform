# D1 Archive Layer Runbook

**Date**: 2026-04-13
**Version**: 0.1.0

## 1. How to Start

### Prerequisites
```bash
# Ensure migration is applied
alembic upgrade head

# Verify tables exist
psql -c "\dt ifa2.archive_*" ifa_db
```

### Start in One-Shot Mode
```bash
python -m ifa_data_platform.archive.daemon --once
```

### Start in Loop Mode
```bash
python -m ifa_data_platform.archive.daemon --loop
```

### With Custom Config
```bash
python -m ifa_data_platform.archive.daemon --config /path/to/config.yaml --once
```

## 2. How to Check Health

### CLI Health Check
```bash
python -m ifa_data_platform.archive.daemon --health
```

Output:
```
=== Archive Health ===
Status: ok
Is Running: False
Last Run: 2026-04-13 21:45:00
Latest Run Status: succeeded
Checkpoint Advanced: True
Message: Archive is healthy

=== Archive Watchdog ===
Is Alive: True
Is Stale: False
Last Run: 2026-04-13 21:45:00
Message: Archive is alive, last run 0m ago
```

### Python Health Query
```python
from ifa_data_platform.archive.archive_config import get_archive_config
from ifa_data_platform.archive.archive_health import get_archive_health, check_archive_watchdog

config = get_archive_config()
health = get_archive_health(config)
print(f"Status: {health.status}")
print(f"Message: {health.message}")

watchdog = check_archive_watchdog(config)
print(f"Alive: {watchdog.is_alive}")
```

## 3. How to Check Summary

### CLI Summary (via health)
```bash
python -m ifa_data_platform.archive.daemon --health
```

### Python Summary Query
```python
from ifa_data_platform.archive.archive_summary import ArchiveSummaryStore

store = ArchiveSummaryStore()
summaries = store.list_summaries(limit=10)
for s in summaries:
    print(f"{s['date']} {s['window_name']}: {s['succeeded_jobs']}/{s['total_jobs']} succeeded")
```

### Query Recent Summaries
```python
summary = store.get_recent_summary()
print(f"Latest: {summary}")
```

## 4. How to Check Checkpoint

### Python Checkpoint Query
```python
from ifa_data_platform.archive.archive_checkpoint import ArchiveCheckpointStore

store = ArchiveCheckpointStore()
checkpoints = store.list_checkpoints()
for cp in checkpoints:
    print(f"{cp['dataset_name']} {cp['asset_type']}: "
          f"last_completed={cp['last_completed_date']}, "
          f"status={cp['status']}")
```

### Query Specific Checkpoint
```python
cp = store.get_checkpoint("stock_daily", "stock")
if cp:
    print(f"Resume from: {cp['last_completed_date']}")
```

## 5. Current Windows

Business time standard: **Asia/Shanghai**

| Window | Start | End | Max Duration |
|-------|-------|-----|-------------|
| night_window_1 | 21:30 | 22:30 | 60 min |
| night_window_2 | 02:00 | 03:00 | 60 min |

Total budget: 2 hours/day

## 6. Common Troubleshooting

### "No matching window"
- Current time is outside window hours
- Check: Is current time in 21:30-22:30 or 02:00-03:00 Shanghai time?

### "No archive runs recorded"
- First run has not completed yet
- Run with: `python -m ifa_data_platform.archive.daemon --once`

### "Archive is stale"
- No runs in >2 hours
- Check daemon log for errors
- Check database connectivity

### Checkpoint Not Advancing
- Verify checkpoint exists:
  ```python
  cp = store.get_checkpoint("dataset", "stock")
  print(cp)
  ```
- Check orchestrator is actually processing batches

### Database Connection Issues
- Verify database is running
- Check `DATABASE_URL` in settings
- Test connectivity: `psql -c "SELECT 1" ifa_db`

### Health Status "running"
- Another daemon instance may be running
- Check processes: `ps aux | grep archive_daemon`
- Or check `is_running` in DB:
  ```sql
  SELECT is_running FROM ifa2.archive_daemon_state;
  ```

### Reset Daemon State
```python
from ifa_data_platform.archive.archive_daemon_state import ArchiveDaemonStateStore
store = ArchiveDaemonStateStore()
store.mark_running(False)
store.update_loop(None, None)
```

## 7. SQL Reference

### Check All Tables
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'ifa2' 
AND table_name LIKE 'archive_%';
```

### View Recent Runs
```sql
SELECT job_name, status, records_processed, started_at, completed_at
FROM ifa2.archive_runs
ORDER BY started_at DESC
LIMIT 10;
```

### View Checkpoints
```sql
SELECT dataset_name, asset_type, last_completed_date, batch_no, status, updated_at
FROM ifa2.archive_checkpoints;
```

### View Summaries
```sql
SELECT date, window_name, total_jobs, succeeded_jobs, failed_jobs, status
FROM ifa2.archive_summary_daily
ORDER BY date DESC, window_name DESC
LIMIT 10;
```

### View Daemon State
```sql
SELECT * FROM ifa2.archive_daemon_state;
```

## 8. Configuration File Example

```yaml
timezone: "Asia/Shanghai"
loop_interval_sec: 60

windows:
  - window_name: "night_window_1"
    start_time: "21:30"
    end_time: "22:30"
    max_duration_minutes: 60
    is_enabled: true

  - window_name: "night_window_2"
    start_time: "02:00"
    end_time: "03:00"
    max_duration_minutes: 60
    is_enabled: true

jobs:
  - job_name: "stock_daily_archive"
    dataset_name: "stock_daily"
    asset_type: "stock"
    pool_name: "default"
    scope_name: "all"
    is_enabled: true
    description: "Stock daily historical data archive"
```

## 9. Run Tests

```bash
python -m pytest tests/archive/test_archive_d1.py -v
```

All tests must pass for D1 acceptance.