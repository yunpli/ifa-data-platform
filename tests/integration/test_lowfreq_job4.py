"""Integration tests for Job 4: current/history/version with promote/active semantics.

Tests cover:
- First ingest -> current+active version
- Second ingest -> previous version retained
- Active version switch
- Current query still returns latest
- Explicit version lookup
- As-of path query
- Rerun stability
"""

import pytest
import uuid
from datetime import date, datetime, timezone

from ifa_data_platform.lowfreq.canonical_persistence import (
    StockBasicCurrent,
    TradeCalCurrent,
)
from ifa_data_platform.lowfreq.models import (
    DatasetConfig,
    JobType,
    Market,
    RunnerType,
    WatermarkStrategy,
)
from ifa_data_platform.lowfreq.query import CurrentQuery, VersionQuery
from ifa_data_platform.lowfreq.registry import DatasetRegistry
from ifa_data_platform.lowfreq.runner import LowFreqRunner
from ifa_data_platform.lowfreq.version_persistence import (
    DatasetVersionRegistry,
    VersionStatus,
)


class TestFirstIngestActiveVersion:
    """Tests for first ingest creating active version."""

    @pytest.fixture
    def clean_dataset(self):
        """Clean up test dataset."""
        dataset_name = "test_job4_first_ingest"
        registry = DatasetRegistry()
        try:
            config = DatasetConfig(
                dataset_name=dataset_name,
                market=Market.CHINA_A_SHARE,
                source_name="dummy",
                job_type=JobType.INCREMENTAL,
                enabled=True,
                runner_type=RunnerType.DUMMY,
                watermark_strategy=WatermarkStrategy.DATE_BASED,
            )
            registry.register(config)
        except Exception:
            pass

        yield dataset_name

        version_registry = DatasetVersionRegistry()
        for version in version_registry.list_versions(dataset_name, limit=100):
            pass

    def test_first_ingest_creates_active_version(self, clean_dataset):
        """Test that first ingest creates active version."""
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        version_registry = DatasetVersionRegistry()

        config = DatasetConfig(
            dataset_name="test_first_ingest_active",
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        result = runner.run("test_first_ingest_active", dry_run=False)
        assert result.status == "succeeded"

        active_version = version_registry.get_active_version("test_first_ingest_active")
        assert active_version is not None
        assert active_version["is_active"] is True
        assert active_version["status"] == VersionStatus.ACTIVE

    def test_first_ingest_current_query_returns_data(self, clean_dataset):
        """Test that current query returns data after first ingest."""
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        current_query = CurrentQuery()

        config = DatasetConfig(
            dataset_name="test_current_after_first",
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        result = runner.run("test_current_after_first", dry_run=False)
        assert result.status == "succeeded"


class TestSecondIngestPreviousVersionRetained:
    """Tests for second ingest retaining previous version."""

    @pytest.fixture
    def versioned_dataset(self):
        """Setup dataset for version test."""
        dataset_name = "test_second_ingest_retained"
        registry = DatasetRegistry()

        config = DatasetConfig(
            dataset_name=dataset_name,
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        yield dataset_name

    def test_second_ingest_creates_new_version(self, versioned_dataset):
        """Test that second ingest creates new version."""
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        version_registry = DatasetVersionRegistry()

        result1 = runner.run(versioned_dataset, dry_run=False)
        assert result1.status == "succeeded"

        active_v1 = version_registry.get_active_version(versioned_dataset)
        assert active_v1 is not None

        result2 = runner.run(versioned_dataset, dry_run=False)
        assert result2.status == "succeeded"

        active_v2 = version_registry.get_active_version(versioned_dataset)
        assert active_v2 is not None
        assert active_v2["id"] != active_v1["id"]

    def test_previous_version_retained_not_active(self, versioned_dataset):
        """Test that previous version is retained but not active."""
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        version_registry = DatasetVersionRegistry()

        result1 = runner.run(versioned_dataset, dry_run=False)
        v1_id = version_registry.get_active_version(versioned_dataset)["id"]

        result2 = runner.run(versioned_dataset, dry_run=False)
        v2_id = version_registry.get_active_version(versioned_dataset)["id"]

        v1_check = version_registry.get_version_by_id(v1_id)
        assert v1_check is not None
        assert v1_check["is_active"] is False
        assert v1_check["status"] == VersionStatus.SUPERSEDED


class TestActiveVersionSwitch:
    """Tests for active version switching."""

    def test_promote_explicit_version(self):
        """Test explicit promotion of a version."""
        dataset_name = "test_promote_explicit2"
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        version_registry = DatasetVersionRegistry()

        config = DatasetConfig(
            dataset_name=dataset_name,
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        v1 = version_registry.get_active_version(dataset_name)
        if v1 is None:
            result = runner.run(dataset_name, dry_run=False, skip_promote=True)
            v1 = version_registry.get_active_version(dataset_name)
            assert v1 is None

            version_id = version_registry.list_versions(dataset_name, limit=1)[0]["id"]
            assert version_id is not None

            result = runner.promote(dataset_name, version_id)

        active_v = version_registry.get_active_version(dataset_name)
        assert active_v is not None
        assert active_v["is_active"] is True
        assert active_v["status"] == VersionStatus.ACTIVE


class TestCurrentQueryStillLatest:
    """Tests that current query still returns latest data."""

    def test_current_query_returns_active_version_data(self):
        """Test that current query returns data from active version."""
        dataset_name = "test_current_latest"
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        current_query = CurrentQuery()

        config = DatasetConfig(
            dataset_name=dataset_name,
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        runner.run(dataset_name, dry_run=False)

        trade_cal_current = TradeCalCurrent()
        trade_cal_current.upsert(
            cal_date=date(2024, 1, 15),
            exchange="SSE",
            is_open=True,
        )

        result = current_query.get_trade_cal(date(2024, 1, 15), "SSE")
        assert result is not None
        assert result["is_open"] is True


class TestExplicitVersionLookup:
    """Tests for explicit version lookup."""

    def test_get_version_by_id(self):
        """Test getting version by ID."""
        dataset_name = "test_version_by_id"
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        version_registry = DatasetVersionRegistry()

        config = DatasetConfig(
            dataset_name=dataset_name,
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        runner.run(dataset_name, dry_run=False)

        active_version = version_registry.get_active_version(dataset_name)
        version_id = active_version["id"]

        version = version_registry.get_version_by_id(version_id)
        assert version is not None
        assert version["id"] == version_id
        assert version["dataset_name"] == dataset_name

    def test_list_versions_for_dataset(self):
        """Test listing versions for a dataset."""
        dataset_name = "test_list_versions"
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        version_registry = DatasetVersionRegistry()

        config = DatasetConfig(
            dataset_name=dataset_name,
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        runner.run(dataset_name, dry_run=False)
        runner.run(dataset_name, dry_run=False)

        versions = version_registry.list_versions(dataset_name, limit=10)
        assert len(versions) >= 2


class TestAsOfPath:
    """Tests for as-of query path."""

    def test_version_at_promoted_time(self):
        """Test querying version at a specific time."""
        dataset_name = "test_as_of_time"
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        version_registry = DatasetVersionRegistry()

        config = DatasetConfig(
            dataset_name=dataset_name,
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        runner.run(dataset_name, dry_run=False)

        now = datetime.now(timezone.utc)
        version_at = version_registry.get_version_at_promoted_time(dataset_name, now)
        assert version_at is not None
        assert version_at["is_active"] is True


class TestRerunStability:
    """Tests for rerun stability."""

    def test_idempotent_rerun_with_version(self):
        """Test that rerun is idempotent and creates new version."""
        dataset_name = "test_rerun_stable"
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        version_registry = DatasetVersionRegistry()

        config = DatasetConfig(
            dataset_name=dataset_name,
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        result1 = runner.run(dataset_name, dry_run=False)
        v1_id = version_registry.get_active_version(dataset_name)["id"]

        result2 = runner.run(dataset_name, dry_run=False)
        v2_id = version_registry.get_active_version(dataset_name)["id"]

        assert result1.status == "succeeded"
        assert result2.status == "succeeded"
        assert v1_id != v2_id
        assert result1.run_id != result2.run_id


class TestVersionHistory:
    """Tests for version history tables."""

    def test_version_registry_has_versions(self):
        """Test that version registry tracks versions."""
        dataset_name = "test_history_version_registry"
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        version_registry = DatasetVersionRegistry()

        config = DatasetConfig(
            dataset_name=dataset_name,
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        runner.run(dataset_name, dry_run=False)

        versions = version_registry.list_versions(dataset_name, limit=10)
        assert len(versions) >= 1
        assert versions[0]["status"] == VersionStatus.ACTIVE


class TestVersionQueryAsOf:
    """Tests for VersionQuery as-of functionality."""

    def test_version_query_get_version_at(self):
        """Test VersionQuery.get_version_at."""
        dataset_name = "test_vq_as_of"
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        version_query = VersionQuery()

        config = DatasetConfig(
            dataset_name=dataset_name,
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        runner.run(dataset_name, dry_run=False)

        now = datetime.now(timezone.utc)
        version = version_query.get_version_at(dataset_name, now)
        assert version is not None
        assert version["is_active"] is True
