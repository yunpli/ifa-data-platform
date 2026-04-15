"""Minimal unified runtime substrate.

This first implementation batch provides:
- one-shot manifest-driven lane execution
- run-state/audit via job_runs
- a single entrypoint for lowfreq / midfreq / archive bounded rounds

This is intentionally small and explicit so that future milestones can extend it
without inventing another daemon family.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.lowfreq.runner import LowFreqRunner
from ifa_data_platform.midfreq.runner import MidfreqRunner
from ifa_data_platform.archive.archive_orchestrator import ArchiveOrchestrator
from ifa_data_platform.archive.archive_config import get_archive_config
from ifa_data_platform.runtime.target_manifest import SelectorScope, build_target_manifest


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


class UnifiedRuntimeStore:
    """Persist minimal unified runtime runs into ifa2.job_runs.

    Reuses the existing placeholder table for the first concrete implementation batch,
    while serializing execution details into error_message as a temporary summary field.
    """

    def __init__(self) -> None:
        self.engine = make_engine()

    def create_run(self, job_name: str) -> str:
        run_id = str(uuid.uuid4())
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
                    "job_name": job_name,
                    "started_at": now_utc(),
                    "created_at": now_utc(),
                },
            )
        return run_id

    def finalize_run(
        self,
        run_id: str,
        status: str,
        records_processed: int,
        summary: dict[str, Any],
    ) -> None:
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
                    "completed_at": now_utc(),
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


class UnifiedRuntime:
    def __init__(self) -> None:
        self.store = UnifiedRuntimeStore()
        self.lowfreq_runner = LowFreqRunner()
        self.midfreq_runner = MidfreqRunner()

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
        run_id = self.store.create_run(f"unified_runtime:{lane}")
        started_at = now_utc().isoformat()

        if dry_run_manifest_only:
            summary = {
                "run_id": run_id,
                "lane": lane,
                "trigger_mode": trigger_mode,
                "manifest_id": manifest.manifest_id,
                "manifest_hash": manifest.manifest_hash,
                "manifest_item_count": manifest.item_count,
                "manifest_preview": manifest.to_dict()["items"][:10],
                "mode": "dry_run_manifest_only",
            }
            self.store.finalize_run(run_id, "succeeded", 0, summary)
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
            return self._run_runtime_lane(run_id, lane, trigger_mode, manifest, started_at)
        return self._run_archive_lane(run_id, trigger_mode, manifest, started_at, archive_window)

    def _run_runtime_lane(
        self,
        run_id: str,
        lane: str,
        trigger_mode: str,
        manifest,
        started_at: str,
    ) -> UnifiedRunResult:
        lane_items = [i for i in manifest.items if i.resolved_lane == lane]
        dataset_map = {
            "lowfreq": "stock_basic",
            "midfreq": "equity_daily_bar",
        }
        worker_map = {
            "lowfreq": self.lowfreq_runner,
            "midfreq": self.midfreq_runner,
        }
        dataset_name = dataset_map[lane]
        runner = worker_map[lane]
        result = runner.run(dataset_name, dry_run=True, run_type="unified_runtime")
        summary = {
            "run_id": run_id,
            "lane": lane,
            "trigger_mode": trigger_mode,
            "manifest_id": manifest.manifest_id,
            "manifest_hash": manifest.manifest_hash,
            "manifest_item_count": len(lane_items),
            "dataset_name": dataset_name,
            "runner_status": result.status,
            "records_processed": result.records_processed,
            "manifest_preview_symbols": [i.symbol_or_series_id for i in lane_items[:10]],
        }
        final_status = "succeeded" if result.status == "succeeded" else result.status
        self.store.finalize_run(run_id, final_status, result.records_processed, summary)
        completed_at = now_utc().isoformat()
        return UnifiedRunResult(
            run_id=run_id,
            lane=lane,
            worker_type=f"{lane}_dryrun_worker",
            trigger_mode=trigger_mode,
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            status=final_status,
            started_at=started_at,
            completed_at=completed_at,
            records_processed=result.records_processed,
            summary=summary,
        )

    def _run_archive_lane(
        self,
        run_id: str,
        trigger_mode: str,
        manifest,
        started_at: str,
        archive_window: str,
    ) -> UnifiedRunResult:
        lane_items = [i for i in manifest.items if i.resolved_lane == 'archive']
        orchestrator = ArchiveOrchestrator(get_archive_config())
        summary_obj = orchestrator.run_window(archive_window, dry_run=True)
        records_processed = sum(r.records_processed for r in summary_obj.job_results)
        summary = {
            "run_id": run_id,
            "lane": "archive",
            "trigger_mode": trigger_mode,
            "manifest_id": manifest.manifest_id,
            "manifest_hash": manifest.manifest_hash,
            "manifest_item_count": len(lane_items),
            "window_name": archive_window,
            "archive_total_jobs": summary_obj.total_jobs,
            "archive_succeeded_jobs": summary_obj.succeeded_jobs,
            "archive_failed_jobs": summary_obj.failed_jobs,
            "manifest_preview_symbols": [i.symbol_or_series_id for i in lane_items[:10]],
        }
        final_status = "succeeded" if summary_obj.failed_jobs == 0 else "partial"
        self.store.finalize_run(run_id, final_status, records_processed, summary)
        completed_at = now_utc().isoformat()
        return UnifiedRunResult(
            run_id=run_id,
            lane="archive",
            worker_type="archive_dryrun_worker",
            trigger_mode=trigger_mode,
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            status=final_status,
            started_at=started_at,
            completed_at=completed_at,
            records_processed=records_processed,
            summary=summary,
        )
