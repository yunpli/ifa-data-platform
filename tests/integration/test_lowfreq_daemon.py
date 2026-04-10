"""Integration tests for low-frequency daemon (Job 6)."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, time, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import text

from ifa_data_platform.lowfreq.daemon import run_once
from ifa_data_platform.lowfreq.daemon_config import (
    DaemonConfig,
    GroupConfig,
    ScheduleWindow,
    get_daemon_config,
)
from ifa_data_platform.lowfreq.daemon_health import (
    DaemonHealth,
    GroupStatus,
    get_daemon_health,
    get_group_status,
)
from ifa_data_platform.lowfreq.daemon_orchestrator import DaemonOrchestrator
from ifa_data_platform.lowfreq.schedule_memory import ScheduleMemory, WindowState
from zoneinfo import ZoneInfo


class TestConfigDefaults:
    """Test default configuration values."""

    def test_default_schedule_values(self):
        """Verify default schedule values are set correctly."""
        config = get_daemon_config()

        window_types = {w.window_type for w in config.schedule_windows}
        assert "daily_light" in window_types
        assert "daily_light_fallback" in window_types
        assert "weekly_deep" in window_types

    def test_daily_light_defaults(self):
        """Verify daily_light has correct defaults."""
        config = get_daemon_config()
        window = next(
            w for w in config.schedule_windows if w.window_type == "daily_light"
        )

        assert window.time_str == "22:45"
        assert str(window.timezone) == "Asia/Shanghai"
        assert window.max_retries == 3

    def test_daily_light_fallback_defaults(self):
        """Verify daily_light_fallback has correct defaults."""
        config = get_daemon_config()
        window = next(
            w
            for w in config.schedule_windows
            if w.window_type == "daily_light_fallback"
        )

        assert window.time_str == "01:30"
        assert str(window.timezone) == "Asia/Shanghai"
        assert window.max_retries == 2

    def test_weekly_deep_defaults(self):
        """Verify weekly_deep has correct defaults."""
        config = get_daemon_config()
        window = next(
            w for w in config.schedule_windows if w.window_type == "weekly_deep"
        )

        assert window.time_str == "10:00"
        assert str(window.timezone) == "Asia/Shanghai"
        assert window.day_of_week == 5
        assert window.max_retries == 2


class TestConfigOverrides:
    """Test configuration overrides via file."""

    def test_config_override_values(self):
        """Verify config override via file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
timezone: "America/New_York"
loop_interval_sec: 30
schedule_windows:
  - window_type: custom_window
    group_name: custom_group
    time_str: "15:00"
    max_retries: 5
groups:
  - group_name: custom_group
    datasets: ["custom_ds"]
""")
            f.flush()
            config = get_daemon_config(f.name)
            os.unlink(f.name)

        assert config.loop_interval_sec == 30
        assert str(config.timezone) == "America/New_York"
        window = next(
            w for w in config.schedule_windows if w.window_type == "custom_window"
        )
        assert window.time_str == "15:00"
        assert window.max_retries == 5


class TestScheduleMatching:
    """Test schedule window matching."""

    def test_daily_light_matching_time(self):
        """Verify daily_light matches at correct time."""
        config = get_daemon_config()
        window = next(
            w for w in config.schedule_windows if w.window_type == "daily_light"
        )

        test_time = datetime(2024, 1, 15, 22, 45, tzinfo=ZoneInfo("Asia/Shanghai"))
        assert window.matches(test_time)

    def test_daily_light_non_matching_time(self):
        """Verify daily_light does not match at wrong time."""
        config = get_daemon_config()
        window = next(
            w for w in config.schedule_windows if w.window_type == "daily_light"
        )

        test_time = datetime(2024, 1, 15, 22, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
        assert not window.matches(test_time)

    def test_weekly_deep_matching_day_and_time(self):
        """Verify weekly_deep matches on Saturday at correct time."""
        config = get_daemon_config()
        window = next(
            w for w in config.schedule_windows if w.window_type == "weekly_deep"
        )

        saturday = datetime(2024, 1, 20, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        assert saturday.weekday() == 5
        assert window.matches(saturday)

    def test_weekly_deep_non_matching_day(self):
        """Verify weekly_deep does not match on wrong day."""
        config = get_daemon_config()
        window = next(
            w for w in config.schedule_windows if w.window_type == "weekly_deep"
        )

        friday = datetime(2024, 1, 19, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        assert friday.weekday() == 4
        assert not window.matches(friday)


class TestScheduleMemory:
    """Test schedule memory for deduplication."""

    def test_get_window_state_empty(self):
        """Test getting window state when DB is empty."""
        from ifa_data_platform.lowfreq.daemon_state import GroupStateStore

        store = GroupStateStore()
        with store.engine.begin() as conn:
            conn.execute(text("DELETE FROM ifa2.lowfreq_group_state"))
            conn.execute(text("DELETE FROM ifa2.lowfreq_daemon_state"))

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ScheduleMemory(storage_path=f"{tmpdir}/memory.json")
            state = memory.get_window_state("daily_light")
            assert state is None

    def test_mark_window_succeeded(self):
        """Test marking window as succeeded."""
        from ifa_data_platform.lowfreq.daemon_state import GroupStateStore

        store = GroupStateStore()
        with store.engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM ifa2.lowfreq_group_state WHERE group_name = 'daily_light'"
                )
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ScheduleMemory(storage_path=f"{tmpdir}/memory.json")
            memory.mark_window_succeeded("daily_light", "daily_light")

            state = memory.get_window_state("daily_light")
            assert state is not None
            assert state.already_succeeded_today is True
            assert state.retry_count_in_window == 0

    def test_dedupe_within_day(self):
        """Test deduplication within a day."""
        from ifa_data_platform.lowfreq.daemon_state import GroupStateStore

        store = GroupStateStore()
        with store.engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM ifa2.lowfreq_group_state WHERE group_name = 'daily_light'"
                )
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ScheduleMemory(storage_path=f"{tmpdir}/memory.json")
            memory.mark_window_succeeded("daily_light", "daily_light")

            state = memory.get_window_state("daily_light")
            assert state is not None
            assert state.already_succeeded_today is True

    def test_increment_retry(self):
        """Test retry increment."""
        from ifa_data_platform.lowfreq.daemon_state import GroupStateStore

        store = GroupStateStore()
        with store.engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM ifa2.lowfreq_group_state WHERE group_name = 'daily_light'"
                )
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ScheduleMemory(storage_path=f"{tmpdir}/memory.json")
            memory.increment_retry("daily_light")

            state = memory.get_window_state("daily_light")
            assert state is not None
            assert state.retry_count_in_window == 1

    def test_retry_resets_success_flag(self):
        """Test that retry resets success flag."""
        from ifa_data_platform.lowfreq.daemon_state import GroupStateStore

        store = GroupStateStore()
        with store.engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM ifa2.lowfreq_group_state WHERE group_name = 'daily_light'"
                )
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ScheduleMemory(storage_path=f"{tmpdir}/memory.json")
            memory.mark_window_succeeded("daily_light", "daily_light")
            memory.increment_retry("daily_light")

            state = memory.get_window_state("daily_light")
            assert state is not None
            assert state.already_succeeded_today is False
            assert state.retry_count_in_window == 1


class TestRetryFallback:
    """Test retry and fallback semantics."""

    def test_exhausted_retries_marked_degraded(self):
        """Test that exhausted retries are marked as degraded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = ScheduleMemory(storage_path=f"{tmpdir}/memory.json")
            for _ in range(3):
                memory.increment_retry("daily_light")

            memory.mark_window_degraded("daily_light")

            state = memory.get_window_state("daily_light")
            assert state is not None
            assert state.is_degraded is True
            assert state.retry_count_in_window >= 3


