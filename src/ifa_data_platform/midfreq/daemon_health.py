"""Daemon health monitoring for midfreq (DB-backed operator view)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.db.engine import make_engine
from sqlalchemy import text


class GroupStatus:
    """Status of a group execution window."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class DaemonHealth:
    """Health status of the midfreq daemon."""

    daemon_name: str
    last_heartbeat: Optional[datetime]
    status: str
    message: str
    group_states: dict[str, dict]
    recent_windows: list[dict]

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json

        return json.dumps(
            {
                "daemon_name": self.daemon_name,
                "last_heartbeat": self.last_heartbeat.isoformat()
                if self.last_heartbeat
                else None,
                "status": self.status,
                "message": self.message,
                "group_states": self.group_states,
                "recent_windows": self.recent_windows,
            },
            default=str,
        )


class DaemonHealthMonitor:
    """Monitor daemon health."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def get_daemon_state(self) -> Optional[dict]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT daemon_name, latest_loop_at, latest_status, created_at
                    FROM ifa2.midfreq_daemon_state
                    WHERE daemon_name = 'midfreq_daemon'
                    """
                ),
            ).mappings().first()
            return dict(row) if row else None

    def get_window_states(self) -> dict[str, dict]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT window_type, group_name, succeeded_today,
                           retry_count, last_status, last_run_time, created_at
                    FROM ifa2.midfreq_window_state
                    ORDER BY last_run_time DESC NULLS LAST, created_at DESC NULLS LAST
                    """
                ),
            ).mappings().all()
            return {
                row['window_type']: {
                    'group_name': row['group_name'],
                    'succeeded_today': bool(row['succeeded_today']),
                    'retry_count': row['retry_count'] or 0,
                    'last_status': row['last_status'] or 'unknown',
                    'last_run_time': row['last_run_time'],
                }
                for row in rows
            }

    def get_recent_execution_windows(self, limit: int = 10) -> list[dict]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT group_name, window_type, started_at, completed_at,
                           total_datasets, succeeded_datasets, failed_datasets, created_at
                    FROM ifa2.midfreq_execution_summary
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {'limit': limit},
            ).mappings().all()
            return [dict(row) for row in rows]


def get_daemon_health() -> DaemonHealth:
    """Get current daemon health."""
    monitor = DaemonHealthMonitor()
    daemon_state = monitor.get_daemon_state()
    group_states = monitor.get_window_states()
    recent_windows = monitor.get_recent_execution_windows()
    last_heartbeat = daemon_state['latest_loop_at'] if daemon_state else None

    if last_heartbeat:
        now = datetime.now(timezone.utc)
        elapsed = (now - last_heartbeat).total_seconds()
        if elapsed > 3600:
            status = GroupStatus.DEGRADED
            message = f"Last heartbeat {elapsed / 60:.1f} minutes ago"
        else:
            status = GroupStatus.HEALTHY
            message = "OK"
    elif recent_windows:
        status = GroupStatus.DEGRADED
        message = "No daemon heartbeat row, but execution summaries exist"
    else:
        status = GroupStatus.UNKNOWN
        message = "Daemon never run"

    return DaemonHealth(
        daemon_name='midfreq_daemon',
        last_heartbeat=last_heartbeat,
        status=status,
        message=message,
        group_states=group_states,
        recent_windows=recent_windows,
    )


def get_group_status(group_name: str) -> str:
    """Get status of a specific group."""
    health = get_daemon_health()
    for state in health.group_states.values():
        if state.get('group_name') == group_name:
            return state.get('last_status', GroupStatus.UNKNOWN)
    return GroupStatus.UNKNOWN
