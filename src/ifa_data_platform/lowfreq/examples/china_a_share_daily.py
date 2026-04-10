"""Example low-frequency dataset: China A-share daily market snapshot.

This is a minimal example dataset proving the registry -> runner -> state update chain.
In production, this would be replaced by actual Tushare dataset jobs.
"""

from ifa_data_platform.lowfreq.models import (
    DatasetConfig,
    JobType,
    Market,
    RunnerType,
    TimezoneSemantics,
    WatermarkStrategy,
)
from ifa_data_platform.lowfreq.registry import DatasetRegistry


def register_example_dataset() -> str:
    """Register the example China A-share daily market dataset."""
    registry = DatasetRegistry()

    config = DatasetConfig(
        dataset_name="china_a_share_daily",
        market=Market.CHINA_A_SHARE,
        source_name="tushare",
        job_type=JobType.INCREMENTAL,
        enabled=True,
        timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
        runner_type=RunnerType.DUMMY,
        watermark_strategy=WatermarkStrategy.DATE_BASED,
        budget_records_max=5000,
        budget_seconds_max=300,
        metadata={
            "api_name": "daily",
            "fields": "ts_code,trade_date,open,high,low,close,vol",
        },
        description="China A-share daily market data - example dataset for framework validation",
    )

    dataset_id = registry.register(config)
    print(f"Registered example dataset: {config.dataset_name} (ID: {dataset_id})")
    return dataset_id


if __name__ == "__main__":
    register_example_dataset()
