"""Unified runtime substrate for Trailblazer lanes.

This implementation batch provides:
- one-shot manifest-driven lane execution
- run-state/audit via both job_runs and unified_runtime_runs
- manifest snapshot persistence
- archive catch-up evidence persistence
- manifest-aware lowfreq/midfreq dataset planning
- a single entrypoint for lowfreq / midfreq / archive bounded rounds
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

from ifa_data_platform.archive.archive_config import get_archive_config
from ifa_data_platform.archive.archive_orchestrator import ArchiveOrchestrator
from ifa_data_platform.archive.archive_target_delta import (
    ArchiveDeltaItem,
    build_archive_manifest,
    diff_archive_manifests,
)
from ifa_data_platform.config.settings import get_settings
from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.lowfreq.registry import DatasetRegistry
from ifa_data_platform.lowfreq.runner import LowFreqRunner
from ifa_data_platform.midfreq.registry import MidfreqDatasetRegistry
from ifa_data_platform.midfreq.runner import MidfreqRunner
from ifa_data_platform.runtime.target_manifest import (
    SelectorScope,
    TargetManifest,
    TargetManifestItem,
    build_target_manifest,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UnifiedRunResult:
    run_id: str
    lane: str
    worker_type: str
    trigger_mode: str
    manifest_id: str
    manifest_hash: str
    status: str
    started_at: str
    completed_at: str
    records_processed: int
    summary: dict[str, Any]


@dataclass
class DatasetExecutionResult:
    dataset_name: str
    status: str
    records_processed: int
    watermark: Optional[str]
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "status": self.status,
            "records_processed": self.records_processed,
            "watermark": self.watermark,
            "error_message": self.error_message,
        }


class UnifiedRuntimeStore:
    """Persist unified runtime runs and Trailblazer artifacts."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def create_run(
        self,
        *,
        lane: str,
        worker_type: str,
        trigger_mode: str,
        manifest: TargetManifest,
        manifest_snapshot_id: str,
    ) -> str:
        run_id = str(uuid.uuid4())
        started_at = now_utc()
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.job_runs (
                        id, job_name, status, started_at, records_processed, created_at
                    ) VALUES (
                        :id, :job_name, 'running', :started_at, 0, :created_at
                    )
                    """
                ),
                {
                    "id": run_id,
                    "job_name": f"unified_runtime:{lane}",
                    "started_at": started_at,
                    "created_at": started_at,
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.unified_runtime_runs (
                        id, lane, worker_type, trigger_mode, manifest_snapshot_id,
                        manifest_id, manifest_hash, status, started_at,
                        records_processed, created_at
                    ) VALUES (
                        :id, :lane, :worker_type, :trigger_mode, :manifest_snapshot_id,
                        :manifest_id, :manifest_hash, 'running', :started_at,
                        0, :created_at
                    )
                    """
                ),
                {
                    "id": run_id,
                    "lane": lane,
                    "worker_type": worker_type,
                    "trigger_mode": trigger_mode,
                    "manifest_snapshot_id": manifest_snapshot_id,
                    "manifest_id": manifest.manifest_id,
                    "manifest_hash": manifest.manifest_hash,
                    "started_at": started_at,
                    "created_at": started_at,
                },
            )
        return run_id

    def finalize_run(
        self,
        *,
        run_id: str,
        lane: str,
        worker_type: str,
        trigger_mode: str,
        manifest_id: str,
        manifest_hash: str,
        manifest_snapshot_id: str,
        status: str,
        records_processed: int,
        summary: dict[str, Any],
    ) -> None:
        completed_at = now_utc()
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE ifa2.job_runs
                    SET status = :status,
                        completed_at = :completed_at,
                        records_processed = :records_processed,
                        error_message = :summary
                    WHERE id = :id
                    """
                ),
                {
                    "id": run_id,
                    "status": status,
                    "completed_at": completed_at,
                    "records_processed": records_processed,
                    "summary": json.dumps(summary, ensure_ascii=False),
                },
            )
            conn.execute(
                text(
                    """
                    UPDATE ifa2.unified_runtime_runs
                    SET lane = :lane,
                        worker_type = :worker_type,
                        trigger_mode = :trigger_mode,
                        manifest_snapshot_id = :manifest_snapshot_id,
                        manifest_id = :manifest_id,
                        manifest_hash = :manifest_hash,
                        status = :status,
                        completed_at = :completed_at,
                        records_processed = :records_processed,
                        summary = CAST(:summary AS jsonb)
                    WHERE id = :id
                    """
                ),
                {
                    "id": run_id,
                    "lane": lane,
                    "worker_type": worker_type,
                    "trigger_mode": trigger_mode,
                    "manifest_snapshot_id": manifest_snapshot_id,
                    "manifest_id": manifest_id,
                    "manifest_hash": manifest_hash,
                    "status": status,
                    "completed_at": completed_at,
                    "records_processed": records_processed,
                    "summary": json.dumps(summary, ensure_ascii=False),
                },
            )

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, job_name, status, started_at, completed_at, error_message, records_processed, created_at
                    FROM ifa2.job_runs
                    WHERE id = :id
                    """
                ),
                {"id": run_id},
            ).mappings().first()
            return dict(row) if row else None

    def get_unified_run(self, run_id: str) -> Optional[dict[str, Any]]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, lane, worker_type, trigger_mode, manifest_snapshot_id,
                           manifest_id, manifest_hash, status, started_at,
                           completed_at, records_processed, summary, created_at
                    FROM ifa2.unified_runtime_runs
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {"id": run_id},
            ).mappings().first()
            return dict(row) if row else None

    def list_unified_runs(self, limit: int = 10, lane: Optional[str] = None) -> list[dict[str, Any]]:
        sql = """
            SELECT id, lane, worker_type, trigger_mode, manifest_snapshot_id,
                   manifest_id, manifest_hash, status, started_at,
                   completed_at, records_processed, summary, created_at
            FROM ifa2.unified_runtime_runs
        """
        params: dict[str, Any] = {"limit": limit}
        if lane:
            sql += " WHERE lane = :lane"
            params["lane"] = lane
        sql += " ORDER BY started_at DESC LIMIT :limit"
        with self.engine.begin() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
            return [dict(row) for row in rows]

    def archive_catchup_status(self, limit: int = 20) -> dict[str, Any]:
        with self.engine.begin() as conn:
            summary_rows = conn.execute(
                text(
                    """
                    SELECT status, count(*) AS row_count
                    FROM ifa2.archive_target_catchup
                    GROUP BY status
                    ORDER BY status
                    """
                )
            ).mappings().all()
            recent_rows = conn.execute(
                text(
                    """
                    SELECT id, manifest_snapshot_id, change_type, dedupe_key,
                           symbol_or_series_id, asset_category, granularity,
                           source_list_name, suggested_backfill_start,
                           suggested_backfill_end, backlog_priority,
                           archive_run_id, checkpoint_dataset_name, checkpoint_asset_type,
                           started_at, completed_at, progress_note,
                           status, reason, created_at, updated_at
                    FROM ifa2.archive_target_catchup
                    ORDER BY updated_at DESC, created_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()
            checkpoint_rows = conn.execute(
                text(
                    """
                    SELECT dataset_name, asset_type, backfill_start, backfill_end,
                           last_completed_date, shard_id, batch_no, status, updated_at, created_at
                    FROM ifa2.archive_checkpoints
                    ORDER BY updated_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()
            run_rows = conn.execute(
                text(
                    """
                    SELECT run_id, job_name, dataset_name, asset_type, window_name,
                           started_at, completed_at, status, records_processed
                    FROM ifa2.archive_runs
                    ORDER BY started_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()
        return {
            "summary_by_status": [dict(row) for row in summary_rows],
            "recent_catchup_rows": [dict(row) for row in recent_rows],
            "recent_checkpoints": [dict(row) for row in checkpoint_rows],
            "recent_archive_runs": [dict(row) for row in run_rows],
        }

    def persist_manifest_snapshot(self, manifest: TargetManifest) -> str:
        snapshot_id = str(uuid.uuid4())
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.target_manifest_snapshots (
                        id, manifest_hash, generated_at, owner_type, owner_id,
                        selector_scope, item_count, payload
                    ) VALUES (
                        :id, :manifest_hash, :generated_at, :owner_type, :owner_id,
                        CAST(:selector_scope AS jsonb), :item_count, CAST(:payload AS jsonb)
                    )
                    ON CONFLICT (manifest_hash) DO NOTHING
                    """
                ),
                {
                    "id": snapshot_id,
                    "manifest_hash": manifest.manifest_hash,
                    "generated_at": datetime.fromisoformat(manifest.generated_at),
                    "owner_type": manifest.selector_scope["owner_type"],
                    "owner_id": manifest.selector_scope["owner_id"],
                    "selector_scope": json.dumps(manifest.selector_scope, ensure_ascii=False),
                    "item_count": manifest.item_count,
                    "payload": json.dumps(manifest.to_dict(), ensure_ascii=False),
                },
            )
            existing = conn.execute(
                text("select id from ifa2.target_manifest_snapshots where manifest_hash=:h"),
                {"h": manifest.manifest_hash},
            ).scalar_one()
            return str(existing)

    def load_latest_previous_manifest(
        self,
        *,
        owner_type: str,
        owner_id: str,
        exclude_snapshot_id: str,
    ) -> Optional[TargetManifest]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT payload
                    FROM ifa2.target_manifest_snapshots
                    WHERE owner_type = :owner_type
                      AND owner_id = :owner_id
                      AND id <> CAST(:exclude_snapshot_id AS uuid)
                    ORDER BY generated_at DESC
                    LIMIT 1
                    """
                ),
                {
                    "owner_type": owner_type,
                    "owner_id": owner_id,
                    "exclude_snapshot_id": exclude_snapshot_id,
                },
            ).scalar_one_or_none()
        if row is None:
            return None
        payload = row if isinstance(row, dict) else json.loads(row)
        items = [
            TargetManifestItem(
                **{
                    **item,
                    "theme_tags": tuple(item.get("theme_tags", [])),
                }
            )
            for item in payload["items"]
        ]
        return TargetManifest(
            manifest_id=payload["manifest_id"],
            manifest_hash=payload["manifest_hash"],
            generated_at=payload["generated_at"],
            selector_scope=payload["selector_scope"],
            items=items,
        )

    def persist_archive_deltas(self, manifest_snapshot_id: str, deltas: list[ArchiveDeltaItem]) -> int:
        inserted = 0
        with self.engine.begin() as conn:
            for d in deltas:
                exists = conn.execute(
                    text(
                        """
                        select id from ifa2.archive_target_catchup
                        where manifest_snapshot_id=:manifest_snapshot_id
                          and dedupe_key=:dedupe_key
                          and change_type=:change_type
                        limit 1
                        """
                    ),
                    {
                        "manifest_snapshot_id": manifest_snapshot_id,
                        "dedupe_key": d.dedupe_key,
                        "change_type": d.change_type,
                    },
                ).first()
                if exists:
                    continue
                checkpoint_dataset_name = self._checkpoint_dataset_name(d)
                checkpoint_asset_type = self._checkpoint_asset_type(d)
                initial_status = "planned" if d.change_type == "added" else "observed"
                progress_note = (
                    f"catch-up intent created for {checkpoint_dataset_name}/{checkpoint_asset_type}"
                    if d.change_type == "added"
                    else f"membership delta observed: {d.change_type}"
                )
                res = conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.archive_target_catchup (
                            id, manifest_snapshot_id, change_type, dedupe_key, symbol_or_series_id,
                            asset_category, granularity, source_list_name,
                            suggested_backfill_start, suggested_backfill_end,
                            backlog_priority, archive_run_id,
                            checkpoint_dataset_name, checkpoint_asset_type,
                            started_at, completed_at, progress_note,
                            status, reason, created_at, updated_at
                        ) VALUES (
                            :id, :manifest_snapshot_id, :change_type, :dedupe_key, :symbol_or_series_id,
                            :asset_category, :granularity, :source_list_name,
                            :suggested_backfill_start, :suggested_backfill_end,
                            :backlog_priority, NULL,
                            :checkpoint_dataset_name, :checkpoint_asset_type,
                            NULL, NULL, :progress_note,
                            :status, :reason, :created_at, :updated_at
                        )
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "manifest_snapshot_id": manifest_snapshot_id,
                        "change_type": d.change_type,
                        "dedupe_key": d.dedupe_key,
                        "symbol_or_series_id": d.symbol_or_series_id,
                        "asset_category": d.asset_category,
                        "granularity": d.granularity,
                        "source_list_name": d.source_list_name,
                        "suggested_backfill_start": d.suggested_backfill_start or None,
                        "suggested_backfill_end": d.suggested_backfill_end or None,
                        "backlog_priority": d.backlog_priority,
                        "checkpoint_dataset_name": checkpoint_dataset_name,
                        "checkpoint_asset_type": checkpoint_asset_type,
                        "progress_note": progress_note,
                        "status": initial_status,
                        "reason": d.reason,
                        "created_at": now_utc(),
                        "updated_at": now_utc(),
                    },
                )
                inserted += int(res.rowcount or 0)
        return inserted

    def begin_archive_catchup_execution(self, *, run_id: str, window_name: str, limit: int = 10) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, dedupe_key, symbol_or_series_id, asset_category, granularity,
                           source_list_name, suggested_backfill_start, suggested_backfill_end,
                           checkpoint_dataset_name, checkpoint_asset_type, backlog_priority
                    FROM ifa2.archive_target_catchup
                    WHERE status = 'planned'
                    ORDER BY
                        CASE backlog_priority
                            WHEN 'medium_high' THEN 1
                            WHEN 'medium' THEN 2
                            WHEN 'guarded_medium_low' THEN 3
                            WHEN 'none' THEN 4
                            ELSE 9
                        END,
                        created_at ASC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()
            started_at = now_utc()
            for row in rows:
                conn.execute(
                    text(
                        """
                        UPDATE ifa2.archive_target_catchup
                        SET archive_run_id = :run_id,
                            status = 'in_progress',
                            started_at = COALESCE(started_at, :started_at),
                            progress_note = :progress_note,
                            updated_at = :updated_at
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": row["id"],
                        "run_id": run_id,
                        "started_at": started_at,
                        "progress_note": f"bound to archive run {run_id} in window {window_name}",
                        "updated_at": started_at,
                    },
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO ifa2.archive_checkpoints (
                            id, dataset_name, asset_type, backfill_start, backfill_end,
                            last_completed_date, shard_id, batch_no, status, updated_at, created_at
                        ) VALUES (
                            :id, :dataset_name, :asset_type, :backfill_start, :backfill_end,
                            NULL, :shard_id, 0, 'planned', :now, :now
                        )
                        ON CONFLICT (dataset_name, asset_type) DO UPDATE SET
                            backfill_start = COALESCE(EXCLUDED.backfill_start, ifa2.archive_checkpoints.backfill_start),
                            backfill_end = COALESCE(EXCLUDED.backfill_end, ifa2.archive_checkpoints.backfill_end),
                            status = 'planned',
                            shard_id = COALESCE(EXCLUDED.shard_id, ifa2.archive_checkpoints.shard_id),
                            updated_at = EXCLUDED.updated_at
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "dataset_name": row["checkpoint_dataset_name"],
                        "asset_type": row["checkpoint_asset_type"],
                        "backfill_start": row["suggested_backfill_start"],
                        "backfill_end": row["suggested_backfill_end"],
                        "shard_id": row["dedupe_key"],
                        "now": started_at,
                    },
                )
                selected.append(dict(row))
        return selected

    def finalize_archive_catchup_execution(self, *, run_id: str, executed_rows: list[dict[str, Any]], completed: bool) -> None:
        if not executed_rows:
            return
        completed_at = now_utc()
        with self.engine.begin() as conn:
            for idx, row in enumerate(executed_rows, start=1):
                status = 'completed' if completed else 'partial'
                last_completed = row.get('suggested_backfill_end') if completed else row.get('suggested_backfill_start')
                conn.execute(
                    text(
                        """
                        UPDATE ifa2.archive_target_catchup
                        SET status = :status,
                            completed_at = :completed_at,
                            progress_note = :progress_note,
                            updated_at = :updated_at
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": row['id'],
                        "status": status,
                        "completed_at": completed_at,
                        "progress_note": (
                            f"catch-up execution closed by archive run {run_id}; checkpoint advanced"
                            if completed else
                            f"catch-up execution partially advanced by archive run {run_id}"
                        ),
                        "updated_at": completed_at,
                    },
                )
                conn.execute(
                    text(
                        """
                        UPDATE ifa2.archive_checkpoints
                        SET last_completed_date = COALESCE(:last_completed_date, last_completed_date),
                            batch_no = COALESCE(batch_no, 0) + :batch_increment,
                            status = :checkpoint_status,
                            updated_at = :updated_at
                        WHERE dataset_name = :dataset_name
                          AND asset_type = :asset_type
                        """
                    ),
                    {
                        "last_completed_date": last_completed,
                        "batch_increment": 1,
                        "checkpoint_status": 'completed' if completed else 'in_progress',
                        "updated_at": completed_at,
                        "dataset_name": row['checkpoint_dataset_name'],
                        "asset_type": row['checkpoint_asset_type'],
                    },
                )

    def _checkpoint_dataset_name(self, delta: ArchiveDeltaItem) -> str:
        granularity_prefix = delta.granularity.replace('min', 'm') if delta.granularity else 'archive'
        return f"{delta.asset_category}_{granularity_prefix}_catchup"

    def _checkpoint_asset_type(self, delta: ArchiveDeltaItem) -> str:
        return delta.asset_category


LOWFREQ_PROOFSET = [
    "trade_cal",
    "stock_basic",
    "index_basic",
    "announcements",
    "news",
    "company_basic",
]

MIDFREQ_PROOFSET = [
    "equity_daily_bar",
    "index_daily_bar",
    "etf_daily_bar",
    "margin_financing",
    "main_force_flow",
    "dragon_tiger_list",
]

MIDFREQ_TUSHARE_REQUIRED = set(MIDFREQ_PROOFSET) | {
    "northbound_flow",
    "limit_up_down_status",
    "limit_up_detail",
    "turnover_rate",
    "southbound_flow",
    "sector_performance",
}


class UnifiedRuntime:
    def __init__(self) -> None:
        self.store = UnifiedRuntimeStore()
        self.lowfreq_runner = LowFreqRunner()
        self.midfreq_runner = MidfreqRunner()
        self.lowfreq_registry = DatasetRegistry()
        self.midfreq_registry = MidfreqDatasetRegistry()
        self._ensure_runtime_registries()

    def run_once(
        self,
        lane: str,
        trigger_mode: str = "manual_once",
        scope: Optional[SelectorScope] = None,
        archive_window: str = "manual_archive",
        dry_run_manifest_only: bool = False,
    ) -> UnifiedRunResult:
        if lane not in {"lowfreq", "midfreq", "archive"}:
            raise ValueError(f"Unsupported lane: {lane}")

        scope = scope or SelectorScope()
        manifest = build_target_manifest(scope)
        manifest_snapshot_id = self.store.persist_manifest_snapshot(manifest)
        initial_worker_type = f"{lane}_manifest_preview_worker" if dry_run_manifest_only else f"{lane}_pending_worker"
        run_id = self.store.create_run(
            lane=lane,
            worker_type=initial_worker_type,
            trigger_mode=trigger_mode,
            manifest=manifest,
            manifest_snapshot_id=manifest_snapshot_id,
        )
        started_at = now_utc().isoformat()

        if dry_run_manifest_only:
            summary = {
                "run_id": run_id,
                "lane": lane,
                "trigger_mode": trigger_mode,
                "manifest_id": manifest.manifest_id,
                "manifest_hash": manifest.manifest_hash,
                "manifest_snapshot_id": manifest_snapshot_id,
                "manifest_item_count": manifest.item_count,
                "manifest_preview": manifest.to_dict()["items"][:10],
                "mode": "dry_run_manifest_only",
            }
            self.store.finalize_run(
                run_id=run_id,
                lane=lane,
                worker_type=f"{lane}_manifest_preview_worker",
                trigger_mode=trigger_mode,
                manifest_id=manifest.manifest_id,
                manifest_hash=manifest.manifest_hash,
                manifest_snapshot_id=manifest_snapshot_id,
                status="succeeded",
                records_processed=0,
                summary=summary,
            )
            completed_at = now_utc().isoformat()
            return UnifiedRunResult(
                run_id=run_id,
                lane=lane,
                worker_type=f"{lane}_manifest_preview_worker",
                trigger_mode=trigger_mode,
                manifest_id=manifest.manifest_id,
                manifest_hash=manifest.manifest_hash,
                status="succeeded",
                started_at=started_at,
                completed_at=completed_at,
                records_processed=0,
                summary=summary,
            )

        if lane in {"lowfreq", "midfreq"}:
            return self._run_runtime_lane(run_id, lane, trigger_mode, manifest, manifest_snapshot_id, started_at)
        return self._run_archive_lane(run_id, trigger_mode, manifest, manifest_snapshot_id, started_at, archive_window)

    def _run_runtime_lane(
        self,
        run_id: str,
        lane: str,
        trigger_mode: str,
        manifest: TargetManifest,
        manifest_snapshot_id: str,
        started_at: str,
    ) -> UnifiedRunResult:
        lane_items = [i for i in manifest.items if i.resolved_lane == lane]
        dataset_names = self._plan_lane_datasets(lane, lane_items)
        execution_mode = self._lane_execution_mode(lane)
        requirement_state = self._runtime_requirement_state(lane)
        blocked = self._blocked_dataset_results(lane, dataset_names, requirement_state)
        runnable_dataset_names = [
            dataset_name for dataset_name in dataset_names if dataset_name not in {r.dataset_name for r in blocked}
        ]
        dataset_results = blocked + [
            self._execute_lane_dataset(lane, dataset_name, dry_run=(execution_mode == "dry_run"))
            for dataset_name in runnable_dataset_names
        ]
        records_processed = sum(r.records_processed for r in dataset_results)
        failed = [r for r in dataset_results if r.status not in {"succeeded", "dry_run"}]
        succeeded = [r for r in dataset_results if r.status in {"succeeded", "dry_run"}]
        final_status = "failed" if failed and not succeeded else "partial" if failed else "succeeded"
        worker_type = f"{lane}_{execution_mode}_worker"
        summary = {
            "run_id": run_id,
            "lane": lane,
            "trigger_mode": trigger_mode,
            "execution_mode": execution_mode,
            "manifest_id": manifest.manifest_id,
            "manifest_hash": manifest.manifest_hash,
            "manifest_snapshot_id": manifest_snapshot_id,
            "manifest_item_count": len(lane_items),
            "planned_dataset_names": dataset_names,
            "executed_dataset_count": len(dataset_results),
            "asset_categories": sorted({i.asset_category for i in lane_items}),
            "dataset_results": [r.to_dict() for r in dataset_results],
            "manifest_preview_symbols": [i.symbol_or_series_id for i in lane_items[:10]],
            "requirements": requirement_state,
            "blocked_dataset_count": len(blocked),
            "blocked_dataset_names": [r.dataset_name for r in blocked],
        }
        self.store.finalize_run(
            run_id=run_id,
            lane=lane,
            worker_type=worker_type,
            trigger_mode=trigger_mode,
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            manifest_snapshot_id=manifest_snapshot_id,
            status=final_status,
            records_processed=records_processed,
            summary=summary,
        )
        completed_at = now_utc().isoformat()
        return UnifiedRunResult(
            run_id=run_id,
            lane=lane,
            worker_type=worker_type,
            trigger_mode=trigger_mode,
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            status=final_status,
            started_at=started_at,
            completed_at=completed_at,
            records_processed=records_processed,
            summary=summary,
        )

    def _plan_lane_datasets(self, lane: str, lane_items: list[TargetManifestItem]) -> list[str]:
        if lane == "lowfreq":
            enabled = [
                d.dataset_name
                for d in self.lowfreq_registry.list_enabled()
                if not d.dataset_name.startswith("test_")
                and d.dataset_name not in {"e2e_test_dataset", "china_a_share_daily"}
            ]
            preferred = [name for name in LOWFREQ_PROOFSET if name in enabled]
            if preferred:
                return preferred
            return enabled or ["stock_basic"]

        if lane == "midfreq":
            enabled = [d.dataset_name for d in self.midfreq_registry.list_enabled()]
            preferred = [name for name in MIDFREQ_PROOFSET if name in enabled]
            if preferred:
                return preferred
            return enabled or ["equity_daily_bar"]

        return []

    def _lane_execution_mode(self, lane: str) -> str:
        if lane == "lowfreq":
            return "real_run"
        if lane == "midfreq":
            return "real_run"
        return "dry_run"

    def _ensure_runtime_registries(self) -> None:
        """Bring runtime-critical registries to the expected minimum closure set."""
        self.midfreq_runner.register_datasets()

    def _runtime_requirement_state(self, lane: str) -> dict[str, Any]:
        settings = get_settings()
        token_configured = bool((settings.tushare_token or "").strip())
        return {
            "lane": lane,
            "tushare_token_configured": token_configured,
            "notes": [] if token_configured or lane != "midfreq" else [
                "TUSHARE_TOKEN missing: token-backed midfreq datasets are failed fast instead of looping the full universe"
            ],
        }

    def _blocked_dataset_results(
        self,
        lane: str,
        dataset_names: list[str],
        requirement_state: dict[str, Any],
    ) -> list[DatasetExecutionResult]:
        if lane != "midfreq" or requirement_state.get("tushare_token_configured"):
            return []
        blocked = []
        for dataset_name in dataset_names:
            if dataset_name not in MIDFREQ_TUSHARE_REQUIRED:
                continue
            blocked.append(
                DatasetExecutionResult(
                    dataset_name=dataset_name,
                    status="failed",
                    records_processed=0,
                    watermark=None,
                    error_message="missing requirement: TUSHARE_TOKEN is required for token-backed midfreq collection",
                )
            )
        return blocked

    def _execute_lane_dataset(self, lane: str, dataset_name: str, dry_run: bool) -> DatasetExecutionResult:
        if lane == "lowfreq":
            result = self.lowfreq_runner.run(dataset_name, dry_run=dry_run, run_type="unified_runtime")
            return DatasetExecutionResult(
                dataset_name=dataset_name,
                status=getattr(result, "status", "unknown"),
                records_processed=int(getattr(result, "records_processed", 0) or 0),
                watermark=getattr(result, "watermark", None),
                error_message=getattr(result, "error_message", None),
            )

        result = self.midfreq_runner.run(dataset_name, dry_run=dry_run)
        return DatasetExecutionResult(
            dataset_name=dataset_name,
            status=getattr(result, "status", "unknown"),
            records_processed=int(getattr(result, "records_processed", 0) or 0),
            watermark=getattr(result, "watermark", None),
            error_message=getattr(result, "error_message", None),
        )

    def _run_archive_lane(
        self,
        run_id: str,
        trigger_mode: str,
        manifest: TargetManifest,
        manifest_snapshot_id: str,
        started_at: str,
        archive_window: str,
    ) -> UnifiedRunResult:
        lane_items = [i for i in manifest.items if i.resolved_lane == "archive"]
        previous = self.store.load_latest_previous_manifest(
            owner_type=manifest.selector_scope["owner_type"],
            owner_id=manifest.selector_scope["owner_id"],
            exclude_snapshot_id=manifest_snapshot_id,
        )
        if previous is None:
            previous = TargetManifest(
                manifest_id=manifest.manifest_id + "_previous",
                manifest_hash=manifest.manifest_hash + "_previous",
                generated_at=manifest.generated_at,
                selector_scope=manifest.selector_scope,
                items=lane_items[:-1] if len(lane_items) > 1 else lane_items,
            )

        current = build_archive_manifest(
            SelectorScope(
                owner_type=manifest.selector_scope["owner_type"],
                owner_id=manifest.selector_scope["owner_id"],
                list_types=("archive_targets",),
            )
        )
        deltas = diff_archive_manifests(previous, current)
        persisted_catchup_rows = self.store.persist_archive_deltas(manifest_snapshot_id, deltas)

        orchestrator = ArchiveOrchestrator(get_archive_config())
        summary_obj = orchestrator.run_window(archive_window, dry_run=False)
        bound_catchups = self.store.begin_archive_catchup_execution(
            run_id=run_id,
            window_name=archive_window,
            limit=max(summary_obj.total_jobs, 1),
        )
        self.store.finalize_archive_catchup_execution(
            run_id=run_id,
            executed_rows=bound_catchups,
            completed=summary_obj.failed_jobs == 0,
        )
        records_processed = sum(r.records_processed for r in summary_obj.job_results)
        worker_type = "archive_real_run_worker"
        summary = {
            "run_id": run_id,
            "lane": "archive",
            "trigger_mode": trigger_mode,
            "manifest_id": manifest.manifest_id,
            "manifest_hash": manifest.manifest_hash,
            "manifest_snapshot_id": manifest_snapshot_id,
            "manifest_item_count": len(lane_items),
            "window_name": archive_window,
            "execution_mode": "real_run",
            "archive_total_jobs": summary_obj.total_jobs,
            "archive_succeeded_jobs": summary_obj.succeeded_jobs,
            "archive_failed_jobs": summary_obj.failed_jobs,
            "archive_delta_count": len(deltas),
            "archive_catchup_rows_inserted": persisted_catchup_rows,
            "archive_catchup_rows_bound": len(bound_catchups),
            "archive_catchup_rows_completed": len(bound_catchups) if summary_obj.failed_jobs == 0 else 0,
            "previous_manifest_hash": previous.manifest_hash,
            "current_archive_manifest_hash": current.manifest_hash,
            "delta_preview": [d.__dict__ for d in deltas[:10]],
            "bound_catchup_preview": [
                {
                    'id': str(row['id']),
                    'dedupe_key': row['dedupe_key'],
                    'checkpoint_dataset_name': row['checkpoint_dataset_name'],
                    'checkpoint_asset_type': row['checkpoint_asset_type'],
                }
                for row in bound_catchups[:10]
            ],
            "manifest_preview_symbols": [i.symbol_or_series_id for i in lane_items[:10]],
        }
        final_status = "succeeded" if summary_obj.failed_jobs == 0 else "partial"
        self.store.finalize_run(
            run_id=run_id,
            lane="archive",
            worker_type=worker_type,
            trigger_mode=trigger_mode,
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            manifest_snapshot_id=manifest_snapshot_id,
            status=final_status,
            records_processed=records_processed,
            summary=summary,
        )
        completed_at = now_utc().isoformat()
        return UnifiedRunResult(
            run_id=run_id,
            lane="archive",
            worker_type=worker_type,
            trigger_mode=trigger_mode,
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            status=final_status,
            started_at=started_at,
            completed_at=completed_at,
            records_processed=records_processed,
            summary=summary,
        )
