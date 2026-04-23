from __future__ import annotations

from datetime import datetime, timezone, date, timedelta

from zoneinfo import ZoneInfo

from sqlalchemy import text

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


def test_watchdog_waiting_for_next_due_is_not_marked_stale() -> None:
    daemon = UnifiedRuntimeDaemon()
    now = datetime(2026, 4, 22, 23, 20, tzinfo=timezone.utc)
    entry = daemon._build_watchdog_entry(
        ws={
            "worker_type": "midfreq",
            "last_status": "succeeded",
            "last_completed_at": now - timedelta(minutes=40),
            "last_heartbeat_at": now - timedelta(minutes=40),
            "next_due_at_utc": now + timedelta(minutes=20),
            "active_run_id": None,
            "active_started_at": None,
        },
        schedules=[{"runtime_budget_sec": 1800}],
        now=now,
    )
    assert entry["state"] == "idle_waiting_for_next_due"
    assert "next due in" in entry["note"]


def test_watchdog_missed_schedule_exceeds_grace() -> None:
    daemon = UnifiedRuntimeDaemon()
    now = datetime(2026, 4, 22, 23, 20, tzinfo=timezone.utc)
    entry = daemon._build_watchdog_entry(
        ws={
            "worker_type": "highfreq",
            "last_status": "succeeded",
            "last_completed_at": now - timedelta(hours=3),
            "last_heartbeat_at": now - timedelta(hours=3),
            "next_due_at_utc": now - timedelta(hours=1),
            "active_run_id": None,
            "active_started_at": None,
        },
        schedules=[{"runtime_budget_sec": 900}],
        now=now,
    )
    assert entry["state"] == "stale_missed_schedule"
    assert "exceeded grace" in entry["note"]


def test_due_schedules_skips_same_minute_duplicate_for_same_schedule_key() -> None:
    store = UnifiedRuntimeDaemonStore()
    store.seed_schedule_policy()
    now_bj = datetime(2026, 4, 23, 11, 5, tzinfo=ZoneInfo("Asia/Shanghai"))

    store.mark_worker_running(
        worker_type="midfreq",
        run_id="00000000-0000-0000-0000-000000000123",
        schedule_key="midfreq:trade_day_1105",
        trigger_mode="scheduled",
    )
    with store.engine.begin() as conn:
        conn.execute(
            text(
                """
                update ifa2.runtime_worker_state
                   set last_started_at = :last_started_at,
                       active_started_at = :last_started_at,
                       last_heartbeat_at = :last_started_at
                 where worker_type = 'midfreq'
                """
            ),
            {"last_started_at": now_bj.astimezone(timezone.utc)},
        )

    due = store.due_schedules(now_bj, day_type="trading_day")
    assert all(row["schedule_key"] != "midfreq:trade_day_1105" for row in due)


def test_due_schedules_keeps_other_same_minute_worker_due() -> None:
    store = UnifiedRuntimeDaemonStore()
    store.seed_schedule_policy()
    now_bj = datetime(2026, 4, 23, 14, 5, tzinfo=ZoneInfo("Asia/Shanghai"))

    store.mark_worker_running(
        worker_type="midfreq",
        run_id="00000000-0000-0000-0000-000000000124",
        schedule_key="midfreq:trade_day_1105",
        trigger_mode="scheduled",
    )

    due = store.due_schedules(now_bj, day_type="trading_day")
    assert any(row["schedule_key"] == "highfreq:trade_day_1405" for row in due)
