"""Execution summary persistence for highfreq daemon."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


class ExecutionSummaryStore:
    def __init__(self) -> None:
        self.engine = make_engine()

    def store(self, summary_json: str, group_name: str, window_type: str, sla_status: str) -> str:
        record_id = str(uuid.uuid4())
        summary_data = json.loads(summary_json)
        started_at = datetime.fromisoformat(summary_data['started_at'])
        completed_at = datetime.fromisoformat(summary_data['completed_at'])
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.highfreq_execution_summary (
                        id, group_name, window_type, started_at, completed_at,
                        total_datasets, succeeded_datasets, failed_datasets,
                        sla_status, summary_json, created_at
                    ) VALUES (
                        :id, :group_name, :window_type, :started_at, :completed_at,
                        :total, :succeeded, :failed, :sla_status, :summary_json, now()
                    )
                    """
                ),
                {
                    'id': record_id,
                    'group_name': group_name,
                    'window_type': window_type,
                    'started_at': started_at,
                    'completed_at': completed_at,
                    'total': summary_data['total_datasets'],
                    'succeeded': summary_data['succeeded_datasets'],
                    'failed': summary_data['failed_datasets'],
                    'sla_status': sla_status,
                    'summary_json': summary_json,
                },
            )
        return record_id


class DaemonWatchdog:
    def __init__(self) -> None:
        self.engine = make_engine()

    def check_health(self) -> dict:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT latest_loop_at, latest_status, last_window_type
                    FROM ifa2.highfreq_daemon_state
                    WHERE daemon_name = 'highfreq_daemon'
                    """
                )
            ).fetchone()
            if not row or not row.latest_loop_at:
                return {'status': 'unknown', 'message': 'Daemon never run', 'last_heartbeat': None}
            now = datetime.now(timezone.utc)
            last_loop_at = row.latest_loop_at
            if last_loop_at.tzinfo is None:
                last_loop_at = last_loop_at.replace(tzinfo=timezone.utc)
            elapsed_min = (now - last_loop_at).total_seconds() / 60
            status = 'stale' if elapsed_min > 20 else 'healthy'
            return {
                'status': status,
                'message': f'Last run {elapsed_min:.1f} minutes ago',
                'last_heartbeat': last_loop_at,
                'last_status': row.latest_status,
                'last_window_type': row.last_window_type,
            }
