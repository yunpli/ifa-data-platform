from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine

BJ_TZ = ZoneInfo("Asia/Shanghai")
UTC = timezone.utc

SLOT_DEFINITIONS: dict[str, dict[str, Any]] = {
    "early": {
        "label": "pre-open / early-support",
        "observed_cutoff": time(9, 30),
        "lanes": ["lowfreq", "midfreq", "highfreq"],
    },
    "mid": {
        "label": "midday / intraday-support",
        "observed_cutoff": time(13, 30),
        "lanes": ["lowfreq", "midfreq", "highfreq"],
    },
    "late": {
        "label": "post-close / final-support",
        "observed_cutoff": time(17, 30),
        "lanes": ["lowfreq", "midfreq", "highfreq", "archive_v2"],
    },
}

DATASET_TABLE_HINTS: dict[str, dict[str, str]] = {
    "trade_cal": {"table": "trade_cal_current", "timestamp_expr": "max(cal_date)::text", "version_column": "version_id"},
    "stock_basic": {"table": "stock_basic_current", "timestamp_expr": "max(list_date)::text", "version_column": "version_id"},
    "index_basic": {"table": "index_basic_current", "timestamp_expr": "max(list_date)::text", "version_column": "version_id"},
    "fund_basic_etf": {"table": "fund_basic_etf_current", "timestamp_expr": "max(list_date)::text", "version_column": "version_id"},
    "sw_industry_mapping": {"table": "sw_industry_mapping_current", "timestamp_expr": "max(index_code)::text", "version_column": "version_id"},
    "announcements": {"table": "announcements_current", "timestamp_expr": "max(ann_date)::text", "version_column": "version_id"},
    "news": {"table": "news_current", "timestamp_expr": "max(pub_time)::text", "version_column": "version_id"},
    "research_reports": {"table": "research_reports_current", "timestamp_expr": "max(pub_date)::text", "version_column": "version_id"},
    "investor_qa": {"table": "investor_qa_current", "timestamp_expr": "max(pub_date)::text", "version_column": "version_id"},
    "index_weight": {"table": "index_weight_current", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "etf_daily_basic": {"table": "etf_daily_basic_current", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "share_float": {"table": "share_float_current", "timestamp_expr": "max(float_date)::text", "version_column": "version_id"},
    "company_basic": {"table": "company_basic_current", "timestamp_expr": "max(ts_code)::text", "version_column": "version_id"},
    "stk_managers": {"table": "stk_managers_current", "timestamp_expr": "max(ann_date)::text", "version_column": "version_id"},
    "new_share": {"table": "new_share_current", "timestamp_expr": "max(ipo_date)::text", "version_column": "version_id"},
    "name_change": {"table": "name_change_current", "timestamp_expr": "max(start_date)::text", "version_column": "version_id"},
    "top10_holders": {"table": "top10_holders_current", "timestamp_expr": "max(end_date)::text", "version_column": "version_id"},
    "top10_floatholders": {"table": "top10_floatholders_current", "timestamp_expr": "max(end_date)::text", "version_column": "version_id"},
    "pledge_stat": {"table": "pledge_stat_current", "timestamp_expr": "max(end_date)::text", "version_column": "version_id"},
    "equity_daily_bar": {"table": "equity_daily_bar_history", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "index_daily_bar": {"table": "index_daily_bar_history", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "etf_daily_bar": {"table": "etf_daily_bar_history", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "northbound_flow": {"table": "northbound_flow_history", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "limit_up_down_status": {"table": "limit_up_down_status_history", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "margin_financing": {"table": "margin_financing_history", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "southbound_flow": {"table": "southbound_flow_history", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "turnover_rate": {"table": "turnover_rate_history", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "main_force_flow": {"table": "main_force_flow_history", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "sector_performance": {"table": "sector_performance_history", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "dragon_tiger_list": {"table": "dragon_tiger_list_history", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "limit_up_detail": {"table": "limit_up_detail_history", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "stock_1m_ohlcv": {"table": "highfreq_stock_1m_working", "timestamp_expr": "max(trade_time)::text", "version_column": "version_id"},
    "index_1m_ohlcv": {"table": "highfreq_index_1m_working", "timestamp_expr": "max(trade_time)::text", "version_column": "version_id"},
    "etf_sector_style_1m_ohlcv": {"table": "highfreq_proxy_1m_working", "timestamp_expr": "max(trade_time)::text", "version_column": "version_id"},
    "futures_commodity_pm_1m_ohlcv": {"table": "highfreq_futures_minute_working", "timestamp_expr": "max(trade_time)::text", "version_column": "version_id"},
    "open_auction_snapshot": {"table": "highfreq_open_auction_working", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "close_auction_snapshot": {"table": "highfreq_close_auction_working", "timestamp_expr": "max(trade_date)::text", "version_column": "version_id"},
    "event_time_stream": {"table": "highfreq_event_stream_working", "timestamp_expr": "max(event_time)::text", "version_column": "version_id"},
}

SCHEMA_DDL = [
    """
    CREATE TABLE IF NOT EXISTS ifa2.slot_replay_evidence (
        id uuid PRIMARY KEY,
        trade_date date NOT NULL,
        slot_key varchar(32) NOT NULL,
        perspective varchar(32) NOT NULL,
        capture_reason varchar(64) NOT NULL,
        slot_label text NOT NULL,
        slot_cutoff_beijing varchar(5),
        captured_at timestamptz NOT NULL DEFAULT now(),
        primary_manifest_snapshot_id uuid NULL REFERENCES ifa2.target_manifest_snapshots(id) ON DELETE SET NULL,
        primary_manifest_hash varchar(64),
        selection_policy jsonb NOT NULL DEFAULT '{}'::jsonb,
        manifest_context jsonb NOT NULL DEFAULT '{}'::jsonb,
        trigger_context jsonb NOT NULL DEFAULT '{}'::jsonb,
        worker_context jsonb NOT NULL DEFAULT '{}'::jsonb,
        dataset_context jsonb NOT NULL DEFAULT '{}'::jsonb,
        snapshot_context jsonb NOT NULL DEFAULT '{}'::jsonb,
        artifact_context jsonb NOT NULL DEFAULT '{}'::jsonb,
        notes text,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ifa2.slot_replay_evidence_runs (
        id uuid PRIMARY KEY,
        evidence_id uuid NOT NULL REFERENCES ifa2.slot_replay_evidence(id) ON DELETE CASCADE,
        run_id uuid NOT NULL REFERENCES ifa2.unified_runtime_runs(id) ON DELETE CASCADE,
        lane varchar(32) NOT NULL,
        role varchar(32) NOT NULL DEFAULT 'source_run',
        selection_rank integer NOT NULL DEFAULT 0,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (evidence_id, run_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_slot_replay_evidence_lookup ON ifa2.slot_replay_evidence (trade_date, slot_key, perspective, captured_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_slot_replay_evidence_runs_evidence ON ifa2.slot_replay_evidence_runs (evidence_id, selection_rank)",
]


@dataclass(frozen=True)
class ReportArtifactRef:
    status: str
    producer: str
    path: Optional[str]
    sha256: Optional[str]
    content_type: Optional[str]
    bytes: Optional[int]
    generated_at: Optional[str]
    note: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "producer": self.producer,
            "path": self.path,
            "sha256": self.sha256,
            "content_type": self.content_type,
            "bytes": self.bytes,
            "generated_at": self.generated_at,
            "note": self.note,
        }


class ReplayEvidenceStore:
    def __init__(self) -> None:
        self.engine = make_engine()

    def ensure_schema(self) -> None:
        with self.engine.begin() as conn:
            for ddl in SCHEMA_DDL:
                conn.execute(text(ddl))

    def capture_slot_evidence(
        self,
        *,
        trade_date: str,
        slot_key: str,
        perspective: str = "observed",
        capture_reason: str = "manual_capture",
        artifact: Optional[ReportArtifactRef] = None,
        run_ids: Optional[list[str]] = None,
        schedule_keys: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        self.ensure_schema()
        slot_def = _slot_definition(slot_key)
        selected_runs = self._select_runs(
            trade_date=trade_date,
            slot_key=slot_key,
            perspective=perspective,
            explicit_run_ids=run_ids or [],
            explicit_schedule_keys=schedule_keys or [],
        )
        manifest_context = self._build_manifest_context(selected_runs)
        dataset_context = self._build_dataset_context(selected_runs)
        worker_context = self._build_worker_context(selected_runs)
        trigger_context = self._build_trigger_context(selected_runs)
        snapshot_context = self._build_snapshot_context(dataset_context)
        selection_policy = {
            "slot_key": slot_key,
            "perspective": perspective,
            "capture_reason": capture_reason,
            "lanes": slot_def["lanes"],
            "explicit_run_ids": run_ids or [],
            "explicit_schedule_keys": schedule_keys or [],
            "selected_run_count": len(selected_runs),
            "selection_mode": "explicit" if (run_ids or schedule_keys) else "slot_inference",
        }
        artifact_payload = (artifact or placeholder_artifact(slot_key=slot_key, trade_date=trade_date)).to_dict()
        primary_manifest_id = manifest_context.get("primary_manifest_snapshot_id")
        primary_manifest_hash = manifest_context.get("primary_manifest_hash")

        evidence_id = str(uuid.uuid4())
        captured_at = datetime.now(UTC)
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.slot_replay_evidence (
                        id, trade_date, slot_key, perspective, capture_reason,
                        slot_label, slot_cutoff_beijing, captured_at,
                        primary_manifest_snapshot_id, primary_manifest_hash,
                        selection_policy, manifest_context, trigger_context,
                        worker_context, dataset_context, snapshot_context,
                        artifact_context, notes
                    ) VALUES (
                        :id, :trade_date, :slot_key, :perspective, :capture_reason,
                        :slot_label, :slot_cutoff_beijing, :captured_at,
                        CAST(:primary_manifest_snapshot_id AS uuid), :primary_manifest_hash,
                        CAST(:selection_policy AS jsonb), CAST(:manifest_context AS jsonb), CAST(:trigger_context AS jsonb),
                        CAST(:worker_context AS jsonb), CAST(:dataset_context AS jsonb), CAST(:snapshot_context AS jsonb),
                        CAST(:artifact_context AS jsonb), :notes
                    )
                    """
                ),
                {
                    "id": evidence_id,
                    "trade_date": trade_date,
                    "slot_key": slot_key,
                    "perspective": perspective,
                    "capture_reason": capture_reason,
                    "slot_label": slot_def["label"],
                    "slot_cutoff_beijing": slot_def["observed_cutoff"].strftime("%H:%M"),
                    "captured_at": captured_at,
                    "primary_manifest_snapshot_id": primary_manifest_id,
                    "primary_manifest_hash": primary_manifest_hash,
                    "selection_policy": json.dumps(selection_policy, ensure_ascii=False),
                    "manifest_context": json.dumps(manifest_context, ensure_ascii=False),
                    "trigger_context": json.dumps(trigger_context, ensure_ascii=False),
                    "worker_context": json.dumps(worker_context, ensure_ascii=False),
                    "dataset_context": json.dumps(dataset_context, ensure_ascii=False),
                    "snapshot_context": json.dumps(snapshot_context, ensure_ascii=False),
                    "artifact_context": json.dumps(artifact_payload, ensure_ascii=False),
                    "notes": notes,
                },
            )
            for idx, run in enumerate(selected_runs, start=1):
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.slot_replay_evidence_runs (
                            id, evidence_id, run_id, lane, role, selection_rank
                        ) VALUES (
                            :id, CAST(:evidence_id AS uuid), CAST(:run_id AS uuid), :lane, 'source_run', :selection_rank
                        )
                        ON CONFLICT (evidence_id, run_id) DO NOTHING
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "evidence_id": evidence_id,
                        "run_id": str(run["id"]),
                        "lane": run["lane"],
                        "selection_rank": idx,
                    },
                )
        return self.get_evidence(evidence_id) or {"id": evidence_id}

    def list_evidence(self, *, trade_date: Optional[str] = None, slot_key: Optional[str] = None, perspective: Optional[str] = None, limit: int = 20) -> list[dict[str, Any]]:
        self.ensure_schema()
        sql = """
            SELECT id, trade_date, slot_key, perspective, capture_reason, captured_at,
                   primary_manifest_hash, artifact_context,
                   jsonb_array_length(COALESCE(dataset_context->'datasets', '[]'::jsonb)) AS dataset_count
            FROM ifa2.slot_replay_evidence
            WHERE 1=1
        """
        params: dict[str, Any] = {"limit": limit}
        if trade_date:
            sql += " AND trade_date = CAST(:trade_date AS date)"
            params["trade_date"] = trade_date
        if slot_key:
            sql += " AND slot_key = :slot_key"
            params["slot_key"] = slot_key
        if perspective:
            sql += " AND perspective = :perspective"
            params["perspective"] = perspective
        sql += " ORDER BY captured_at DESC LIMIT :limit"
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
            return [dict(r) for r in rows]

    def get_evidence(self, evidence_id: str) -> Optional[dict[str, Any]]:
        self.ensure_schema()
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT e.*, COALESCE(
                        (
                            SELECT jsonb_agg(jsonb_build_object(
                                'run_id', r.run_id,
                                'lane', r.lane,
                                'role', r.role,
                                'selection_rank', r.selection_rank
                            ) ORDER BY r.selection_rank)
                            FROM ifa2.slot_replay_evidence_runs r
                            WHERE r.evidence_id = e.id
                        ),
                        '[]'::jsonb
                    ) AS linked_runs
                    FROM ifa2.slot_replay_evidence e
                    WHERE e.id = CAST(:id AS uuid)
                    """
                ),
                {"id": evidence_id},
            ).mappings().first()
            return dict(row) if row else None

    def capture_runtime_run_evidence(
        self,
        *,
        run_id: str,
        slot_key: str,
        perspective: str,
        capture_reason: str = "runtime_auto_capture",
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        self.ensure_schema()
        run = self._load_run(run_id)
        if not run:
            raise ValueError(f"Runtime run not found: {run_id}")
        trade_date = self._infer_trade_date(run)
        artifact = placeholder_artifact(slot_key=slot_key, trade_date=trade_date)
        return self.capture_slot_evidence(
            trade_date=trade_date,
            slot_key=slot_key,
            perspective=perspective,
            capture_reason=capture_reason,
            artifact=artifact,
            run_ids=[run_id],
            notes=notes,
        )

    def _load_run(self, run_id: str) -> Optional[dict[str, Any]]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, lane, worker_type, trigger_mode, schedule_key,
                           triggered_for_beijing_time, runtime_budget_sec, duration_ms,
                           governance_state, status, started_at, completed_at,
                           records_processed, error_count, tables_updated, tasks_executed,
                           manifest_snapshot_id, manifest_hash, summary
                    FROM ifa2.unified_runtime_runs
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {"id": run_id},
            ).mappings().first()
            return dict(row) if row else None

    def _infer_trade_date(self, run: dict[str, Any]) -> str:
        summary = run.get("summary") or {}
        if not isinstance(summary, dict):
            try:
                summary = json.loads(summary)
            except Exception:
                summary = {}
        if summary.get("business_date"):
            return str(summary["business_date"])
        started_at = run.get("started_at")
        if isinstance(started_at, datetime):
            ts = started_at if started_at.tzinfo else started_at.replace(tzinfo=UTC)
            return ts.astimezone(BJ_TZ).date().isoformat()
        if started_at:
            parsed = datetime.fromisoformat(str(started_at))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(BJ_TZ).date().isoformat()
        raise ValueError(f"Unable to infer trade_date for runtime run {run.get('id')}")

    def _select_runs(
        self,
        *,
        trade_date: str,
        slot_key: str,
        perspective: str,
        explicit_run_ids: list[str],
        explicit_schedule_keys: list[str],
    ) -> list[dict[str, Any]]:
        slot_def = _slot_definition(slot_key)
        if explicit_run_ids:
            sql = """
                SELECT id, lane, worker_type, trigger_mode, schedule_key,
                       triggered_for_beijing_time, runtime_budget_sec, duration_ms,
                       governance_state, status, started_at, completed_at,
                       records_processed, error_count, tables_updated, tasks_executed,
                       manifest_snapshot_id, manifest_hash, summary
                FROM ifa2.unified_runtime_runs
                WHERE id = ANY(CAST(:run_ids AS uuid[]))
                ORDER BY started_at ASC
            """
            with self.engine.begin() as conn:
                rows = conn.execute(text(sql), {"run_ids": explicit_run_ids}).mappings().all()
                return [dict(r) for r in rows]

        with self.engine.begin() as conn:
            if explicit_schedule_keys:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, lane, worker_type, trigger_mode, schedule_key,
                               triggered_for_beijing_time, runtime_budget_sec, duration_ms,
                               governance_state, status, started_at, completed_at,
                               records_processed, error_count, tables_updated, tasks_executed,
                               manifest_snapshot_id, manifest_hash, summary
                        FROM ifa2.unified_runtime_runs
                        WHERE schedule_key = ANY(:schedule_keys)
                          AND date(started_at + interval '8 hours') = CAST(:trade_date AS date)
                        ORDER BY started_at ASC
                        """
                    ),
                    {"schedule_keys": explicit_schedule_keys, "trade_date": trade_date},
                ).mappings().all()
                return [dict(r) for r in rows]

            if perspective not in {"observed", "corrected"}:
                raise ValueError(f"Unsupported perspective: {perspective}")

            if perspective == "observed":
                selected: list[dict[str, Any]] = []
                cutoff = slot_def["observed_cutoff"].strftime("%H:%M")
                for lane in slot_def["lanes"]:
                    row = conn.execute(
                        text(
                            """
                            SELECT id, lane, worker_type, trigger_mode, schedule_key,
                                   triggered_for_beijing_time, runtime_budget_sec, duration_ms,
                                   governance_state, status, started_at, completed_at,
                                   records_processed, error_count, tables_updated, tasks_executed,
                                   manifest_snapshot_id, manifest_hash, summary
                            FROM ifa2.unified_runtime_runs
                            WHERE lane = :lane
                              AND status IN ('succeeded', 'partial')
                              AND date(started_at + interval '8 hours') = CAST(:trade_date AS date)
                              AND to_char(started_at + interval '8 hours', 'HH24:MI') <= :cutoff
                            ORDER BY started_at DESC
                            LIMIT 1
                            """
                        ),
                        {"lane": lane, "trade_date": trade_date, "cutoff": cutoff},
                    ).mappings().first()
                    if row:
                        selected.append(dict(row))
                return selected

            selected = []
            for lane in slot_def["lanes"]:
                row = conn.execute(
                    text(
                        """
                        SELECT id, lane, worker_type, trigger_mode, schedule_key,
                               triggered_for_beijing_time, runtime_budget_sec, duration_ms,
                               governance_state, status, started_at, completed_at,
                               records_processed, error_count, tables_updated, tasks_executed,
                               manifest_snapshot_id, manifest_hash, summary
                        FROM ifa2.unified_runtime_runs
                        WHERE lane = :lane
                          AND status IN ('succeeded', 'partial')
                          AND (
                                date(started_at + interval '8 hours') = CAST(:trade_date AS date)
                             OR coalesce(summary->>'business_date', '') = :trade_date
                          )
                        ORDER BY completed_at DESC NULLS LAST, started_at DESC
                        LIMIT 1
                        """
                    ),
                    {"lane": lane, "trade_date": trade_date},
                ).mappings().first()
                if row:
                    selected.append(dict(row))
            return selected

    def _build_manifest_context(self, selected_runs: list[dict[str, Any]]) -> dict[str, Any]:
        manifest_ids = [str(r["manifest_snapshot_id"]) for r in selected_runs if r.get("manifest_snapshot_id")]
        manifests: list[dict[str, Any]] = []
        if manifest_ids:
            with self.engine.begin() as conn:
                rows = conn.execute(
                    text(
                        """
                        SELECT id, manifest_hash, generated_at, owner_type, owner_id, selector_scope, item_count, payload
                        FROM ifa2.target_manifest_snapshots
                        WHERE id = ANY(CAST(:ids AS uuid[]))
                        ORDER BY generated_at DESC
                        """
                    ),
                    {"ids": manifest_ids},
                ).mappings().all()
                manifests = [
                    {
                        "id": str(row["id"]),
                        "manifest_hash": row["manifest_hash"],
                        "generated_at": _iso(row["generated_at"]),
                        "owner_type": row["owner_type"],
                        "owner_id": row["owner_id"],
                        "selector_scope": row["selector_scope"],
                        "item_count": row["item_count"],
                    }
                    for row in rows
                ]
        primary = manifests[0] if manifests else None
        return {
            "primary_manifest_snapshot_id": primary["id"] if primary else None,
            "primary_manifest_hash": primary["manifest_hash"] if primary else None,
            "manifest_count": len(manifests),
            "manifests": manifests,
            "selected_manifest_snapshot_ids": manifest_ids,
        }

    def _build_trigger_context(self, selected_runs: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "trigger_modes": sorted({r.get("trigger_mode") for r in selected_runs if r.get("trigger_mode")}),
            "schedule_keys": [r.get("schedule_key") for r in selected_runs if r.get("schedule_key")],
            "triggered_for_beijing_times": [r.get("triggered_for_beijing_time") for r in selected_runs if r.get("triggered_for_beijing_time")],
        }

    def _build_worker_context(self, selected_runs: list[dict[str, Any]]) -> dict[str, Any]:
        workers = []
        for row in selected_runs:
            workers.append(
                {
                    "run_id": str(row["id"]),
                    "lane": row.get("lane"),
                    "worker_type": row.get("worker_type"),
                    "status": row.get("status"),
                    "schedule_key": row.get("schedule_key"),
                    "governance_state": row.get("governance_state"),
                    "runtime_budget_sec": row.get("runtime_budget_sec"),
                    "duration_ms": row.get("duration_ms"),
                    "records_processed": row.get("records_processed"),
                    "error_count": row.get("error_count"),
                    "started_at": _iso(row.get("started_at")),
                    "completed_at": _iso(row.get("completed_at")),
                    "tables_updated": row.get("tables_updated") or [],
                    "tasks_executed": row.get("tasks_executed") or [],
                }
            )
        return {
            "selected_runs": workers,
            "lane_count": len({w["lane"] for w in workers}),
            "worker_count": len(workers),
        }

    def _build_dataset_context(self, selected_runs: list[dict[str, Any]]) -> dict[str, Any]:
        datasets: dict[tuple[str, str], dict[str, Any]] = {}
        for row in selected_runs:
            summary = row.get("summary") or {}
            if not isinstance(summary, dict):
                try:
                    summary = json.loads(summary)
                except Exception:
                    summary = {}
            for item in summary.get("dataset_results") or []:
                key = (row["lane"], item.get("dataset_name") or "unknown")
                datasets[key] = {
                    "lane": row["lane"],
                    "run_id": str(row["id"]),
                    "dataset_name": item.get("dataset_name"),
                    "status": item.get("status"),
                    "records_processed": int(item.get("records_processed") or 0),
                    "watermark": item.get("watermark"),
                    "error_message": item.get("error_message"),
                }
            for family in summary.get("nightly_family_set") or []:
                key = (row["lane"], family)
                datasets.setdefault(
                    key,
                    {
                        "lane": row["lane"],
                        "run_id": str(row["id"]),
                        "dataset_name": family,
                        "status": summary.get("archive_v2_status") or row.get("status"),
                        "records_processed": 0,
                        "watermark": summary.get("business_date"),
                        "error_message": None,
                    },
                )
        ordered = sorted(datasets.values(), key=lambda d: (d["lane"], d["dataset_name"] or ""))
        return {"dataset_count": len(ordered), "datasets": ordered}

    def _build_snapshot_context(self, dataset_context: dict[str, Any]) -> dict[str, Any]:
        snapshots = []
        datasets = dataset_context.get("datasets") or []
        with self.engine.begin() as conn:
            for item in datasets:
                dataset_name = item.get("dataset_name")
                hint = DATASET_TABLE_HINTS.get(dataset_name or "")
                if not hint:
                    continue
                table = hint["table"]
                if not self._table_exists(conn, table):
                    continue
                version_col = hint.get("version_column")
                version_expr = f", max(({version_col})::text) as latest_version_id" if version_col and self._column_exists(conn, table, version_col) else ", null::text as latest_version_id"
                ts_expr = hint.get("timestamp_expr", "null::text")
                try:
                    with conn.begin_nested():
                        row = conn.execute(
                            text(f"SELECT count(*)::bigint AS row_count, {ts_expr} AS latest_observed_value {version_expr} FROM ifa2.{table}")
                        ).mappings().first()
                except Exception as exc:
                    snapshots.append(
                        {
                            "dataset_name": dataset_name,
                            "table": f"ifa2.{table}",
                            "row_count": None,
                            "latest_observed_value": None,
                            "latest_version_id": None,
                            "probe_error": str(exc),
                        }
                    )
                    continue
                snapshots.append(
                    {
                        "dataset_name": dataset_name,
                        "table": f"ifa2.{table}",
                        "row_count": int(row["row_count"] or 0),
                        "latest_observed_value": row["latest_observed_value"],
                        "latest_version_id": row.get("latest_version_id"),
                    }
                )
        return {"snapshot_count": len(snapshots), "snapshots": snapshots}

    def _table_exists(self, conn, table_name: str) -> bool:
        return bool(
            conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema='ifa2' AND table_name=:table_name
                    )
                    """
                ),
                {"table_name": table_name},
            ).scalar()
        )

    def _column_exists(self, conn, table_name: str, column_name: str) -> bool:
        return bool(
            conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema='ifa2' AND table_name=:table_name AND column_name=:column_name
                    )
                    """
                ),
                {"table_name": table_name, "column_name": column_name},
            ).scalar()
        )


def placeholder_artifact(*, slot_key: str, trade_date: str) -> ReportArtifactRef:
    return ReportArtifactRef(
        status="pending_integration",
        producer="slot_replay_evidence",
        path=None,
        sha256=None,
        content_type=None,
        bytes=None,
        generated_at=datetime.now(UTC).isoformat(),
        note=f"No report artifact path was supplied for {trade_date} {slot_key}; contract placeholder preserved for later report-layer integration.",
    )



def artifact_from_path(path: str, *, producer: str = "manual") -> ReportArtifactRef:
    p = Path(path)
    if not p.exists():
        return ReportArtifactRef(
            status="missing",
            producer=producer,
            path=str(p),
            sha256=None,
            content_type=None,
            bytes=None,
            generated_at=None,
            note="Artifact path does not exist at capture time.",
        )
    content = p.read_bytes()
    sha = hashlib.sha256(content).hexdigest()
    suffix = p.suffix.lower()
    content_type = {
        ".html": "text/html",
        ".md": "text/markdown",
        ".json": "application/json",
        ".pdf": "application/pdf",
    }.get(suffix, "application/octet-stream")
    generated_at = datetime.fromtimestamp(p.stat().st_mtime, tz=UTC).isoformat()
    return ReportArtifactRef(
        status="present",
        producer=producer,
        path=str(p),
        sha256=sha,
        content_type=content_type,
        bytes=len(content),
        generated_at=generated_at,
        note=None,
    )



def _slot_definition(slot_key: str) -> dict[str, Any]:
    if slot_key not in SLOT_DEFINITIONS:
        raise ValueError(f"Unsupported slot: {slot_key}")
    return SLOT_DEFINITIONS[slot_key]



def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat()
    return str(value)
