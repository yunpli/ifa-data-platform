from __future__ import annotations

import argparse
import json
import signal
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.runtime.schedule_policy import DEFAULT_SCHEDULE_POLICY, SchedulePolicyRow
from ifa_data_platform.runtime.trading_calendar import TradingCalendarService
from ifa_data_platform.runtime.unified_runtime import UnifiedRuntime, now_utc

BJ_TZ = ZoneInfo("Asia/Shanghai")


@dataclass
class RuntimeWorkerSchedule:
    worker_type: str
    day_type: str
    schedule_key: str
    group_name: Optional[str]
    trigger_type: str
    timezone: str
    beijing_time_hm: Optional[str]
    day_of_week: Optional[int]
    cadence_minutes: Optional[int]
    runtime_budget_sec: int
    overlap_policy: str
    retry_policy: str
    max_retries: int
    enabled: bool
    schedule_source: str
    purpose: str
    schedule_payload: dict[str, Any]


class UnifiedRuntimeDaemonStore:
    def __init__(self) -> None:
        self.engine = make_engine()

    def seed_schedule_policy(self) -> None:
        defaults = [
            RuntimeWorkerSchedule(
                worker_type=row.worker_type,
                day_type=row.day_type,
                schedule_key=row.schedule_key,
                group_name=row.group_name,
                trigger_type="daily_time",
                timezone="Asia/Shanghai",
                beijing_time_hm=row.beijing_time_hm,
                day_of_week=None,
                cadence_minutes=None,
                runtime_budget_sec=row.runtime_budget_sec,
                overlap_policy=row.overlap_policy,
                retry_policy=row.retry_policy,
                max_retries=row.max_retries,
                enabled=row.should_run,
                schedule_source="policy_seeded",
                purpose=row.purpose,
                schedule_payload={
                    "day_type": row.day_type,
                    "purpose": row.purpose,
                    "group_name": row.group_name,
                },
            )
            for row in DEFAULT_SCHEDULE_POLICY
        ]
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM ifa2.runtime_worker_schedules WHERE schedule_source IN ('seeded_from_code', 'policy_seeded')"))
            for item in defaults:
                conn.execute(text("""
                    INSERT INTO ifa2.runtime_worker_schedules (
                        id, worker_type, day_type, schedule_key, group_name, trigger_type, timezone,
                        beijing_time_hm, day_of_week, cadence_minutes, runtime_budget_sec,
                        overlap_policy, retry_policy, max_retries, enabled, schedule_source,
                        purpose, schedule_payload, created_at, updated_at
                    ) VALUES (
                        :id, :worker_type, :day_type, :schedule_key, :group_name, :trigger_type, :timezone,
                        :beijing_time_hm, :day_of_week, :cadence_minutes, :runtime_budget_sec,
                        :overlap_policy, :retry_policy, :max_retries, :enabled, :schedule_source,
                        :purpose, CAST(:schedule_payload AS jsonb), now(), now()
                    )
                    ON CONFLICT (worker_type, schedule_key) DO UPDATE SET
                        day_type = EXCLUDED.day_type,
                        group_name = EXCLUDED.group_name,
                        trigger_type = EXCLUDED.trigger_type,
                        timezone = EXCLUDED.timezone,
                        beijing_time_hm = EXCLUDED.beijing_time_hm,
                        day_of_week = EXCLUDED.day_of_week,
                        cadence_minutes = EXCLUDED.cadence_minutes,
                        runtime_budget_sec = EXCLUDED.runtime_budget_sec,
                        overlap_policy = EXCLUDED.overlap_policy,
                        retry_policy = EXCLUDED.retry_policy,
                        max_retries = EXCLUDED.max_retries,
                        enabled = EXCLUDED.enabled,
                        schedule_source = EXCLUDED.schedule_source,
                        purpose = EXCLUDED.purpose,
                        schedule_payload = EXCLUDED.schedule_payload,
                        updated_at = now()
                """), {
                    "id": str(uuid.uuid4()),
                    "worker_type": item.worker_type,
                    "day_type": item.day_type,
                    "schedule_key": item.schedule_key,
                    "group_name": item.group_name,
                    "trigger_type": item.trigger_type,
                    "timezone": item.timezone,
                    "beijing_time_hm": item.beijing_time_hm,
                    "day_of_week": item.day_of_week,
                    "cadence_minutes": item.cadence_minutes,
                    "runtime_budget_sec": item.runtime_budget_sec,
                    "overlap_policy": item.overlap_policy,
                    "retry_policy": item.retry_policy,
                    "max_retries": item.max_retries,
                    "enabled": item.enabled,
                    "schedule_source": item.schedule_source,
                    "purpose": item.purpose,
                    "schedule_payload": json.dumps(item.schedule_payload, ensure_ascii=False),
                })

    def list_schedules(self, enabled_only: bool = True, day_type: Optional[str] = None) -> list[dict[str, Any]]:
        sql = """
            SELECT worker_type, day_type, schedule_key, group_name, trigger_type, timezone,
                   beijing_time_hm, day_of_week, cadence_minutes, runtime_budget_sec,
                   overlap_policy, retry_policy, max_retries, enabled, schedule_source,
                   purpose, schedule_payload, created_at, updated_at
            FROM ifa2.runtime_worker_schedules
            WHERE 1=1
        """
        params: dict[str, Any] = {}
        if enabled_only:
            sql += " AND enabled = true"
        if day_type is not None:
            sql += " AND day_type = :day_type"
            params["day_type"] = day_type
        sql += " ORDER BY day_type, worker_type, beijing_time_hm NULLS LAST, schedule_key"
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
            return [dict(r) for r in rows]

    def due_schedules(self, now_bj: datetime, day_type: str) -> list[dict[str, Any]]:
        due = []
        for row in self.list_schedules(enabled_only=True, day_type=day_type):
            if row["trigger_type"] != "daily_time" or not row["beijing_time_hm"]:
                continue
            if row["day_of_week"] is not None and now_bj.weekday() != row["day_of_week"]:
                continue
            if now_bj.strftime("%H:%M") == row["beijing_time_hm"]:
                due.append(row)
        return due

    def get_worker_state(self, worker_type: str) -> Optional[dict[str, Any]]:
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT * FROM ifa2.runtime_worker_state WHERE worker_type=:worker_type"), {"worker_type": worker_type}).mappings().first()
            return dict(row) if row else None

    def mark_worker_running(self, *, worker_type: str, run_id: str, schedule_key: Optional[str], trigger_mode: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO ifa2.runtime_worker_state (
                    worker_type, last_run_id, last_schedule_key, last_trigger_mode,
                    last_started_at, active_run_id, active_schedule_key, active_started_at,
                    last_heartbeat_at, updated_at
                ) VALUES (
                    :worker_type, CAST(:run_id AS uuid), :schedule_key, :trigger_mode,
                    now(), CAST(:run_id AS uuid), :schedule_key, now(), now(), now()
                )
                ON CONFLICT (worker_type) DO UPDATE SET
                    last_run_id = CAST(:run_id AS uuid),
                    last_schedule_key = :schedule_key,
                    last_trigger_mode = :trigger_mode,
                    last_started_at = now(),
                    active_run_id = CAST(:run_id AS uuid),
                    active_schedule_key = :schedule_key,
                    active_started_at = now(),
                    last_heartbeat_at = now(),
                    updated_at = now()
            """), {"worker_type": worker_type, "run_id": run_id, "schedule_key": schedule_key, "trigger_mode": trigger_mode})

    def mark_worker_finished(self, *, worker_type: str, run_id: str, status: str, error: Optional[str] = None, next_due_at_utc: Optional[datetime] = None) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO ifa2.runtime_worker_state (
                    worker_type, last_run_id, last_completed_at, last_status,
                    active_run_id, active_schedule_key, active_started_at,
                    last_heartbeat_at, last_error, next_due_at_utc, updated_at
                ) VALUES (
                    :worker_type, CAST(:run_id AS uuid), now(), :status,
                    NULL, NULL, NULL, now(), :error, :next_due_at_utc, now()
                )
                ON CONFLICT (worker_type) DO UPDATE SET
                    last_run_id = CAST(:run_id AS uuid),
                    last_completed_at = now(),
                    last_status = :status,
                    active_run_id = NULL,
                    active_schedule_key = NULL,
                    active_started_at = NULL,
                    last_heartbeat_at = now(),
                    last_error = :error,
                    next_due_at_utc = :next_due_at_utc,
                    updated_at = now()
            """), {"worker_type": worker_type, "run_id": run_id, "status": status, "error": error, "next_due_at_utc": next_due_at_utc})

    def list_worker_states(self) -> list[dict[str, Any]]:
        with self.engine.begin() as conn:
            rows = conn.execute(text("SELECT * FROM ifa2.runtime_worker_state ORDER BY worker_type")).mappings().all()
            return [dict(r) for r in rows]

    def update_unified_run_governance(
        self,
        *,
        run_id: str,
        schedule_key: Optional[str],
        beijing_time_hm: Optional[str],
        runtime_budget_sec: Optional[int],
        duration_ms: Optional[int],
        tables_updated: list[str],
        tasks_executed: list[str],
        error_count: int,
        governance_state: str,
        status: Optional[str] = None,
        summary_patch: Optional[dict[str, Any]] = None,
    ) -> None:
        with self.engine.begin() as conn:
            current = conn.execute(text("SELECT summary FROM ifa2.unified_runtime_runs WHERE id = CAST(:id AS uuid)"), {"id": run_id}).scalar_one_or_none()
            merged = {}
            if current:
                merged = current if isinstance(current, dict) else json.loads(current)
            if summary_patch:
                merged.update(summary_patch)
            conn.execute(text("""
                UPDATE ifa2.unified_runtime_runs
                SET schedule_key=:schedule_key,
                    triggered_for_beijing_time=:beijing_time_hm,
                    runtime_budget_sec=:runtime_budget_sec,
                    duration_ms=:duration_ms,
                    tables_updated=CAST(:tables_updated AS jsonb),
                    tasks_executed=CAST(:tasks_executed AS jsonb),
                    error_count=:error_count,
                    governance_state=:governance_state,
                    status=COALESCE(:status, status),
                    summary=CAST(:summary AS jsonb)
                WHERE id = CAST(:id AS uuid)
            """), {
                "id": run_id,
                "schedule_key": schedule_key,
                "beijing_time_hm": beijing_time_hm,
                "runtime_budget_sec": runtime_budget_sec,
                "duration_ms": duration_ms,
                "tables_updated": json.dumps(tables_updated, ensure_ascii=False),
                "tasks_executed": json.dumps(tasks_executed, ensure_ascii=False),
                "error_count": error_count,
                "governance_state": governance_state,
                "status": status,
                "summary": json.dumps(merged, ensure_ascii=False),
            })

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.engine.begin() as conn:
            rows = conn.execute(text("""
                SELECT id, lane, worker_type, trigger_mode, schedule_key,
                       triggered_for_beijing_time, runtime_budget_sec, duration_ms,
                       governance_state, status, started_at, completed_at,
                       records_processed, error_count, tables_updated, tasks_executed, summary
                FROM ifa2.unified_runtime_runs
                ORDER BY started_at DESC
                LIMIT :limit
            """), {"limit": limit}).mappings().all()
            return [dict(r) for r in rows]


