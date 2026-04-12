"""Register Job 10A asset-layer lowfreq datasets."""

from ifa_data_platform.lowfreq.models import (
    DatasetConfig,
    JobType,
    Market,
    RunnerType,
    TimezoneSemantics,
    WatermarkStrategy,
)
from ifa_data_platform.lowfreq.registry import DatasetRegistry


def register_job10a_datasets() -> None:
    """Register Job 10A datasets."""
    registry = DatasetRegistry()

    top10_holders_config = DatasetConfig(
        dataset_name="top10_holders",
        market=Market.CHINA_A_SHARE,
        source_name="tushare",
        job_type=JobType.INCREMENTAL,
        enabled=True,
        timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
        runner_type=RunnerType.TUSHARE,
        watermark_strategy=WatermarkStrategy.DATE_BASED,
        budget_records_max=5000,
        budget_seconds_max=300,
        metadata={"api_name": "top10_holders"},
        description="Top 10 shareholders per stock",
    )

    top10_floatholders_config = DatasetConfig(
        dataset_name="top10_floatholders",
        market=Market.CHINA_A_SHARE,
        source_name="tushare",
        job_type=JobType.INCREMENTAL,
        enabled=True,
        timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
        runner_type=RunnerType.TUSHARE,
        watermark_strategy=WatermarkStrategy.DATE_BASED,
        budget_records_max=5000,
        budget_seconds_max=300,
        metadata={"api_name": "top10_floatholders"},
        description="Top 10 float shareholders per stock",
    )

    pledge_stat_config = DatasetConfig(
        dataset_name="pledge_stat",
        market=Market.CHINA_A_SHARE,
        source_name="tushare",
        job_type=JobType.INCREMENTAL,
        enabled=True,
        timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
        runner_type=RunnerType.TUSHARE,
        watermark_strategy=WatermarkStrategy.DATE_BASED,
        budget_records_max=5000,
        budget_seconds_max=300,
        metadata={"api_name": "pledge_stat"},
        description="Pledge statistics per stock",
    )

    forecast_config = DatasetConfig(
        dataset_name="forecast",
        market=Market.CHINA_A_SHARE,
        source_name="tushare",
        job_type=JobType.INCREMENTAL,
        enabled=True,
        timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
        runner_type=RunnerType.TUSHARE,
        watermark_strategy=WatermarkStrategy.DATE_BASED,
        budget_records_max=5000,
        budget_seconds_max=300,
        metadata={"api_name": "forecast"},
        description="Earnings forecast per stock",
    )

    margin_config = DatasetConfig(
        dataset_name="margin",
        market=Market.CHINA_A_SHARE,
        source_name="tushare",
        job_type=JobType.INCREMENTAL,
        enabled=True,
        timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
        runner_type=RunnerType.TUSHARE,
        watermark_strategy=WatermarkStrategy.DATE_BASED,
        budget_records_max=5000,
        budget_seconds_max=300,
        metadata={"api_name": "margin"},
        description="Margin trading summary",
    )

    north_south_flow_config = DatasetConfig(
        dataset_name="north_south_flow",
        market=Market.CHINA_A_SHARE,
        source_name="tushare",
        job_type=JobType.INCREMENTAL,
        enabled=True,
        timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
        runner_type=RunnerType.TUSHARE,
        watermark_strategy=WatermarkStrategy.DATE_BASED,
        budget_records_max=500,
        budget_seconds_max=60,
        metadata={"api_name": "moneyflow_hsgt"},
        description="North-south money flow (HSGT)",
    )

    print("Registering Job 10A datasets...")
    for config in [
        top10_holders_config,
        top10_floatholders_config,
        pledge_stat_config,
        forecast_config,
        margin_config,
        north_south_flow_config,
    ]:
        ds_id = registry.register(config)
        print(f"  {config.dataset_name} registered: {ds_id}")

    print("\nEnabled datasets:")
    for ds in registry.list_enabled():
        print(f"  - {ds.dataset_name}")


if __name__ == "__main__":
    register_job10a_datasets()
