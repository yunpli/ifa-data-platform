"""Daemon health monitoring for midfreq."""

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
    group_states: dict[str, str]

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
            }
        )


class DaemonHealthMonitor:
    """Monitor daemon health."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def get_last_heartbeat(self) -> Optional[datetime]:
        """Get last daemon heartbeat time."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT latest_loop_at FROM ifa2.midfreq_daemon_state
                    ORDER BY latest_loop_at DESC
                    LIMIT 1
                    """
                ),
            ).fetchone()
            return row.latest_loop_at if row else None


def get_daemon_health() -> DaemonHealth:
    """Get current daemon health."""
    monitor = DaemonHealthMonitor()
    last_heartbeat = monitor.get_last_heartbeat()

    message = "OK"
    status = GroupStatus.HEALTHY

    if last_heartbeat:
        now = datetime.now(timezone.utc)
        elapsed = (now - last_heartbeat).total_seconds()
        if elapsed > 3600:
            status = GroupStatus.DEGRADED
            message = f"Last heartbeat {elapsed / 60:.1f} minutes ago"

    return DaemonHealth(
        daemon_name="midfreq_daemon",
        last_heartbeat=last_heartbeat,
        status=status,
        message=message,
        group_states={},
    )


def get_group_status(group_name: str) -> str:
    """Get status of a specific group."""
    return GroupStatus.UNKNOWN