class UnifiedWorkerAdapter:
    def __init__(self) -> None:
        self.runtime = UnifiedRuntime()

    def run(
        self,
        worker_type: str,
        trigger_mode: str,
        schedule_key: Optional[str] = None,
        group_name: Optional[str] = None,
        dry_run_manifest_only: bool = False,
    ) -> dict[str, Any]:
        start = now_utc()
        runtime_budget_sec = None
        if worker_type == "archive":
            window_name = "manual_archive" if not schedule_key else schedule_key.replace(":", "_")
            result = self.runtime.run_once(
                "archive",
                trigger_mode=trigger_mode,
                archive_window=window_name,
                dry_run_manifest_only=dry_run_manifest_only,
            )
        else:
            result = self.runtime.run_once(
                worker_type,
                trigger_mode=trigger_mode,
                dry_run_manifest_only=dry_run_manifest_only,
            )
        end = now_utc()
        summary = dict(result.summary)
        tasks_executed = summary.get("planned_dataset_names") or summary.get("executed_jobs") or [worker_type]
        tables_updated = self._infer_tables_updated(worker_type)
        error_count = len([x for x in summary.get("dataset_results", []) if x.get("status") not in {"succeeded", "dry_run", "skeleton_ready"}])
        governance_state = "ok" if result.status in {"succeeded", "partial"} else "degraded"
        return {
            "run_id": result.run_id,
            "lane": worker_type,
            "status": result.status,
            "duration_ms": int((end - start).total_seconds() * 1000),
            "tasks_executed": tasks_executed,
            "tables_updated": tables_updated,
            "error_count": error_count,
            "governance_state": governance_state,
            "runtime_budget_sec": runtime_budget_sec,
            "summary_patch": {
                "unified_daemon_entry": True,
                "group_name": group_name,
                "schedule_key": schedule_key,
                "trigger_mode": trigger_mode,
                "dry_run_manifest_only": dry_run_manifest_only,
            },
        }

    def _infer_tables_updated(self, worker_type: str) -> list[str]:
        if worker_type == "archive":
            return ["ifa2.archive_runs", "ifa2.archive_checkpoints", "ifa2.archive_target_catchup"]
        if worker_type == "midfreq":
            return ["ifa2.job_runs", "ifa2.unified_runtime_runs", "ifa2.midfreq_execution_summary"]
        if worker_type == "highfreq":
            return ["ifa2.job_runs", "ifa2.unified_runtime_runs", "ifa2.highfreq_execution_summary"]
        return ["ifa2.job_runs", "ifa2.unified_runtime_runs"]


