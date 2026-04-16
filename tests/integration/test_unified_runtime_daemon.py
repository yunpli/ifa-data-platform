from __future__ import annotations

from datetime import datetime, timezone, date

from ifa_data_platform.runtime.trading_calendar import TradingCalendarService
from ifa_data_platform.runtime.unified_daemon import UnifiedRuntimeDaemon, UnifiedRuntimeDaemonStore


def test_seed_default_schedules_populates_all_four_workers() -> None:
    store = UnifiedRuntimeDaemonStore()
    store.seed_schedule_policy()
    rows = store.list_schedules(enabled_only=False)
    worker_types = {row["worker_type"] for row in rows}
    assert {"lowfreq", "midfreq", "highfreq", "archive"}.issubset(worker_types)


def test_manual_entry_runs_through_unified_daemon() -> None:
    daemon = UnifiedRuntimeDaemon()
    result = daemon.run_manual("highfreq", dry_run_manifest_only=True)
    assert result["lane"] == "highfreq"
    assert result["run_id"]
    assert result["governance_state"] in {"ok", "degraded"}


def test_scheduled_due_selection_uses_beijing_time_and_day_type() -> None:
    daemon = UnifiedRuntimeDaemon()
    t = datetime(2026, 4, 16, 1, 15, tzinfo=timezone.utc)
    day_type = daemon.calendar.get_runtime_day_type(t, exchange="SSE")
    results = daemon.run_due_once(current_time_utc=t)
    if day_type == "trading_day":
        assert any(r["lane"] == "highfreq" for r in results)
    else:
        assert results == []


def test_status_surface_returns_central_views() -> None:
    daemon = UnifiedRuntimeDaemon()
    payload = daemon.status()
    assert payload["daemon_name"] == "unified_runtime_daemon"
    assert payload["official_long_running_entry"].endswith("--loop")
    assert isinstance(payload["schedules"], list)
    assert isinstance(payload["worker_states"], list)
    assert isinstance(payload["recent_runs"], list)


def test_trading_calendar_service_reads_db_backed_truth() -> None:
    svc = TradingCalendarService()
    status = svc.get_day_status(date(2026, 4, 16), exchange="SSE")
    assert status.source in {"ifa2.trade_cal_current", "fallback_weekday_only"}
    assert status.as_of_date == date(2026, 4, 16)
