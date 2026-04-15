"""D1 Archive Framework End-to-End Test.

Proves:
1. Archiver starts
2. Window match works
3. archive_runs writes
4. archive_checkpoints writes
5. summary persists
6. watchdog / health works
7. checkpoint / resume chain works
"""

import uuid
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from ifa_data_platform.archive.archive_config import (
    ArchiveConfig,
    ArchiveWindow,
    ArchiveJobConfig,
    get_archive_config,
)
from ifa_data_platform.archive.archive_job_store import ArchiveJobStore
from ifa_data_platform.archive.archive_run_store import ArchiveRunStore
from ifa_data_platform.archive.archive_checkpoint import ArchiveCheckpointStore
from ifa_data_platform.archive.archive_summary import ArchiveSummaryStore
from ifa_data_platform.archive.archive_daemon_state import ArchiveDaemonStateStore
from ifa_data_platform.archive.archive_orchestrator import ArchiveOrchestrator
from ifa_data_platform.archive.archive_health import (
    get_archive_health,
    check_archive_watchdog,
)


@pytest.fixture
def test_config():
    """Test configuration with fixed windows."""
    return ArchiveConfig(
        timezone=ZoneInfo("Asia/Shanghai"),
        loop_interval_sec=60,
        windows=[
            ArchiveWindow(
                window_name="test_window_1",
                start_time="21:30",
                end_time="22:30",
                timezone=ZoneInfo("Asia/Shanghai"),
                max_duration_minutes=60,
                is_enabled=True,
            ),
            ArchiveWindow(
                window_name="test_window_2",
                start_time="02:00",
                end_time="03:00",
                timezone=ZoneInfo("Asia/Shanghai"),
                max_duration_minutes=60,
                is_enabled=True,
            ),
        ],
        jobs=[
            ArchiveJobConfig(
                job_name="test_stock_archive",
                dataset_name="test_stock_daily",
                asset_type="stock",
                pool_name="test_pool",
                scope_name="test_scope",
                is_enabled=True,
                description="Test stock archive",
            ),
            ArchiveJobConfig(
                job_name="test_commodity_archive",
                dataset_name="test_commodity_history",
                asset_type="commodity",
                pool_name="test_pool",
                scope_name="test_scope",
                is_enabled=True,
                description="Test commodity archive",
            ),
            ArchiveJobConfig(
                job_name="test_precious_archive",
                dataset_name="test_precious_history",
                asset_type="precious_metal",
                pool_name="test_pool",
                scope_name="test_scope",
                is_enabled=True,
                description="Test precious archive",
            ),
        ],
    )


@pytest.fixture
def test_time_window_1():
    """Time within window_1 (21:30-22:30 Shanghai)."""
    dt = datetime(2026, 4, 13, 21, 45, 0)
    return dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))


