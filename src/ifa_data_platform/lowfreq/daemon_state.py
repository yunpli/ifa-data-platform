"""Daemon state persistence (DB-backed, primary source of truth)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class DaemonStateStore:
    """DB-backed daemon state as primary source of truth.

    Tracks daemon-level state: last loop time, last run group, last status, etc.
    """

    def __init__(self, daemon_name: str = "default") -> None:
        self.engine = make_engine()
        self.daemon_name = daemon_name

    def get_state(self) -> dict:
        """Get daemon state from DB."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT daemon_name, last_loop_at_utc, last_run_group,
                           last_run_status, last_success_at_utc, updated_at_utc
                    FROM ifa2.lowfreq_daemon_state
                    WHERE daemon_name = :daemon_name
                    """
                ),
                {"daemon_name": self.daemon_name},
            ).fetchone()

            if not row:
                return {
                    "daemon_name": self.daemon_name,
                    "last_loop_at_utc": None,
                    "last_run_group": None,
                    "last_run_status": None,
                    "last_success_at_utc": None,
                    "updated_at_utc": None,
                }

            return {
                "daemon_name": row.daemon_name,
                "last_loop_at_utc": row.last_loop_at_utc,
                "last_run_group": row.last_run_group,
                "last_run_status": row.last_run_status,
                "last_success_at_utc": row.last_success_at_utc,
                "updated_at_utc": row.updated_at_utc,
            }

    def update_loop(self, group_name: Optional[str], status: Optional[str]) -> None:
        """Update daemon state after a loop iteration."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.lowfreq_daemon_state (daemon_name, last_loop_at_utc, last_run_group, last_run_status, updated_at_utc)
                    VALUES (:daemon_name, :last_loop_at_utc, :last_run_group, :last_run_status, now())
                    ON CONFLICT (daemon_name) DO UPDATE SET
                        last_loop_at_utc = EXCLUDED.last_loop_at_utc,
                        last_run_group = EXCLUDED.last_run_group,
                        last_run_status = EXCLUDED.last_run_status,
                        updated_at_utc = now()
                    """
                ),
                {
                    "daemon_name": self.daemon_name,
                    "last_loop_at_utc": now_utc(),
                    "last_run_group": group_name,
                    "last_run_status": status,
                },
            )

    def mark_success(self, group_name: str) -> None:
        """Mark a group run as successful."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.lowfreq_daemon_state (daemon_name, last_success_at_utc, last_run_group, last_run_status, updated_at_utc)
                    VALUES (:daemon_name, :last_success_at_utc, :group_name, 'succeeded', now())
                    ON CONFLICT (daemon_name) DO UPDATE SET
                        last_success_at_utc = EXCLUDED.last_success_at_utc,
                        last_run_group = EXCLUDED.last_run_group,
                        last_run_status = 'succeeded',
                        updated_at_utc = now()
                    """
                ),
                {
                    "daemon_name": self.daemon_name,
                    "last_success_at_utc": now_utc(),
                    "group_name": group_name,
                },
            )


class GroupStateStore:
    """DB-backed group state as primary source of truth.

    Tracks per-group state: last run time, success time, status, retry count, degraded, fallback.
    """

    def __init__(self) -> None:
        self.engine = make_engine()

    def get_group_state(self, group_name: str) -> dict:
        """Get state for a specific group."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT group_name, last_run_at_utc, last_success_at_utc,
                           last_status, retry_count, is_degraded, in_fallback
                    FROM ifa2.lowfreq_group_state
                    WHERE group_name = :group_name
                    """
                ),
                {"group_name": group_name},
            ).fetchone()

            if not row:
                return {
                    "group_name": group_name,
                    "last_run_at_utc": None,
                    "last_success_at_utc": None,
                    "last_status": None,
                    "retry_count": 0,
                    "is_degraded": False,
                    "in_fallback": False,
                }

            return {
                "group_name": row.group_name,
                "last_run_at_utc": row.last_run_at_utc,
                "last_success_at_utc": row.last_success_at_utc,
                "last_status": row.last_status,
                "retry_count": row.retry_count or 0,
                "is_degraded": bool(row.is_degraded),
                "in_fallback": bool(row.in_fallback),
            }

    def update_group_run(self, group_name: str, status: str) -> None:
        """Update group state after a run."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.lowfreq_group_state (group_name, last_run_at_utc, last_status, updated_at_utc)
                    VALUES (:group_name, :last_run_at_utc, :last_status, now())
                    ON CONFLICT (group_name) DO UPDATE SET
                        last_run_at_utc = EXCLUDED.last_run_at_utc,
                        last_status = EXCLUDED.last_status,
                        updated_at_utc = now()
                    """
                ),
                {
                    "group_name": group_name,
                    "last_run_at_utc": now_utc(),
                    "last_status": status,
                },
            )

    def mark_group_success(self, group_name: str) -> None:
        """Mark a group as successful, reset retries."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.lowfreq_group_state (group_name, last_success_at_utc, last_status, retry_count, is_degraded, in_fallback, updated_at_utc)
                    VALUES (:group_name, :last_success_at_utc, 'succeeded', 0, FALSE, FALSE, now())
                    ON CONFLICT (group_name) DO UPDATE SET
                        last_success_at_utc = EXCLUDED.last_success_at_utc,
                        last_status = 'succeeded',
                        retry_count = 0,
                        is_degraded = FALSE,
                        in_fallback = FALSE,
                        updated_at_utc = now()
                    """
                ),
                {
                    "group_name": group_name,
                    "last_success_at_utc": now_utc(),
                },
            )

    def increment_retry(self, group_name: str) -> None:
        """Increment retry count for a group."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.lowfreq_group_state (group_name, retry_count, last_status, updated_at_utc)
                    VALUES (:group_name, 1, 'retrying', now())
                    ON CONFLICT (group_name) DO UPDATE SET
                        retry_count = ifa2.lowfreq_group_state.retry_count + 1,
                        last_status = 'retrying',
                        updated_at_utc = now()
                    """
                ),
                {"group_name": group_name},
            )

    def mark_degraded(self, group_name: str) -> None:
        """Mark a group as degraded (exhausted retries)."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE ifa2.lowfreq_group_state
                    SET is_degraded = TRUE, last_status = 'degraded', updated_at_utc = now()
                    WHERE group_name = :group_name
                    """
                ),
                {"group_name": group_name},
            )

    def set_fallback(self, group_name: str, in_fallback: bool) -> None:
        """Set fallback mode for a group."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE ifa2.lowfreq_group_state
                    SET in_fallback = :in_fallback, updated_at_utc = now()
                    WHERE group_name = :group_name
                    """
                ),
                {"group_name": group_name, "in_fallback": in_fallback},
            )

    def has_succeeded_today(self, group_name: str) -> bool:
        """Check if group succeeded today (UTC-normalized day boundary)."""
        state = self.get_group_state(group_name)
        if not state["last_success_at_utc"]:
            return False

        now = now_utc().astimezone(timezone.utc)
        last_success = state["last_success_at_utc"]

        if last_success.tzinfo is None:
            last_success = last_success.replace(tzinfo=timezone.utc)
        else:
            last_success = last_success.astimezone(timezone.utc)

        return last_success.date() == now.date() and state["last_status"] == "succeeded"

    def has_succeeded_this_week(self, group_name: str) -> bool:
        """Check if group succeeded this ISO week (UTC-normalized)."""
        state = self.get_group_state(group_name)
        if not state["last_success_at_utc"]:
            return False

        now = now_utc().astimezone(timezone.utc)
        last_success = state["last_success_at_utc"]

        if last_success.tzinfo is None:
            last_success = last_success.replace(tzinfo=timezone.utc)
        else:
            last_success = last_success.astimezone(timezone.utc)

        return (
            now.isocalendar()[0] == last_success.isocalendar()[0]
            and now.isocalendar()[1] == last_success.isocalendar()[1]
            and state["last_status"] == "succeeded"
        )

    def get_all_groups_state(self) -> dict[str, dict]:
        """Get state for all groups."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT group_name, last_run_at_utc, last_success_at_utc,
                           last_status, retry_count, is_degraded, in_fallback
                    FROM ifa2.lowfreq_group_state
                    """
                ),
            ).fetchall()

            result = {}
            for row in rows:
                result[row.group_name] = {
                    "group_name": row.group_name,
                    "last_run_at_utc": row.last_run_at_utc,
                    "last_success_at_utc": row.last_success_at_utc,
                    "last_status": row.last_status,
                    "retry_count": row.retry_count or 0,
                    "is_degraded": bool(row.is_degraded),
                    "in_fallback": bool(row.in_fallback),
                }

            return result
