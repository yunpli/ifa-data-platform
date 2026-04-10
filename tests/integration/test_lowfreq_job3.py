"""Integration tests for Job 3: real Tushare low-frequency ingestion chain."""

import pytest
import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from ifa_data_platform.lowfreq.adaptor import BaseAdaptor, FetchResult
from ifa_data_platform.lowfreq.adaptor_factory import get_adaptor
from ifa_data_platform.lowfreq.canonical_persistence import (
    StockBasicCurrent,
    TradeCalCurrent,
)
from ifa_data_platform.lowfreq.models import (
    DatasetConfig,
    JobType,
    Market,
    RunnerType,
    TimezoneSemantics,
    WatermarkStrategy,
)
from ifa_data_platform.lowfreq.raw_persistence import RawFetchPersistence
from ifa_data_platform.lowfreq.registry import DatasetRegistry
from ifa_data_platform.lowfreq.run_state import RunStateManager
from ifa_data_platform.lowfreq.runner import LowFreqRunner


class TestRunnerTrigger:
    """Tests for runner trigger functionality."""

    def test_runner_runs_registered_dataset(self):
        """Test that runner can execute a registered dataset."""
        registry = DatasetRegistry()
        runner = LowFreqRunner()

        config = DatasetConfig(
            dataset_name="test_trigger_runner",
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        result = runner.run(config.dataset_name, dry_run=False)
        assert result.status == "succeeded"
        assert result.records_processed > 0

    def test_runner_respects_disabled_datasets(self):
        """Test that runner raises error for disabled datasets."""
        registry = DatasetRegistry()
        runner = LowFreqRunner()

        config = DatasetConfig(
            dataset_name="test_disabled_runner",
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=False,
            runner_type=RunnerType.DUMMY,
        )
        registry.register(config)

        with pytest.raises(ValueError, match="disabled"):
            runner.run(config.dataset_name)


class TestAdaptorPath:
    """Tests for adaptor path."""

    def test_dummy_adaptor_produces_records(self):
        """Test that DummyAdaptor produces records."""
        adaptor = get_adaptor(RunnerType.DUMMY)
        result = adaptor.fetch("test_dataset")
        assert len(result.records) > 0
        assert result.watermark is not None
        assert result.fetched_at != ""

    def test_adaptor_factory_returns_correct_type(self):
        """Test adaptor factory returns correct adaptor type."""
        dummy = get_adaptor(RunnerType.DUMMY)
        assert isinstance(dummy, BaseAdaptor)

    def test_runner_uses_adaptor_from_factory(self):
        """Test that runner uses adaptor from factory."""
        registry = DatasetRegistry()
        runner = LowFreqRunner()

        config = DatasetConfig(
            dataset_name="test_adaptor_path",
            market=Market.CHINA_A_SHARE,
            source_name="test",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
        )
        registry.register(config)

        result = runner.run(config.dataset_name, dry_run=False)
        assert result.status == "succeeded"
        assert result.records_processed > 0


class TestRawPersistence:
    """Tests for raw/source mirror persistence."""

    @pytest.fixture
    def raw_persistence(self):
        return RawFetchPersistence()

    def test_store_and_retrieve_raw_fetch(self, raw_persistence):
        """Test storing and retrieving raw fetch records."""
        run_id = str(uuid.uuid4())
        records = [{"cal_date": "2024-01-15", "is_open": 1}]

        fetch_id = raw_persistence.store(
            run_id=run_id,
            source_name="tushare",
            dataset_name="trade_cal",
            request_params={"exchange": "SSE"},
            raw_payload=records,
            watermark="2024-01-15",
            status="success",
        )

        assert fetch_id is not None

        retrieved = raw_persistence.get_by_run_id(run_id)
        assert retrieved is not None
        assert retrieved["dataset_name"] == "trade_cal"
        assert retrieved["source_name"] == "tushare"
        assert retrieved["record_count"] == 1
        assert retrieved["status"] == "success"

    def test_get_latest_for_dataset(self, raw_persistence):
        """Test retrieving latest raw fetch for a dataset."""
        run_id_1 = str(uuid.uuid4())
        run_id_2 = str(uuid.uuid4())

        raw_persistence.store(
            run_id=run_id_1,
            source_name="tushare",
            dataset_name="test_raw_dataset",
            request_params={},
            raw_payload=[{"id": 1}],
            watermark="2024-01-14",
            status="success",
        )

        raw_persistence.store(
            run_id=run_id_2,
            source_name="tushare",
            dataset_name="test_raw_dataset",
            request_params={},
            raw_payload=[{"id": 2}],
            watermark="2024-01-15",
            status="success",
        )

        latest = raw_persistence.get_latest_for_dataset("test_raw_dataset", limit=2)
        assert len(latest) == 2
        assert latest[0]["watermark"] == "2024-01-15"

    def test_store_failure_record(self, raw_persistence):
        """Test storing a failed fetch record."""
        run_id = str(uuid.uuid4())

        fetch_id = raw_persistence.store(
            run_id=run_id,
            source_name="tushare",
            dataset_name="trade_cal",
            request_params={},
            raw_payload=[],
            watermark=None,
            status="failed",
            error_message="API Error: connection timeout",
        )

        retrieved = raw_persistence.get_by_run_id(run_id)
        assert retrieved["status"] == "failed"
        assert "timeout" in retrieved["error_message"]


class TestCanonicalPersistence:
    """Tests for canonical current persistence."""

    @pytest.fixture
    def trade_cal_current(self):
        return TradeCalCurrent()

    @pytest.fixture
    def stock_basic_current(self):
        return StockBasicCurrent()

    def test_trade_cal_upsert_and_get(self, trade_cal_current):
        """Test upserting and retrieving trade calendar records."""
        record_id = trade_cal_current.upsert(
            cal_date=date(2024, 1, 15),
            exchange="SSE",
            is_open=True,
        )

        assert record_id is not None

        retrieved = trade_cal_current.get_by_date(date(2024, 1, 15), "SSE")
        assert retrieved is not None
        assert retrieved["cal_date"] == date(2024, 1, 15)
        assert retrieved["exchange"] == "SSE"
        assert retrieved["is_open"] is True

    def test_trade_cal_upsert_idempotent(self, trade_cal_current):
        """Test that upserting the same record is idempotent."""
        record_id_1 = trade_cal_current.upsert(
            cal_date=date(2024, 1, 15),
            exchange="SSE",
            is_open=True,
        )

        record_id_2 = trade_cal_current.upsert(
            cal_date=date(2024, 1, 15),
            exchange="SSE",
            is_open=True,
        )

        retrieved = trade_cal_current.get_by_date(date(2024, 1, 15), "SSE")
        assert retrieved is not None

    def test_trade_cal_bulk_upsert(self, trade_cal_current):
        """Test bulk upserting trade calendar records."""
        records = [
            {
                "cal_date": date(2024, 1, 10),
                "exchange": "SSE",
                "is_open": True,
                "pretrade_date": None,
            },
            {
                "cal_date": date(2024, 1, 11),
                "exchange": "SSE",
                "is_open": True,
                "pretrade_date": date(2024, 1, 10),
            },
            {
                "cal_date": date(2024, 1, 12),
                "exchange": "SSE",
                "is_open": True,
                "pretrade_date": date(2024, 1, 11),
            },
            {
                "cal_date": date(2024, 1, 13),
                "exchange": "SSE",
                "is_open": False,
                "pretrade_date": date(2024, 1, 12),
            },
        ]

        count = trade_cal_current.bulk_upsert(records)
        assert count == 4

        retrieved = trade_cal_current.list_range(
            date(2024, 1, 10), date(2024, 1, 13), "SSE"
        )
        assert len(retrieved) == 4

    def test_stock_basic_upsert_and_get(self, stock_basic_current):
        """Test upserting and retrieving stock basic records."""
        record_id = stock_basic_current.upsert(
            ts_code="000001.SZ",
            symbol="000001",
            name="平安银行",
            market="主板",
            list_status="L",
            list_date=date(1991, 4, 3),
        )

        assert record_id is not None

        retrieved = stock_basic_current.get_by_ts_code("000001.SZ")
        assert retrieved is not None
        assert retrieved["ts_code"] == "000001.SZ"
        assert retrieved["symbol"] == "000001"
        assert retrieved["name"] == "平安银行"

    def test_stock_basic_upsert_idempotent(self, stock_basic_current):
        """Test that upserting the same record is idempotent."""
        stock_basic_current.upsert(
            ts_code="600000.SZ",
            symbol="600000",
            name="浦发银行",
            market="主板",
            list_status="L",
        )

        stock_basic_current.upsert(
            ts_code="600000.SZ",
            symbol="600000",
            name="浦发银行",
            market="主板",
            list_status="L",
        )

        retrieved = stock_basic_current.get_by_ts_code("600000.SZ")
        assert retrieved is not None
        assert retrieved["ts_code"] == "600000.SZ"


class TestWatermarkUpdate:
    """Tests for watermark advancement."""

    def test_watermark_advances_on_repeat_runs(self):
        """Test that watermark advances on repeat runs."""
        registry = DatasetRegistry()
        runner = LowFreqRunner()

        config = DatasetConfig(
            dataset_name="test_watermark_advance",
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        result1 = runner.run(config.dataset_name, dry_run=False)
        assert result1.watermark is not None
        watermark1 = result1.watermark

        result2 = runner.run(config.dataset_name, dry_run=False)
        assert result2.watermark is not None
        watermark2 = result2.watermark

        assert watermark2 >= watermark1

    def test_watermark_persists_in_run_state(self):
        """Test that watermark persists in run state."""
        run_state_manager = RunStateManager()
        run_state = run_state_manager.create_run("test_watermark_persist")

        run_state_manager.update_status(
            run_state.run_id,
            "succeeded",
            records_processed=100,
            watermark="2024-01-15",
        )

        retrieved = run_state_manager.get(run_state.run_id)
        assert retrieved.watermark == "2024-01-15"
        assert retrieved.records_processed == 100


class TestIdempotentRerun:
    """Tests for idempotent re-run behavior."""

    def test_repeat_execution_does_not_duplicate_records(self):
        """Test that repeat execution does not dirty current tables."""
        registry = DatasetRegistry()
        runner = LowFreqRunner()
        trade_cal = TradeCalCurrent()

        config = DatasetConfig(
            dataset_name="test_idempotent_rerun",
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        result1 = runner.run(config.dataset_name, dry_run=False)
        assert result1.status == "succeeded"

        result2 = runner.run(config.dataset_name, dry_run=False)
        assert result2.status == "succeeded"
        assert result2.run_id != result1.run_id


class TestErrorStatusBehavior:
    """Tests for error status behavior."""

    def test_runner_records_error_on_failure(self):
        """Test that runner records error message on failure."""
        registry = DatasetRegistry()
        run_state_manager = RunStateManager()

        config = DatasetConfig(
            dataset_name="test_error_status",
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
        )
        registry.register(config)

        run_state = run_state_manager.create_run(config.dataset_name)
        run_state_manager.update_status(
            run_state.run_id,
            "failed",
            error_message="Test error message",
        )

        latest = run_state_manager.get_latest_for_dataset(config.dataset_name)
        assert latest.status == "failed"
        assert "Test error" in latest.error_message


class TestEndToEndIntegration:
    """End-to-end integration tests with controlled adaptor."""

    def test_full_chain_registry_and_runner(self):
        """Test full chain: registry -> runner."""
        registry = DatasetRegistry()
        runner = LowFreqRunner()

        config = DatasetConfig(
            dataset_name="test_e2e_dummy",
            market=Market.CHINA_A_SHARE,
            source_name="dummy",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
        )
        registry.register(config)

        result = runner.run(config.dataset_name, dry_run=False)
        assert result.status == "succeeded"
        assert result.records_processed > 0


class TestTushareAdaptorWithMock:
    """Tests for Tushare adaptor with mocked client."""

    @patch("ifa_data_platform.lowfreq.adaptors.tushare.get_tushare_client")
    def test_tushare_adaptor_fetches_trade_cal(self, mock_get_client):
        """Test Tushare adaptor fetches trade_cal data."""
        mock_client = MagicMock()
        mock_client.query.return_value = [
            {"cal_date": "20240115", "exchange": "SSE", "is_open": "1"},
            {"cal_date": "20240116", "exchange": "SSE", "is_open": "1"},
        ]
        mock_client.test_connection.return_value = True
        mock_get_client.return_value = mock_client

        from ifa_data_platform.lowfreq.adaptors.tushare import TushareAdaptor

        adaptor = TushareAdaptor()
        result = adaptor.fetch("trade_cal", run_id=str(uuid.uuid4()))

        assert len(result.records) == 2
        assert result.watermark is not None

    @patch("ifa_data_platform.lowfreq.adaptors.tushare.get_tushare_client")
    def test_tushare_adaptor_fetches_stock_basic(self, mock_get_client):
        """Test Tushare adaptor fetches stock_basic data."""
        mock_client = MagicMock()
        mock_client.query.return_value = [
            {
                "ts_code": "000001.SZ",
                "symbol": "000001",
                "name": "平安银行",
                "area": "深圳",
                "industry": "银行",
                "market": "主板",
                "list_status": "L",
                "list_date": "19910403",
                "is_hs": "1",
            },
        ]
        mock_client.test_connection.return_value = True
        mock_get_client.return_value = mock_client

        from ifa_data_platform.lowfreq.adaptors.tushare import TushareAdaptor

        adaptor = TushareAdaptor()
        result = adaptor.fetch("stock_basic", run_id=str(uuid.uuid4()))

        assert len(result.records) == 1
        assert result.records[0]["ts_code"] == "000001.SZ"
        assert result.watermark == "full_snapshot"


class TestDatasetRegistry:
    """Tests for dataset registry."""

    def test_list_enabled_includes_registered_datasets(self):
        """Test that list_enabled includes registered datasets."""
        registry = DatasetRegistry()

        config = DatasetConfig(
            dataset_name="test_list_enabled",
            market=Market.CHINA_A_SHARE,
            source_name="test",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
        )
        registry.register(config)

        enabled = registry.list_enabled()
        dataset_names = [ds.dataset_name for ds in enabled]
        assert "test_list_enabled" in dataset_names

    def test_registry_upserts_on_duplicate(self):
        """Test that registry upserts on duplicate dataset_name."""
        registry = DatasetRegistry()

        config1 = DatasetConfig(
            dataset_name="test_upsert",
            market=Market.CHINA_A_SHARE,
            source_name="test",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            description="First description",
        )
        registry.register(config1)

        config2 = DatasetConfig(
            dataset_name="test_upsert",
            market=Market.CHINA_A_SHARE,
            source_name="test",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            runner_type=RunnerType.DUMMY,
            description="Updated description",
        )
        registry.register(config2)

        retrieved = registry.get("test_upsert")
        assert retrieved.description == "Updated description"
