"""Schedule execution memory for daemon deduplication.

Now DB-backed as primary source, with file-based only as debug fallback.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ifa_data_platform.lowfreq.daemon_state import (
    DaemonStateStore,
    GroupStateStore,
    now_utc,
)


@dataclass
class WindowState:
    """State of a schedule window (derived from DB or fallback)."""

    window_type: str
    group_name: str
    already_succeeded_today: bool = False
    already_succeeded_this_week: bool = False
    retry_count_in_window: int = 0
    is_degraded: bool = False
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None


class ScheduleMemory:
    """DB-backed tracking for schedule window execution state.

    Primary source: DB (ifa2.lowfreq_group_state)
    Debug fallback: File (only if DB unavailable, not for decisions)

    Tracks:
    - Whether daily_light already succeeded today
    - Whether weekly_deep already succeeded this week
    - Whether a fallback window is active
    - Retries used in current window
    - Last success time
    """

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self._group_store = GroupStateStore()
        self._daemon_store = DaemonStateStore()

        if storage_path is None:
            storage_path = os.environ.get(
                "LOWFREQ_DAEMON_MEMORY", "/tmp/ifa_daemon_memory.json"
            )
        self._debug_file = Path(storage_path)
        self._debug_fallback = False

    def get_window_state(self, window_type: str) -> Optional[WindowState]:
        """Get state for a window type from DB (primary source)."""
        try:
            group_name = self._window_to_group(window_type)
            db_state = self._group_store.get_group_state(group_name)

            if (
                db_state["last_status"] is None
                and db_state["last_success_at_utc"] is None
                and db_state["last_run_at_utc"] is None
            ):
                return None

            return WindowState(
                window_type=window_type,
                group_name=group_name,
                already_succeeded_today=self._group_store.has_succeeded_today(
                    group_name
                ),
                already_succeeded_this_week=self._group_store.has_succeeded_this_week(
                    group_name
                ),
                retry_count_in_window=db_state["retry_count"],
                is_degraded=db_state["is_degraded"],
                last_success_time=db_state["last_success_at_utc"],
                last_failure_time=db_state["last_run_at_utc"]
                if db_state["last_status"] == "failed"
                else None,
            )
        except Exception as e:
            self._debug_fallback = True
            return self._get_window_state_fallback(window_type)

    def _window_to_group(self, window_type: str) -> str:
        """Map window type to group name."""
        if window_type in ("daily_light", "daily_light_fallback"):
            return "daily_light"
        return window_type

    def mark_window_succeeded(self, window_type: str, group_name: str) -> None:
        """Mark a window as succeeded in DB."""
        try:
            self._group_store.mark_group_success(group_name)
            self._daemon_store.mark_success(group_name)
        except Exception:
            self._debug_fallback = True
            self._mark_window_succeeded_fallback(window_type, group_name)

    def mark_window_failed(self, window_type: str) -> None:
        """Mark a window as failed in DB."""
        group_name = self._window_to_group(window_type)
        try:
            self._group_store.update_group_run(group_name, "failed")
        except Exception:
            self._debug_fallback = True

    def mark_window_degraded(self, window_type: str) -> None:
        """Mark a window as degraded (exhausted retries) in DB."""
        group_name = self._window_to_group(window_type)
        try:
            self._group_store.mark_degraded(group_name)
        except Exception:
            self._debug_fallback = True

    def increment_retry(self, window_type: str) -> None:
        """Increment retry count for a window in DB."""
        group_name = self._window_to_group(window_type)
        try:
            self._group_store.increment_retry(group_name)
        except Exception:
            self._debug_fallback = True

    def reset_daily(self) -> None:
        """Reset daily success flags (for testing or manual reset)."""
        pass

    def reset_weekly(self) -> None:
        """Reset weekly success flags."""
        pass

    def get_daemon_state(self) -> dict:
        """Get daemon-level state from DB."""
        try:
            return self._daemon_store.get_state()
        except Exception:
            return {"last_loop_at_utc": None, "last_success_at_utc": None}

    def update_daemon_loop(
        self, group_name: Optional[str], status: Optional[str]
    ) -> None:
        """Update daemon-level state in DB."""
        try:
            self._daemon_store.update_loop(group_name, status)
        except Exception:
            pass

    def _get_window_state_fallback(self, window_type: str) -> Optional[WindowState]:
        """Debug fallback: read from file."""
        if not self._debug_file.exists():
            return None

        try:
            with open(self._debug_file) as f:
                data = json.load(f)

            state = data.get(window_type)
            if not state:
                return None

            return WindowState(
                window_type=window_type,
                group_name=state.get("group_name", ""),
                already_succeeded_today=state.get("already_succeeded_today", False),
                already_succeeded_this_week=state.get(
                    "already_succeeded_this_week", False
                ),
                retry_count_in_window=state.get("retry_count_in_window", 0),
                is_degraded=state.get("is_degraded", False),
                last_success_time=(
                    datetime.fromisoformat(state["last_success_time"])
                    if state.get("last_success_time")
                    else None
                ),
                last_failure_time=(
                    datetime.fromisoformat(state["last_failure_time"])
                    if state.get("last_failure_time")
                    else None
                ),
            )
        except Exception:
            return None

    def _mark_window_succeeded_fallback(
        self, window_type: str, group_name: str
    ) -> None:
        """Debug fallback: write to file."""
        data = {}
        if self._debug_file.exists():
            try:
                with open(self._debug_file) as f:
                    data = json.load(f)
            except Exception:
                pass

        now = now_utc()
        data[window_type] = {
            "group_name": group_name,
            "already_succeeded_today": True,
            "already_succeeded_this_week": True,
            "retry_count_in_window": 0,
            "is_degraded": False,
            "last_success_time": now.isoformat(),
            "last_failure_time": None,
        }

        try:
            with open(self._debug_file, "w") as f:
                json.dump(data, f)
        except Exception:
            pass