class UnifiedRuntimeDaemon:
    def __init__(self) -> None:
        self.store = UnifiedRuntimeDaemonStore()
        self.adapter = UnifiedWorkerAdapter()
        self.shutdown_requested = False
        self.calendar = TradingCalendarService()

    def bootstrap(self) -> None:
        self.store.seed_schedule_policy()

    def run_manual(
        self,
        worker_type: str,
        schedule_key: Optional[str] = None,
        dry_run_manifest_only: bool = False,
        runtime_budget_sec: Optional[int] = None,
    ) -> dict[str, Any]:
        self.bootstrap()
        return self._dispatch(
            worker_type=worker_type,
            trigger_mode="manual",
            schedule_key=schedule_key,
            dry_run_manifest_only=dry_run_manifest_only,
            runtime_budget_override_sec=runtime_budget_sec,
        )

    def run_due_once(self, current_time_utc: Optional[datetime] = None) -> list[dict[str, Any]]:
        self.bootstrap()
        now = current_time_utc or now_utc()
        now_bj = now.astimezone(BJ_TZ)
        day_type = self.calendar.get_runtime_day_type(now, exchange="SSE")
        due = self.store.due_schedules(now_bj, day_type=day_type)
        return [
            self._dispatch(
                worker_type=s["worker_type"],
                trigger_mode="scheduled",
                schedule_key=s["schedule_key"],
                schedule_row=s,
                current_time_utc=now,
                dry_run_manifest_only=False,
            )
            for s in due
        ]

    def run_loop(self, loop_interval_sec: int = 60) -> None:
        self.bootstrap()
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        while not self.shutdown_requested:
            self.run_due_once()
            time.sleep(loop_interval_sec)

    def status(self) -> dict[str, Any]:
        self.bootstrap()
        now = now_utc()
        day_type = self.calendar.get_runtime_day_type(now, exchange="SSE")
        trading_status = self.calendar.get_day_status(now.astimezone(BJ_TZ).date(), exchange="SSE")
        return {
            "daemon_name": "unified_runtime_daemon",
            "official_long_running_entry": "python3 -m ifa_data_platform.runtime.unified_daemon --loop",
            "now_utc": now.isoformat(),
            "now_beijing": now.astimezone(BJ_TZ).isoformat(),
            "runtime_day_type": day_type,
            "trading_day_status": {
                "as_of_date": str(trading_status.as_of_date),
                "exchange": trading_status.exchange,
                "is_trading_day": trading_status.is_trading_day,
                "pretrade_date": str(trading_status.pretrade_date) if trading_status.pretrade_date else None,
                "source": trading_status.source,
            },
            "schedules": self.store.list_schedules(enabled_only=False),
            "worker_states": self.store.list_worker_states(),
            "recent_runs": self.store.recent_runs(limit=20),
        }

    def _dispatch(
        self,
        *,
        worker_type: str,
        trigger_mode: str,
        schedule_key: Optional[str],
        schedule_row: Optional[dict[str, Any]] = None,
        current_time_utc: Optional[datetime] = None,
        dry_run_manifest_only: bool = False,
        runtime_budget_override_sec: Optional[int] = None,
    ) -> dict[str, Any]:
        start = current_time_utc or now_utc()
        runtime_budget_sec = runtime_budget_override_sec or int((schedule_row or {}).get("runtime_budget_sec") or self._default_budget(worker_type))
        state = self.store.get_worker_state(worker_type)
        if state and state.get("active_run_id"):
            active_started = state.get("active_started_at")
            if active_started and active_started.tzinfo is None:
                active_started = active_started.replace(tzinfo=timezone.utc)
            if active_started and (start - active_started).total_seconds() > runtime_budget_sec:
                self.store.update_unified_run_governance(
                    run_id=str(state["active_run_id"]),
                    schedule_key=state.get("active_schedule_key"),
                    beijing_time_hm=(schedule_row or {}).get("beijing_time_hm"),
                    runtime_budget_sec=runtime_budget_sec,
                    duration_ms=int((start - active_started).total_seconds() * 1000),
                    tables_updated=[],
                    tasks_executed=[],
                    error_count=1,
                    governance_state="timed_out",
                    status="timed_out",
                    summary_patch={"timeout_marked_by_unified_daemon": True},
                )
                self.store.mark_worker_finished(
                    worker_type=worker_type,
                    run_id=str(state["active_run_id"]),
                    status="timed_out",
                    error="marked timed_out by unified daemon overlap governance",
                )
            else:
                marker = self.adapter.runtime.run_once(worker_type, trigger_mode="scheduled_overlap_marker", dry_run_manifest_only=True)
                self.store.update_unified_run_governance(
                    run_id=marker.run_id,
                    schedule_key=schedule_key,
                    beijing_time_hm=(schedule_row or {}).get("beijing_time_hm"),
                    runtime_budget_sec=runtime_budget_sec,
                    duration_ms=0,
                    tables_updated=[],
                    tasks_executed=[],
                    error_count=1,
                    governance_state="overlap_conflict",
                    status="overlap_conflict",
                    summary_patch={"reason": "active prior run exists", "worker_type": worker_type},
                )
                return {
                    "run_id": marker.run_id,
                    "lane": worker_type,
                    "status": "overlap_conflict",
                    "duration_ms": 0,
                    "tasks_executed": [],
                    "tables_updated": [],
                    "error_count": 1,
                    "governance_state": "overlap_conflict",
                }

        result = self.adapter.run(
            worker_type,
            trigger_mode=trigger_mode,
            schedule_key=schedule_key,
            group_name=(schedule_row or {}).get("group_name"),
            dry_run_manifest_only=dry_run_manifest_only,
        )
        self.store.mark_worker_running(worker_type=worker_type, run_id=result["run_id"], schedule_key=schedule_key, trigger_mode=trigger_mode)
        self.store.update_unified_run_governance(
            run_id=result["run_id"],
            schedule_key=schedule_key,
            beijing_time_hm=(schedule_row or {}).get("beijing_time_hm"),
            runtime_budget_sec=runtime_budget_sec,
            duration_ms=result["duration_ms"],
            tables_updated=result["tables_updated"],
            tasks_executed=result["tasks_executed"],
            error_count=result["error_count"],
            governance_state=result["governance_state"],
            status=result["status"],
            summary_patch={
                "automatic_entry": trigger_mode == "scheduled",
                "worker_type": worker_type,
                "runtime_budget_sec": runtime_budget_sec,
                "day_type": (schedule_row or {}).get("day_type"),
                "purpose": (schedule_row or {}).get("purpose"),
            },
        )
        self.store.mark_worker_finished(
            worker_type=worker_type,
            run_id=result["run_id"],
            status=result["status"],
            error=None if result["error_count"] == 0 else "see unified_runtime_runs.summary",
            next_due_at_utc=self._next_due_at_utc(worker_type, start),
        )
        return result

    def _default_budget(self, worker_type: str) -> int:
        return {
            "lowfreq": 1800,
            "midfreq": 1800,
            "highfreq": 900,
            "archive": 3600,
        }[worker_type]

    def _next_due_at_utc(self, worker_type: str, base_utc: datetime) -> Optional[datetime]:
        schedules = [s for s in self.store.list_schedules(enabled_only=True) if s["worker_type"] == worker_type and s["beijing_time_hm"]]
        if not schedules:
            return None
        base_bj = base_utc.astimezone(BJ_TZ)
        candidates: list[datetime] = []
        for s in schedules:
            hh, mm = map(int, s["beijing_time_hm"].split(":"))
            for add_days in range(0, 8):
                d = (base_bj + timedelta(days=add_days)).date()
                candidate = datetime(d.year, d.month, d.day, hh, mm, tzinfo=BJ_TZ)
                runtime_day_type = self.calendar.get_runtime_day_type(candidate.astimezone(timezone.utc), exchange="SSE")
                if runtime_day_type != s["day_type"]:
                    continue
                if candidate <= base_bj:
                    continue
                candidates.append(candidate.astimezone(timezone.utc))
                break
        return min(candidates) if candidates else None

    def _signal_handler(self, signum, frame) -> None:
        self.shutdown_requested = True
        sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified runtime/data-collector daemon (official long-running entry)")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--worker", choices=["lowfreq", "midfreq", "highfreq", "archive"])
    parser.add_argument("--schedule-key", type=str)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--dry-run-manifest-only", action="store_true")
    parser.add_argument("--runtime-budget-sec", type=int)
    parser.add_argument("--loop-interval-sec", type=int, default=60)
    args = parser.parse_args()

    daemon = UnifiedRuntimeDaemon()
    if args.status:
        print(json.dumps(daemon.status(), ensure_ascii=False, indent=2, default=str))
        return
    if args.worker:
        print(json.dumps(daemon.run_manual(args.worker, schedule_key=args.schedule_key, dry_run_manifest_only=args.dry_run_manifest_only, runtime_budget_sec=args.runtime_budget_sec), ensure_ascii=False, indent=2, default=str))
        return
    if args.once:
        print(json.dumps(daemon.run_due_once(), ensure_ascii=False, indent=2, default=str))
        return
    daemon.run_loop(loop_interval_sec=args.loop_interval_sec)


if __name__ == "__main__":
    main()
