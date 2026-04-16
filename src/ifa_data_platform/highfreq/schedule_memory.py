"""DB-backed schedule memory for highfreq daemon."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ifa_data_platform.db.engine import make_engine
from sqlalchemy import text


@dataclass
class WindowState:
    window_type: str
    group_name: str
    already_succeeded_today: bool
    retry_count_in_window: int
    last_status: str
    last_run_time: Optional[datetime]
    sla_status: Optional[str]
    duration_ms: Optional[int]


class ScheduleMemory:
    def __init__(self) -> None:
        self.engine = make_engine()

    def get_window_state(self, window_type: str) -> Optional[WindowState]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT window_type, group_name, succeeded_today, retry_count,
                           last_status, last_run_time, sla_status, duration_ms
                    FROM ifa2.highfreq_window_state
                    WHERE window_type = :window_type
                    """
                ),
                {"window_type": window_type},
            ).fetchone()
            if not row:
                return None
            return WindowState(
                window_type=row.window_type,
                group_name=row.group_name,
                already_succeeded_today=bool(row.succeeded_today),
                retry_count_in_window=row.retry_count or 0,
                last_status=row.last_status or "unknown",
                last_run_time=row.last_run_time,
                sla_status=row.sla_status,
                duration_ms=row.duration_ms,
            )

    def mark_window_result(self, window_type: str, group_name: str, status: str, duration_ms: int, sla_status: str) -> None:
        succeeded_today = status == "succeeded"
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.highfreq_window_state (
                        window_type, group_name, succeeded_today, retry_count,
                        last_status, last_run_time, sla_status, duration_ms, created_at
                    ) VALUES (
                        :window_type, :group_name, :succeeded_today, 0,
                        :status, now(), :sla_status, :duration_ms, now()
                    )
                    ON CONFLICT (window_type) DO UPDATE SET
                        group_name = EXCLUDED.group_name,
                        succeeded_today = EXCLUDED.succeeded_today,
                        retry_count = CASE WHEN EXCLUDED.last_status = 'failed' THEN ifa2.highfreq_window_state.retry_count + 1 ELSE 0 END,
                        last_status = EXCLUDED.last_status,
                        last_run_time = now(),
                        sla_status = EXCLUDED.sla_status,
                        duration_ms = EXCLUDED.duration_ms
                    """
                ),
                {
                    'window_type': window_type,
                    'group_name': group_name,
                    'succeeded_today': succeeded_today,
                    'status': status,
                    'sla_status': sla_status,
                    'duration_ms': duration_ms,
                },
            )

    def update_daemon_loop(self, status: str, window_type: Optional[str]) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.highfreq_daemon_state (
                        daemon_name, latest_loop_at, latest_status, last_window_type, created_at
                    ) VALUES (
                        'highfreq_daemon', now(), :status, :window_type, now()
                    )
                    ON CONFLICT (daemon_name) DO UPDATE SET
                        latest_loop_at = now(),
                        latest_status = EXCLUDED.latest_status,
                        last_window_type = EXCLUDED.last_window_type
                    """
                ),
                {'status': status, 'window_type': window_type},
            )
