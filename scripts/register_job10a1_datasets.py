"""Register Job 10A1 datasets in the lowfreq registry."""

from ifa_data_platform.lowfreq.models import (
    DatasetConfig,
    JobType,
    Market,
    RunnerType,
    TimezoneSemantics,
    WatermarkStrategy,
)
from ifa_data_platform.lowfreq.registry import DatasetRegistry


def register_job10a1_datasets() -> None:
    registry = DatasetRegistry()
    datasets = [
        DatasetConfig(
            dataset_name="top10_holders",
            market=Market.CHINA_A_SHARE,
            source_name="tushare",
            job_type=JobType.SNAPSHOT,
            enabled=True,
            timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
            runner_type=RunnerType.TUSHARE,
            watermark_strategy=WatermarkStrategy.NONE,
            budget_records_max=50000,
            budget_seconds_max=600,
            metadata={"api_name": "top10_holders", "description": "Top 10 shareholders"},
            description="Top 10 shareholders from Tushare",
        ),
        DatasetConfig(
            dataset_name="top10_floatholders",
            market=Market.CHINA_A_SHARE,
            source_name="tushare",
            job_type=JobType.SNAPSHOT,
            enabled=True,
            timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
            runner_type=RunnerType.TUSHARE,
            watermark_strategy=WatermarkStrategy.NONE,
            budget_records_max=50000,
            budget_seconds_max=600,
            metadata={"api_name": "top10_floatholders", "description": "Top 10 float shareholders"},
            description="Top 10 float shareholders from Tushare",
        ),
        DatasetConfig(
            dataset_name="pledge_stat",
            market=Market.CHINA_A_SHARE,
            source_name="tushare",
            job_type=JobType.SNAPSHOT,
            enabled=True,
            timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
            runner_type=RunnerType.TUSHARE,
            watermark_strategy=WatermarkStrategy.NONE,
            budget_records_max=50000,
            budget_seconds_max=600,
            metadata={"api_name": "pledge_stat", "description": "Pledge statistics"},
            description="Pledge statistics from Tushare",
        ),
    ]

    for config in datasets:
        registry.register(config)
        print(f"registered: {config.dataset_name}")


if __name__ == "__main__":
    register_job10a1_datasets()
