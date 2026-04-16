from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

DB_URL = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp')
OUT_DIR = Path('artifacts/acceptance_monitor')
OUT_DIR.mkdir(parents=True, exist_ok=True)
engine = create_engine(DB_URL)

WORKERS = ['lowfreq', 'midfreq', 'highfreq', 'archive']
LANE_TABLES = {
    'lowfreq': ['lowfreq_runs', 'job_runs', 'unified_runtime_runs'],
    'midfreq': ['midfreq_execution_summary', 'job_runs', 'unified_runtime_runs'],
    'highfreq': ['highfreq_execution_summary', 'highfreq_runs', 'job_runs', 'unified_runtime_runs'],
    'archive': ['archive_runs', 'archive_checkpoints', 'archive_target_catchup', 'archive_summary_daily', 'unified_runtime_runs'],
}


def table_count(conn, table: str) -> int:
    return conn.execute(text(f'select count(*) from ifa2."{table}"')).scalar_one()


def latest_runtime(conn, worker: str):
    row = conn.execute(text(
        "select lane, trigger_mode, status, governance_state, runtime_budget_sec, started_at, completed_at, duration_ms, error_count "
        "from ifa2.unified_runtime_runs where lane=:w order by started_at desc limit 1"
    ), {'w': worker}).mappings().first()
    return dict(row) if row else None


def worker_state(conn, worker: str):
    row = conn.execute(text(
        "select worker_type, last_trigger_mode, last_status, active_run_id, active_started_at, next_due_at_utc, last_error "
        "from ifa2.runtime_worker_state where worker_type=:w"
    ), {'w': worker}).mappings().first()
    return dict(row) if row else None


def snapshot(label: str):
    payload = {
        'label': label,
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'workers': {},
    }
    with engine.begin() as conn:
        for worker in WORKERS:
            payload['workers'][worker] = {
                'runtime': latest_runtime(conn, worker),
                'worker_state': worker_state(conn, worker),
                'table_counts': {t: table_count(conn, t) for t in LANE_TABLES[worker]},
            }
    path = OUT_DIR / f'{label}.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    print(path)


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == 'once':
        label = sys.argv[2] if len(sys.argv) >= 3 else datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot(label)
        return
    if len(sys.argv) >= 2 and sys.argv[1] == 'loop':
        interval = int(sys.argv[2]) if len(sys.argv) >= 3 else 180
        labels = ['t+1m', 't+3m', 't+5m', 't+10m']
        start = time.time()
        idx = 0
        while True:
            elapsed = int(time.time() - start)
            if idx < len(labels):
                target = [60, 180, 300, 600][idx]
                if elapsed >= target:
                    snapshot(labels[idx])
                    idx += 1
                    continue
            if elapsed >= 600:
                snapshot(f't+{elapsed//60}m')
                time.sleep(interval)
                continue
            time.sleep(5)
        return
    print('usage: monitor_unified_acceptance_run.py once <label> | loop [interval_sec]')


if __name__ == '__main__':
    main()
