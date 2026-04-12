"""Test script for midfreq batch 1 datasets."""

import logging
from datetime import date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_dummy_ingest():
    """Test ingestion with dummy adaptor."""
    from ifa_data_platform.midfreq.runner import MidfreqRunner

    runner = MidfreqRunner(source_name="dummy")

    runner.register_datasets()
    logger.info("Registered datasets")

    datasets = [
        "equity_daily_bar",
        "index_daily_bar",
        "etf_daily_bar",
        "northbound_flow",
        "limit_up_down_status",
    ]

    for ds in datasets:
        result = runner.run(ds)
        logger.info(
            f"{ds}: status={result.status}, records={result.records_processed}, "
            f"watermark={result.watermark}"
        )


def test_dummy_query():
    """Query data from dummy tables."""
    from ifa_data_platform.midfreq.canonical_persistence import (
        EquityDailyBarCurrent,
        EtfDailyBarCurrent,
        IndexDailyBarCurrent,
        LimitUpDownStatusCurrent,
        NorthboundFlowCurrent,
    )

    equity = EquityDailyBarCurrent()
    records = equity.list_all(limit=10)
    logger.info(f"equity_daily_bar: {len(records)} records")

    index = IndexDailyBarCurrent()
    records = index.list_all(limit=10)
    logger.info(f"index_daily_bar: {len(records)} records")

    etf = EtfDailyBarCurrent()
    records = etf.list_all(limit=10)
    logger.info(f"etf_daily_bar: {len(records)} records")

    northbound = NorthboundFlowCurrent()
    records = northbound.list_all(limit=10)
    logger.info(f"northbound_flow: {len(records)} records")

    limit = LimitUpDownStatusCurrent()
    records = limit.list_all(limit=10)
    logger.info(f"limit_up_down_status: {len(records)} records")


if __name__ == "__main__":
    logger.info("=== Testing Dummy Ingest ===")
    test_dummy_ingest()

    logger.info("\n=== Testing Dummy Query ===")
    test_dummy_query()

    logger.info("\n=== Tests Complete ===")
