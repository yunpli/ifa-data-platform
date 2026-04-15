"""Schedule memory for midfreq daemon."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.db.engine import make_engine
from sqlalchemy import text


@dataclass
class WindowState:
    """State of a schedule window."""

    window_type: str
    already_succeeded_today: bool
    retry_count_in_window: int
    last_status: str
    last_run_time: Optional[datetime]


class ScheduleMemory:
    """In-memory schedule state tracking for midfreq daemon."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def get_window_state(self, window_type: str) -> Optional[WindowState]:
        """Get state for a window type."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT window_type, succeeded_today, retry_count, 
                           last_status, last_run_time
                    FROM ifa2.midfreq_window_state
                    WHERE window_type = :window_type
                    """
                ),
                {"window_type": window_type},
            ).fetchone()

            if not row:
                return None

            return WindowState(
                window_type=row.window_type,
                already_succeeded_today=bool(row.succeeded_today),
                retry_count_in_window=row.retry_count or 0,
                last_status=row.last_status or "unknown",
                last_run_time=row.last_run_time,
            )

    def mark_window_succeeded(self, window_type: str, group_name: str) -> None:
        """Mark a window as succeeded for today."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.midfreq_window_state (
                        window_type, group_name, succeeded_today, 
                        retry_count, last_status, last_run_time, created_at
                    )
                    VALUES (
                        :window_type, :group_name, true, 0, 'succeeded', now(), now()
                    )
                    ON CONFLICT (window_type) DO UPDATE SET
                        succeeded_today = true,
                        retry_count = 0,
                        last_status = 'succeeded',
                        last_run_time = now()
                    """
                ),
                {"window_type": window_type, "group_name": group_name},
            )

    def increment_retry(self, window_type: str) -> None:
        """Increment retry count for a window."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.midfreq_window_state (
                        window_type, retry_count, last_status, created_at
                    )
                    VALUES (:window_type, 1, 'failed', now())
                    ON CONFLICT (window_type) DO UPDATE SET
                        retry_count = COALESCE(midfreq_window_state.retry_count, 0) + 1,
                        last_status = 'failed',
                        last_run_time = now()
                    """
                ),
                {"window_type": window_type},
            )

    def mark_window_degraded(self, window_type: str) -> None:
        """Mark a window as degraded."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE ifa2.midfreq_window_state
                    SET last_status = 'degraded', last_run_time = now()
                    WHERE window_type = :window_type
                    """
                ),
                {"window_type": window_type},
            )

    def update_daemon_loop(self, group_name: str, status: str) -> None:
        """Update daemon loop state."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.midfreq_daemon_state (
                        daemon_name, latest_loop_at, latest_status, created_at
                    )
                    VALUES (:daemon_name, now(), :status, now())
                    ON CONFLICT (daemon_name) DO UPDATE SET
                        latest_loop_at = now(),
                        latest_status = :status
                    """
                ),
                {"daemon_name": "midfreq_daemon", "status": status},
            )
