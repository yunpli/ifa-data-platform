"""Unified runner for low-frequency dataset jobs."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.lowfreq.adaptor_factory import get_adaptor
from ifa_data_platform.lowfreq.models import DatasetConfig, JobStatus, RunnerType
from ifa_data_platform.lowfreq.registry import DatasetRegistry
from ifa_data_platform.lowfreq.run_state import RunStateManager
from ifa_data_platform.lowfreq.version_persistence import (
    DatasetVersionRegistry,
    StockBasicHistory,
    TradeCalHistory,
    VersionStatus,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class LowFreqRunner:
    """Unified runner for low-frequency dataset ingestion.

    Supports:
    - Dataset registration
    - Execute-by-dataset
    - Dry-run and real-run modes
    - Run state tracking
    - Watermark management
    - Version lifecycle (candidate -> promote -> active)
    """

    def __init__(self) -> None:
        self.registry = DatasetRegistry()
        self.run_state_manager = RunStateManager()
        self._version_registry = DatasetVersionRegistry()
        self._trade_cal_history = TradeCalHistory()
        self._stock_basic_history = StockBasicHistory()

    def run(
        self,
        dataset_name: str,
        dry_run: bool = False,
        run_type: str = "manual",
        skip_promote: bool = False,
    ) -> RunState:
        """Execute a dataset job.

        Args:
            dataset_name: Name of the dataset to run.
            dry_run: If True, simulate execution without writing data.
            run_type: Type of run (manual, scheduled, etc.).
            skip_promote: If True, skip promotion (create candidate only).

        Returns:
            RunState with final status.
        """
        config = self.registry.get(dataset_name)
        if not config:
            raise ValueError(f"Dataset not found: {dataset_name}")

        if not config.enabled:
            raise ValueError(f"Dataset is disabled: {dataset_name}")

        run_state = self.run_state_manager.create_run(
            dataset_name=dataset_name,
            dry_run=dry_run,
            run_type=run_type,
        )

        logger.info(
            f"Starting run {run_state.run_id} for dataset {dataset_name} (dry_run={dry_run})"
        )

        self.run_state_manager.update_status(run_state.run_id, "running")

        version_id = None

        try:
            if dry_run:
                logger.info(f"[DRY RUN] Would execute dataset: {dataset_name}")
                self.run_state_manager.update_status(
                    run_state.run_id,
                    "succeeded",
                    records_processed=0,
                    watermark=None,
                )
            else:
                adaptor = get_adaptor(config.runner_type)

                latest_run = self.run_state_manager.get_latest_for_dataset(dataset_name)
                watermark = latest_run.watermark if latest_run else None

                version_id = self._version_registry.create_version(
                    dataset_name=dataset_name,
                    source_name=config.source_name,
                    run_id=run_state.run_id,
                    watermark=watermark,
                )

                logger.info(
                    f"Created candidate version {version_id} for dataset {dataset_name}"
                )

                result = adaptor.fetch(
                    dataset_name=dataset_name,
                    watermark=watermark,
                    limit=config.budget_records_max,
                    run_id=run_state.run_id,
                    source_name=config.source_name,
                    version_id=version_id,
                )

                logger.info(
                    f"Fetched {len(result.records)} records for dataset {dataset_name}, "
                    f"watermark={result.watermark}"
                )

                self._store_version_history(dataset_name, version_id, result.records)

                if not skip_promote:
                    self._version_registry.promote(dataset_name, version_id)
                    logger.info(
                        f"Promoted version {version_id} to active for dataset {dataset_name}"
                    )

                self.run_state_manager.update_status(
                    run_state.run_id,
                    "succeeded",
                    records_processed=len(result.records),
                    watermark=result.watermark,
                )

        except Exception as e:
            logger.error(f"Run {run_state.run_id} failed: {e}")
            self.run_state_manager.update_status(
                run_state.run_id,
                "failed",
                error_message=str(e),
            )
            raise

        final_state = self.run_state_manager.get(run_state.run_id)
        logger.info(
            f"Run {run_state.run_id} completed with status: {final_state.status}"
        )
        return final_state

    def _store_version_history(
        self,
        dataset_name: str,
        version_id: str,
        records: list[dict],
    ) -> None:
        """Store records to version history tables.

        Args:
            dataset_name: Name of the dataset.
            version_id: Version ID.
            records: Records to store.
        """
        if dataset_name == "trade_cal":
            self._trade_cal_history.store_version(version_id, records)
            logger.info(f"Stored {len(records)} trade_cal records to history")
        elif dataset_name == "stock_basic":
            self._stock_basic_history.store_version(version_id, records)
            logger.info(f"Stored {len(records)} stock_basic records to history")

    def promote(
        self,
        dataset_name: str,
        version_id: str,
    ) -> bool:
        """Promote a candidate version to active.

        Args:
            dataset_name: Name of the dataset.
            version_id: ID of the version to promote.

        Returns:
            True if successful.
        """
        return self._version_registry.promote(dataset_name, version_id)

    def get_active_version(self, dataset_name: str) -> Optional[dict]:
        """Get the active version for a dataset.

        Args:
            dataset_name: Name of the dataset.

        Returns:
            Version dict if found, None otherwise.
        """
        return self._version_registry.get_active_version(dataset_name)

    def run_all(self, dry_run: bool = False) -> list[RunState]:
        """Execute all enabled datasets.

        Args:
            dry_run: If True, simulate execution without writing data.

        Returns:
            List of RunState for each dataset.
        """
        datasets = self.registry.list_enabled()
        results = []

        for config in datasets:
            try:
                result = self.run(config.dataset_name, dry_run=dry_run)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to run dataset {config.dataset_name}: {e}")
                results.append(
                    self.run_state_manager.get_latest_for_dataset(config.dataset_name)
                )

        return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Low-frequency dataset runner")
    parser.add_argument(
        "--dataset",
        type=str,
        help="Dataset name to run (default: run all enabled)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without writing data",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all datasets",
    )
    parser.add_argument(
        "--run-type",
        type=str,
        default="manual",
        help="Type of run (manual, scheduled)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    runner = LowFreqRunner()

    if args.list:
        datasets = runner.registry.list_all()
        print(
            f"{'Dataset Name':<30} {'Market':<15} {'Source':<15} {'Enabled':<8} {'Runner'}"
        )
        print("-" * 90)
        for ds in datasets:
            print(
                f"{ds.dataset_name:<30} {ds.market.value:<15} {ds.source_name:<15} {str(ds.enabled):<8} {ds.runner_type.value}"
            )
        return 0

    if args.dataset:
        try:
            state = runner.run(
                args.dataset, dry_run=args.dry_run, run_type=args.run_type
            )
            print(f"Run completed: {state.status}")
            return 0 if state.status == "succeeded" else 1
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        results = runner.run_all(dry_run=args.dry_run)
        succeeded = sum(1 for r in results if r and r.status == "succeeded")
        failed = sum(1 for r in results if r and r.status == "failed")
        print(f"Completed: {succeeded} succeeded, {failed} failed")
        return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
