"""Register trade_cal and stock_basic datasets in the lowfreq registry."""

from ifa_data_platform.lowfreq.models import (
    DatasetConfig,
    JobType,
    Market,
    RunnerType,
    TimezoneSemantics,
    WatermarkStrategy,
)
from ifa_data_platform.lowfreq.registry import DatasetRegistry


def register_datasets() -> None:
    """Register trade_cal and stock_basic datasets."""
    registry = DatasetRegistry()

    trade_cal_config = DatasetConfig(
        dataset_name="trade_cal",
        market=Market.CHINA_A_SHARE,
        source_name="tushare",
        job_type=JobType.INCREMENTAL,
        enabled=True,
        timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
        runner_type=RunnerType.TUSHARE,
        watermark_strategy=WatermarkStrategy.DATE_BASED,
        budget_records_max=10000,
        budget_seconds_max=300,
        metadata={
            "api_name": "trade_cal",
            "exchange": "SSE",
            "description": "China-market trading calendar (SSE)",
        },
        description="China A-share trading calendar from Tushare",
    )

    stock_basic_config = DatasetConfig(
        dataset_name="stock_basic",
        market=Market.CHINA_A_SHARE,
        source_name="tushare",
        job_type=JobType.SNAPSHOT,
        enabled=True,
        timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
        runner_type=RunnerType.TUSHARE,
        watermark_strategy=WatermarkStrategy.NONE,
        budget_records_max=10000,
        budget_seconds_max=300,
        metadata={
            "api_name": "stock_basic",
            "list_status": "L",
            "description": "A-share instrument master data",
        },
        description="A-share instrument master data from Tushare",
    )

    print("Registering datasets...")
    trade_cal_id = registry.register(trade_cal_config)
    print(f"  trade_cal registered: {trade_cal_id}")

    stock_basic_id = registry.register(stock_basic_config)
    print(f"  stock_basic registered: {stock_basic_id}")

    print("\nEnabled datasets:")
    for ds in registry.list_enabled():
        print(
            f"  - {ds.dataset_name} (runner: {ds.runner_type.value}, watermark: {ds.watermark_strategy.value})"
        )


if __name__ == "__main__":
    register_datasets()