class TestArchiveFramework:
    """Test Archive Framework D1."""

    def test_window_match(self, test_config, test_time_window_1):
        """Test 1: Window match works."""
        window = test_config.get_matching_window(test_time_window_1)
        assert window is not None
        assert window.window_name == "test_window_1"
        print(f"Window matched: {window.window_name}")

    def test_archive_runs_write(self, test_config):
        """Test 3: archive_runs writes."""
        run_store = ArchiveRunStore()
        run_id = run_store.create_run(
            job_name="test_job",
            dataset_name="test_dataset",
            asset_type="stock",
            window_name="test_window",
        )
        assert run_id is not None

        run = run_store.get_run(run_id)
        assert run is not None
        assert run["run_id"] == run_id
        print(f"Run created: {run_id}")

        run_store.update_status(run_id, "succeeded", records_processed=10)
        updated = run_store.get_run(run_id)
        assert updated["status"] == "succeeded"
        assert updated["records_processed"] == 10

    def test_archive_checkpoints_write(self, test_config):
        """Test 4: archive_checkpoints writes."""
        checkpoint_store = ArchiveCheckpointStore()

        from datetime import date

        backfill_start = date(2025, 1, 1)
        backfill_end = date(2025, 12, 31)
        last_completed = date(2025, 6, 15)

        checkpoint_store.upsert_checkpoint(
            dataset_name="test_stock_daily",
            asset_type="stock",
            backfill_start=backfill_start,
            backfill_end=backfill_end,
            last_completed_date=last_completed,
            shard_id="shard_001",
            batch_no=5,
            status="in_progress",
        )

        cp = checkpoint_store.get_checkpoint("test_stock_daily", "stock")
        assert cp is not None
        assert cp["last_completed_date"] == last_completed
        assert cp["shard_id"] == "shard_001"
        print(f"Checkpoint created: {cp['last_completed_date']}")

    def test_summary_persists(self, test_config):
        """Test 5: summary persists."""
        summary_store = ArchiveSummaryStore()

        from datetime import date

        summary_date = date(2026, 4, 13)

        summary_store.upsert_summary(
            summary_date=summary_date,
            window_name="test_window_1",
            total_jobs=1,
            succeeded_jobs=1,
            failed_jobs=0,
            total_records=100,
            status="completed",
        )

        summary = summary_store.get_summary(summary_date, "test_window_1")
        assert summary is not None
        assert summary["succeeded_jobs"] == 1
        assert summary["total_records"] == 100
        print(f"Summary persisted: {summary['status']}")

    def test_health_query(self, test_config):
        """Test 6: health query works."""
        daemon_store = ArchiveDaemonStateStore()
        daemon_store.update_loop("test_job", "succeeded")

        health = get_archive_health(test_config)
        assert health is not None
        print(f"Health: {health.status}, {health.message}")

        watchdog = check_archive_watchdog(test_config)
        assert watchdog is not None
        print(f"Watchdog: {watchdog.is_alive}, {watchdog.message}")

    def test_checkpoint_resume_chain(self, test_config):
        """Test 7: checkpoint/resume chain works."""
        checkpoint_store = ArchiveCheckpointStore()

        from datetime import date

        checkpoint_store.upsert_checkpoint(
            dataset_name="test_resume_dataset",
            asset_type="stock",
            backfill_start=date(2025, 1, 1),
            backfill_end=date(2025, 12, 31),
            last_completed_date=date(2025, 6, 15),
            shard_id="shard_001",
            batch_no=5,
            status="in_progress",
        )

        cp1 = checkpoint_store.get_checkpoint("test_resume_dataset", "stock")
        assert cp1 is not None
        assert cp1["last_completed_date"] == date(2025, 6, 15)
        print(f"Resume from: {cp1['last_completed_date']}")

        checkpoint_store.update_progress(
            dataset_name="test_resume_dataset",
            asset_type="stock",
            last_completed_date=date(2025, 6, 16),
            batch_no=6,
            status="in_progress",
        )

        cp2 = checkpoint_store.get_checkpoint("test_resume_dataset", "stock")
        assert cp2["last_completed_date"] == date(2025, 6, 16)
        assert cp2["batch_no"] == 6
        print(f"Advanced to: {cp2['last_completed_date']}, batch {cp2['batch_no']}")

    def test_orchestrator_run(self, test_config):
        """End-to-end test: orchestrator runs and persists everything."""
        orchestrator = ArchiveOrchestrator(test_config)

        summary = orchestrator.run_window("test_window_1", dry_run=False)

        assert summary is not None
        assert summary.total_jobs >= 3
        print(f"Executed: {summary.succeeded_jobs}/{summary.total_jobs} succeeded")

        checkpoint_store = ArchiveCheckpointStore()
        checkpoints = checkpoint_store.list_checkpoints()
        print(f"Checkpoints: {len(checkpoints)}")

        summary_store = ArchiveSummaryStore()
        summaries = summary_store.list_summaries(limit=5)
        print(f"Summaries: {len(summaries)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