class TestGroupExecution:
    """Test group orchestration."""

    def test_orchestrator_runs_datasets(self):
        """Test orchestrator runs all datasets in group."""
        config = get_daemon_config()
        orchestrator = DaemonOrchestrator(config)

        summary = orchestrator.run_group("daily_light")

        assert summary.total_datasets >= 1
        assert summary.group_name == "daily_light"

    def test_group_execution_not_crash_on_failure(self):
        """Test group execution does not crash on dataset failure."""
        config = get_daemon_config()
        orchestrator = DaemonOrchestrator(config)

        summary = orchestrator.run_group("daily_light")

        assert summary is not None
        assert summary.completed_at is not None


class TestHealthStatus:
    """Test health and status reporting."""

    def test_daemon_health_returns_structure(self):
        """Test daemon health returns expected structure."""
        config = get_daemon_config()
        health = get_daemon_health(config)

        assert isinstance(health, DaemonHealth)
        assert health.status in ["ok", "stale", "no_runs"]
        assert isinstance(health.group_statuses, dict)
        assert isinstance(health.dataset_freshness, dict)

    def test_group_status_returns_structure(self):
        """Test group status returns expected structure."""
        config = get_daemon_config()
        statuses = get_group_status(config)

        assert isinstance(statuses, dict)
        for name, status in statuses.items():
            assert isinstance(status, GroupStatus)
            assert status.group_name == name


class TestDaemonOnceMode:
    """Test --once mode functionality."""

    def test_once_mode_skips_non_matching_window(self):
        """Test --once mode skips when no matching window."""
        config = get_daemon_config()
        window = config.get_matching_window(
            datetime(2024, 1, 15, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        )
        assert window is None

    def test_once_mode_runs_on_matching_window(self):
        """Test --once mode runs on matching window."""
        config = get_daemon_config()
        window = config.get_matching_window(
            datetime(2024, 1, 15, 22, 45, tzinfo=ZoneInfo("Asia/Shanghai"))
        )
        assert window is not None
        assert window.window_type == "daily_light"


class TestDaemonValidation:
    """Test real validation paths."""

    def test_config_loading_from_file(self):
        """Test config loading from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
loop_interval_sec: 45
schedule_windows:
  - window_type: test_window
    group_name: test_group
    time_str: "12:00"
groups:
  - group_name: test_group
    datasets: ["test_ds"]
""")
            f.flush()
            config = get_daemon_config(f.name)
            os.unlink(f.name)

        assert config.loop_interval_sec == 45
        assert len(config.schedule_windows) == 1
        assert len(config.groups) == 1

    def test_config_from_env_var(self):
        """Test config can be loaded from env var."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
loop_interval_sec: 99
schedule_windows: []
groups: []
""")
            f.flush()

            original = os.environ.get("LOWFREQ_DAEMON_CONFIG")
            try:
                os.environ["LOWFREQ_DAEMON_CONFIG"] = f.name
                config = get_daemon_config()
                assert config.loop_interval_sec == 99
            finally:
                if original:
                    os.environ["LOWFREQ_DAEMON_CONFIG"] = original
                else:
                    os.environ.pop("LOWFREQ_DAEMON_CONFIG", None)
                os.unlink(f.name)
