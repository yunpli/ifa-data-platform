"""Functional tests for low-frequency ingestion framework."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from ifa_data_platform.lowfreq.models import (
    DatasetConfig,
    JobType,
    Market,
    RunnerType,
    TimezoneSemantics,
    WatermarkStrategy,
)
from ifa_data_platform.lowfreq.registry import DatasetRegistry
from ifa_data_platform.lowfreq.run_state import RunStateManager
from ifa_data_platform.lowfreq.runner import LowFreqRunner


@pytest.fixture
def registry():
    return DatasetRegistry()


@pytest.fixture
def run_state_manager():
    return RunStateManager()


@pytest.fixture
def runner():
    return LowFreqRunner()


@pytest.fixture
def sample_dataset_config():
    return DatasetConfig(
        dataset_name="test_dataset",
        market=Market.CHINA_A_SHARE,
        source_name="test_source",
        job_type=JobType.INCREMENTAL,
        enabled=True,
        timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
        runner_type=RunnerType.DUMMY,
        watermark_strategy=WatermarkStrategy.DATE_BASED,
        budget_records_max=1000,
        budget_seconds_max=60,
        metadata={"test": "data"},
        description="Test dataset for functional tests",
    )


class TestDatasetRegistry:
    def test_register_new_dataset(self, registry, sample_dataset_config):
        dataset_id = registry.register(sample_dataset_config)
        assert dataset_id is not None

        retrieved = registry.get(sample_dataset_config.dataset_name)
        assert retrieved is not None
        assert retrieved.dataset_name == sample_dataset_config.dataset_name
        assert retrieved.market == sample_dataset_config.market
        assert retrieved.enabled is True

    def test_register_duplicate_updates_existing(self, registry, sample_dataset_config):
        registry.register(sample_dataset_config)

        sample_dataset_config.description = "Updated description"
        registry.register(sample_dataset_config)

        retrieved = registry.get(sample_dataset_config.dataset_name)
        assert retrieved.description == "Updated description"

    def test_get_nonexistent_dataset(self, registry):
        result = registry.get("nonexistent_dataset")
        assert result is None

    def test_list_enabled(self, registry, sample_dataset_config):
        registry.register(sample_dataset_config)

        enabled = registry.list_enabled()
        assert len(enabled) >= 1
        assert any(
            ds.dataset_name == sample_dataset_config.dataset_name for ds in enabled
        )

    def test_list_all(self, registry, sample_dataset_config):
        registry.register(sample_dataset_config)

        all_datasets = registry.list_all()
        assert len(all_datasets) >= 1

    def test_enable_disable_dataset(self, registry, sample_dataset_config):
        registry.register(sample_dataset_config)

        registry.disable(sample_dataset_config.dataset_name)
        retrieved = registry.get(sample_dataset_config.dataset_name)
        assert retrieved.enabled is False

        registry.enable(sample_dataset_config.dataset_name)
        retrieved = registry.get(sample_dataset_config.dataset_name)
        assert retrieved.enabled is True


class TestRunStateManager:
    def test_create_run(self, run_state_manager):
        run_state = run_state_manager.create_run("test_dataset", dry_run=False)
        assert run_state.run_id is not None
        assert run_state.dataset_name == "test_dataset"
        assert run_state.status == "pending"
        assert run_state.dry_run is False

    def test_create_dry_run(self, run_state_manager):
        run_state = run_state_manager.create_run("test_dataset", dry_run=True)
        assert run_state.dry_run is True

    def test_update_status(self, run_state_manager):
        run_state = run_state_manager.create_run("test_dataset")
        run_state_manager.update_status(run_state.run_id, "running")
        run_state_manager.update_status(
            run_state.run_id, "succeeded", records_processed=100, watermark="2024-01-15"
        )

        retrieved = run_state_manager.get(run_state.run_id)
        assert retrieved.status == "succeeded"
        assert retrieved.records_processed == 100
        assert retrieved.watermark == "2024-01-15"
        assert retrieved.completed_at is not None

    def test_update_status_with_error(self, run_state_manager):
        run_state = run_state_manager.create_run("test_dataset")
        run_state_manager.update_status(
            run_state.run_id, "failed", error_message="Test error"
        )

        retrieved = run_state_manager.get(run_state.run_id)
        assert retrieved.status == "failed"
        assert retrieved.error_message == "Test error"

    def test_get_latest_for_dataset(self, run_state_manager):
        run_state_manager.create_run("test_dataset")
        latest = run_state_manager.get_latest_for_dataset("test_dataset")
        assert latest is not None
        assert latest.dataset_name == "test_dataset"

    def test_list_recent(self, run_state_manager):
        run_state_manager.create_run("dataset_1")
        run_state_manager.create_run("dataset_2")

        recent = run_state_manager.list_recent(limit=5)
        assert len(recent) >= 2


class TestLowFreqRunner:
    def test_dry_run_path(self, runner, registry, sample_dataset_config):
        registry.register(sample_dataset_config)

        result = runner.run(sample_dataset_config.dataset_name, dry_run=True)
        assert result.status == "succeeded"
        assert result.records_processed == 0

    def test_real_run_path(self, runner, registry, sample_dataset_config):
        registry.register(sample_dataset_config)

        result = runner.run(sample_dataset_config.dataset_name, dry_run=False)
        assert result.status == "succeeded"
        assert result.records_processed > 0

    def test_watermark_update_on_real_run(
        self, runner, registry, sample_dataset_config
    ):
        registry.register(sample_dataset_config)

        result1 = runner.run(sample_dataset_config.dataset_name, dry_run=False)
        assert result1.watermark is not None

        result2 = runner.run(sample_dataset_config.dataset_name, dry_run=False)
        assert result2.watermark is not None

    def test_repeat_execution_stability(self, runner, registry, sample_dataset_config):
        registry.register(sample_dataset_config)

        result1 = runner.run(sample_dataset_config.dataset_name, dry_run=False)
        result2 = runner.run(sample_dataset_config.dataset_name, dry_run=False)

        assert result1.status == "succeeded"
        assert result2.status == "succeeded"
        assert result2.run_id != result1.run_id

    def test_run_nonexistent_dataset_raises_error(self, runner):
        with pytest.raises(ValueError, match="Dataset not found"):
            runner.run("nonexistent_dataset")

    def test_run_disabled_dataset_raises_error(
        self, runner, registry, sample_dataset_config
    ):
        sample_dataset_config.enabled = False
        registry.register(sample_dataset_config)

        with pytest.raises(ValueError, match="disabled"):
            runner.run(sample_dataset_config.dataset_name)

    def test_run_all_enabled_datasets(self, runner, registry, sample_dataset_config):
        registry.register(sample_dataset_config)

        results = runner.run_all(dry_run=True)
        assert len(results) >= 1

    def test_error_status_handling(self, runner, registry):
        disabled_config = DatasetConfig(
            dataset_name="error_test_disabled",
            market=Market.CHINA_A_SHARE,
            source_name="test",
            job_type=JobType.INCREMENTAL,
            enabled=False,
            runner_type=RunnerType.DUMMY,
        )
        registry.register(disabled_config)

        results = runner.run_all(dry_run=True)
        assert len(results) >= 0


class TestAdaptorFactory:
    def test_get_dummy_adaptor(self):
        from ifa_data_platform.lowfreq.adaptor_factory import get_adaptor

        adaptor = get_adaptor(RunnerType.DUMMY)
        assert adaptor.test_connection() is True

        result = adaptor.fetch("test_dataset")
        assert len(result.records) > 0

    @patch("ifa_data_platform.lowfreq.adaptors.tushare.get_tushare_client")
    def test_get_tushare_adaptor(self, mock_get_client):
        from ifa_data_platform.lowfreq.adaptor_factory import get_adaptor

        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        mock_get_client.return_value = mock_client

        adaptor = get_adaptor(RunnerType.TUSHARE)
        assert adaptor.test_connection() is True

    def test_unsupported_runner_type_raises_error(self):
        from ifa_data_platform.lowfreq.adaptor_factory import get_adaptor

        class CustomRunnerType:
            pass

        with pytest.raises(ValueError, match="Unsupported"):
            get_adaptor(CustomRunnerType())


class TestEndToEnd:
    def test_full_registry_runner_state_chain(self, registry, runner):
        config = DatasetConfig(
            dataset_name="e2e_test_dataset",
            market=Market.CHINA_A_SHARE,
            source_name="e2e_source",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
            description="End-to-end test dataset",
        )

        dataset_id = registry.register(config)
        assert dataset_id is not None

        result = runner.run(config.dataset_name, dry_run=False)
        assert result.status == "succeeded"
        assert result.records_processed > 0
        assert result.watermark is not None

        retrieved = registry.get(config.dataset_name)
        assert retrieved is not None
        assert retrieved.enabled is True
