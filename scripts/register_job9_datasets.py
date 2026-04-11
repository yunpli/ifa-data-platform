"""Register Job 9 datasets in the lowfreq registry."""

from ifa_data_platform.lowfreq.models import (
    DatasetConfig,
    JobType,
    Market,
    RunnerType,
    TimezoneSemantics,
    WatermarkStrategy,
)
from ifa_data_platform.lowfreq.registry import DatasetRegistry


def register_job9_datasets() -> None:
    """Register Job 9 datasets."""
    registry = DatasetRegistry()

    datasets = [
        DatasetConfig(
            dataset_name="etf_basic",
            market=Market.CHINA_A_SHARE,
            source_name="tushare",
            job_type=JobType.SNAPSHOT,
            enabled=True,
            timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
            runner_type=RunnerType.TUSHARE,
            watermark_strategy=WatermarkStrategy.NONE,
            budget_records_max=5000,
            budget_seconds_max=300,
            metadata={
                "api_name": "fund_basic",
                "description": "ETF master data",
            },
            description="ETF master data from Tushare",
        ),
        DatasetConfig(
            dataset_name="news_basic",
            market=Market.CHINA_A_SHARE,
            source_name="tushare",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
            runner_type=RunnerType.TUSHARE,
            watermark_strategy=WatermarkStrategy.NONE,
            budget_records_max=5000,
            budget_seconds_max=300,
            metadata={
                "api_name": "news",
                "description": "China-market financial news metadata",
            },
            description="China-market financial news metadata from Tushare",
        ),
        DatasetConfig(
            dataset_name="stock_repurchase",
            market=Market.CHINA_A_SHARE,
            source_name="tushare",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
            runner_type=RunnerType.TUSHARE,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
            budget_records_max=5000,
            budget_seconds_max=300,
            metadata={
                "api_name": "stock_repurchase",
                "description": "Stock repurchase announcements",
            },
            description="Stock repurchase announcements from Tushare",
        ),
        DatasetConfig(
            dataset_name="stock_dividend",
            market=Market.CHINA_A_SHARE,
            source_name="tushare",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
            runner_type=RunnerType.TUSHARE,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
            budget_records_max=5000,
            budget_seconds_max=300,
            metadata={
                "api_name": "dividend",
                "description": "Dividend announcements",
            },
            description="Dividend announcements from Tushare",
        ),
        DatasetConfig(
            dataset_name="stk_managers",
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
                "api_name": "stk_managers",
                "description": "Management team information",
            },
            description="Management team information from Tushare",
        ),
        DatasetConfig(
            dataset_name="new_share",
            market=Market.CHINA_A_SHARE,
            source_name="tushare",
            job_type=JobType.SNAPSHOT,
            enabled=True,
            timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
            runner_type=RunnerType.TUSHARE,
            watermark_strategy=WatermarkStrategy.NONE,
            budget_records_max=5000,
            budget_seconds_max=300,
            metadata={
                "api_name": "new_share",
                "description": "IPO schedule and results",
            },
            description="IPO schedule and results from Tushare",
        ),
        DatasetConfig(
            dataset_name="name_change",
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
                "api_name": "stock_namechange",
                "description": "Security name change history",
            },
            description="Security name change history from Tushare",
        ),
        DatasetConfig(
            dataset_name="management",
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
                "api_name": "stock_manager",
                "description": "Management team information",
            },
            description="Management team information from Tushare",
        ),
        DatasetConfig(
            dataset_name="stock_equity_change",
            market=Market.CHINA_A_SHARE,
            source_name="tushare",
            job_type=JobType.INCREMENTAL,
            enabled=True,
            timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
            runner_type=RunnerType.TUSHARE,
            watermark_strategy=WatermarkStrategy.DATE_BASED,
            budget_records_max=5000,
            budget_seconds_max=300,
            metadata={
                "api_name": "stock_equity_change",
                "description": "Equity changes (capital increase/decrease)",
            },
            description="Equity changes from Tushare",
        ),
    ]

    print("Registering Job 9 datasets...")
    for config in datasets:
        dataset_id = registry.register(config)
        print(f"  {config.dataset_name} registered: {dataset_id}")

    print("\nAll Job 9 datasets registered:")
    for ds in registry.list_all():
        if ds.dataset_name in [d.dataset_name for d in datasets]:
            print(
                f"  - {ds.dataset_name} (runner: {ds.runner_type.value}, watermark: {ds.watermark_strategy.value})"
            )


if __name__ == "__main__":
    register_job9_datasets()
