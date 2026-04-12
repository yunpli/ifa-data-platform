"""Register Job 10A2 datasets in the lowfreq registry."""

from ifa_data_platform.lowfreq.models import (
    DatasetConfig,
    JobType,
    Market,
    RunnerType,
    TimezoneSemantics,
    WatermarkStrategy,
)
from ifa_data_platform.lowfreq.registry import DatasetRegistry


def register_job10a2_datasets() -> None:
    registry = DatasetRegistry()
    datasets = [
        DatasetConfig(
            dataset_name="stock_fund_forecast",
            market=Market.CHINA_A_SHARE,
            source_name="tushare",
            job_type=JobType.SNAPSHOT,
            enabled=True,
            timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
            runner_type=RunnerType.TUSHARE,
            watermark_strategy=WatermarkStrategy.NONE,
            budget_records_max=50000,
            budget_seconds_max=600,
            metadata={
                "api_name": "stock_fund_forecast",
                "description": "Stock fund forecast",
            },
            description="Stock fund forecast from Tushare",
        ),
        DatasetConfig(
            dataset_name="margin",
            market=Market.CHINA_A_SHARE,
            source_name="tushare",
            job_type=JobType.SNAPSHOT,
            enabled=True,
            timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
            runner_type=RunnerType.TUSHARE,
            watermark_strategy=WatermarkStrategy.NONE,
            budget_records_max=50000,
            budget_seconds_max=600,
            metadata={"api_name": "margin", "description": "Margin trading data"},
            description="Margin trading data from Tushare",
        ),
        DatasetConfig(
            dataset_name="north_south_flow",
            market=Market.CHINA_A_SHARE,
            source_name="tushare",
            job_type=JobType.SNAPSHOT,
            enabled=True,
            timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
            runner_type=RunnerType.TUSHARE,
            watermark_strategy=WatermarkStrategy.NONE,
            budget_records_max=50000,
            budget_seconds_max=600,
            metadata={"api_name": "moneyflow_hsgt", "description": "North-South flow"},
            description="North-South flow (moneyflow_hsgt) from Tushare",
        ),
    ]

    for config in datasets:
        registry.register(config)
        print(f"registered: {config.dataset_name}")


if __name__ == "__main__":
    register_job10a2_datasets()
