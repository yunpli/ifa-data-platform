#!/usr/bin/env python
"""Job 5 Real Validation Script

Run real multi-round versioned ingestion validation for trade_cal and stock_basic.

Usage:
    # Set token first (do not hardcode):
    export TUSHARE_TOKEN="your_token_here"

    # Run validation:
    python scripts/validate_job5.py

Or run inline:
    TUSHARE_TOKEN="your_token" .venv/bin/python scripts/validate_job5.py
"""

import logging
import os
import sys
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        logger.error(
            "TUSHARE_TOKEN not set. Set via: export TUSHARE_TOKEN='your_token'"
        )
        return 1

    logger.info(f"Token loaded: {token[:8]}...")

    from ifa_data_platform.lowfreq.runner import LowFreqRunner
    from ifa_data_platform.lowfreq.version_persistence import (
        DatasetVersionRegistry,
        TradeCalHistory,
        StockBasicHistory,
    )

    vreg = DatasetVersionRegistry()
    runner = LowFreqRunner()
    tch = TradeCalHistory()
    sbh = StockBasicHistory()

    datasets = ["trade_cal", "stock_basic"]

    for ds_name in datasets:
        logger.info(f"=== Running 3 rounds for {ds_name} ===")

        # Run 3 times
        for i in range(1, 4):
            result = runner.run(ds_name, dry_run=False)
            logger.info(
                f"  Round {i}: {result.status}, {result.records_processed} records, watermark={result.watermark}"
            )

        # Check versions
        versions = vreg.list_versions(ds_name, limit=10)
        active = vreg.get_active_version(ds_name)

        logger.info(f"  Total versions: {len(versions)}")
        logger.info(f"  Active: {active['id']}")
        logger.info(f"  Promoted at: {active['promoted_at_utc']}")

        # History
        vclass = tch if ds_name == "trade_cal" else sbh
        for v in versions[:3]:
            recs = vclass.query_by_version(str(v["id"]))
            logger.info(
                f"  Version {v['id']} ({v['status']}): {len(recs)} history records"
            )

        logger.info("")

    # As-of query test
    logger.info("=== As-of query test ===")
    from ifa_data_platform.lowfreq.query import VersionQuery

    vquery = VersionQuery()

    now = datetime.now(timezone.utc)
    for ds_name in datasets:
        v_at = vquery.get_version_at(ds_name, now)
        logger.info(f"  {ds_name} at now: {v_at['id']} status={v_at['status']}")

    logger.info("\n=== Validation complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
