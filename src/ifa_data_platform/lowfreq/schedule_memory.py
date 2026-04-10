"""Schedule execution memory for daemon deduplication."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class WindowState:
    """State of a schedule window."""

    window_type: str
    group_name: str
    already_succeeded_today: bool = False
    already_succeeded_this_week: bool = False
    retry_count_in_window: int = 0
    is_degraded: bool = False
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None


class ScheduleMemory:
    """In-memory tracking for schedule window execution state.

    Tracks:
    - Whether daily_light already succeeded today
    - Whether weekly_deep already succeeded this week
    - Whether a fallback window is active
    - Retries used in current window
    - Last success time
    """

    def __init__(self, storage_path: Optional[str] = None) -> None:
        if storage_path is None:
            storage_path = os.environ.get(
                "LOWFREQ_DAEMON_MEMORY", "/tmp/ifa_daemon_memory.json"
            )
        self.storage_path = Path(storage_path)
        self._memory: dict[str, WindowState] = {}
        self._load()

    def _load(self) -> None:
        """Load memory from file if exists."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path) as f:
                data = json.load(f)

            for window_type, state in data.items():
                self._memory[window_type] = WindowState(
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
            pass

    def _save(self) -> None:
        """Persist memory to file."""
        data = {}
        for window_type, state in self._memory.items():
            data[window_type] = {
                "group_name": state.group_name,
                "already_succeeded_today": state.already_succeeded_today,
                "already_succeeded_this_week": state.already_succeeded_this_week,
                "retry_count_in_window": state.retry_count_in_window,
                "is_degraded": state.is_degraded,
                "last_success_time": (
                    state.last_success_time.isoformat()
                    if state.last_success_time
                    else None
                ),
                "last_failure_time": (
                    state.last_failure_time.isoformat()
                    if state.last_failure_time
                    else None
                ),
            }

        try:
            with open(self.storage_path, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def get_window_state(self, window_type: str) -> Optional[WindowState]:
        """Get state for a window type."""
        return self._memory.get(window_type)

    def mark_window_succeeded(self, window_type: str, group_name: str) -> None:
        """Mark a window as succeeded."""
        now = datetime.now(timezone.utc)
        today = now.date()
        week_num = now.isocalendar()[1]

        if window_type not in self._memory:
            self._memory[window_type] = WindowState(
                window_type=window_type, group_name=group_name
            )

        state = self._memory[window_type]
        state.already_succeeded_today = True
        state.already_succeeded_this_week = True
        state.retry_count_in_window = 0
        state.is_degraded = False
        state.last_success_time = now
        state.group_name = group_name

        self._save()

    def mark_window_failed(self, window_type: str) -> None:
        """Mark a window as failed."""
        now = datetime.now(timezone.utc)

        if window_type not in self._memory:
            self._memory[window_type] = WindowState(
                window_type=window_type, group_name=""
            )

        state = self._memory[window_type]
        state.last_failure_time = now

        self._save()

    def mark_window_degraded(self, window_type: str) -> None:
        """Mark a window as degraded (exhausted retries)."""
        if window_type not in self._memory:
            self._memory[window_type] = WindowState(
                window_type=window_type, group_name=""
            )

        state = self._memory[window_type]
        state.is_degraded = True

        self._save()

    def increment_retry(self, window_type: str) -> None:
        """Increment retry count for a window."""
        if window_type not in self._memory:
            self._memory[window_type] = WindowState(
                window_type=window_type, group_name=""
            )

        state = self._memory[window_type]
        state.retry_count_in_window += 1
        state.already_succeeded_today = False

        self._save()

    def reset_daily(self) -> None:
        """Reset daily success flags (for testing or manual reset)."""
        for state in self._memory.values():
            state.already_succeeded_today = False
            state.retry_count_in_window = 0
        self._save()

    def reset_weekly(self) -> None:
        """Reset weekly success flags."""
        for state in self._memory.values():
            state.already_succeeded_this_week = False
        self._save()
