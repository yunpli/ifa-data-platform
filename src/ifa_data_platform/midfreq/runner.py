"""Runner module for mid-frequency dataset ingestion."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from ifa_data_platform.midfreq.adaptor_factory import get_midfreq_adaptor
from ifa_data_platform.midfreq.models import RunState
from ifa_data_platform.midfreq.registry import MidfreqDatasetRegistry
from ifa_data_platform.midfreq.version_persistence import DatasetVersionRegistry

logger = logging.getLogger(__name__)


class RunnerResult:
    """Result of a runner execution."""

    def __init__(
        self,
        run_id: str,
        dataset_name: str,
        status: str,
        records_processed: int,
        watermark: Optional[str] = None,
        error_message: Optional[str] = None,
        version_id: Optional[str] = None,
    ) -> None:
        self.run_id = run_id
        self.dataset_name = dataset_name
        self.status = status
        self.records_processed = records_processed
        self.watermark = watermark
        self.error_message = error_message
        self.version_id = version_id


class MidfreqRunner:
    """Runner for mid-frequency datasets."""

    def __init__(
        self,
        source_name: str = "tushare",
    ) -> None:
        self.source_name = source_name
        self.adaptor = get_midfreq_adaptor(source_name)
        self.dataset_registry = MidfreqDatasetRegistry()
        self.version_registry = DatasetVersionRegistry()

    def run(
        self,
        dataset_name: str,
        watermark: Optional[str] = None,
        limit: Optional[int] = None,
        dry_run: bool = False,
    ) -> RunnerResult:
        """Run ingestion for a single dataset.

        Args:
            dataset_name: Name of the dataset to run.
            watermark: Optional watermark (trade_date).
            limit: Optional record limit.
            dry_run: If True, don't persist to database.

        Returns:
            RunnerResult with execution details.
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        logger.info(f"Starting midfreq run {run_id} for {dataset_name}")

        version_id: Optional[str] = None
        if not dry_run:
            version_id = self.version_registry.create_version(
                dataset_name=dataset_name,
                source_name=self.source_name,
                run_id=run_id,
                watermark=watermark,
            )

        try:
            fetch_result = self.adaptor.fetch(
                dataset_name=dataset_name,
                watermark=watermark,
                limit=limit,
                run_id=run_id,
                source_name=self.source_name,
                version_id=version_id,
            )

            records_processed = len(fetch_result.records)
            watermark = fetch_result.watermark

            if dry_run:
                logger.info(
                    f"[DRY RUN] {dataset_name}: {records_processed} records fetched"
                )
                return RunnerResult(
                    run_id=run_id,
                    dataset_name=dataset_name,
                    status="dry_run",
                    records_processed=records_processed,
                    watermark=watermark,
                )

            logger.info(f"{dataset_name}: {records_processed} records processed")

            if records_processed > 0 and version_id:
                self.version_registry.promote(dataset_name, version_id)
                self._persist_current_to_history(dataset_name, version_id)

            return RunnerResult(
                run_id=run_id,
                dataset_name=dataset_name,
                status="succeeded",
                records_processed=records_processed,
                watermark=watermark,
                version_id=version_id,
            )

        except Exception as e:
            logger.error(f"Failed to run {dataset_name}: {e}")
            return RunnerResult(
                run_id=run_id,
                dataset_name=dataset_name,
                status="failed",
                records_processed=0,
                error_message=str(e),
                version_id=version_id,
            )

    def register_datasets(self) -> None:
        """Register midfreq datasets if not already registered."""
        datasets = [
            {
                "dataset_name": "equity_daily_bar",
                "description": "A-share equity daily OHLCV for B Universe",
            },
            {
                "dataset_name": "index_daily_bar",
                "description": "Index daily OHLCV",
            },
            {
                "dataset_name": "etf_daily_bar",
                "description": "ETF daily OHLCV",
            },
            {
                "dataset_name": "northbound_flow",
                "description": "Northbound (HK->CN) capital flow",
            },
            {
                "dataset_name": "limit_up_down_status",
                "description": "Limit up/down market status",
            },
            {
                "dataset_name": "margin_financing",
                "description": "融资融券余额与成交",
            },
            {
                "dataset_name": "turnover_rate",
                "description": "个股换手率",
            },
            {
                "dataset_name": "limit_up_detail",
                "description": "涨跌停明细",
            },
            {
                "dataset_name": "southbound_flow",
                "description": "Southbound (CN->HK) capital flow",
            },
            {
                "dataset_name": "main_force_flow",
                "description": "主力资金流",
            },
            {
                "dataset_name": "sector_performance",
                "description": "申万行业表现",
            },
            {
                "dataset_name": "dragon_tiger_list",
                "description": "龙虎榜",
            },
        ]

        for ds in datasets:
            from ifa_data_platform.midfreq.models import (
                DatasetConfig,
                JobType,
                Market,
                RunnerType,
                TimezoneSemantics,
                WatermarkStrategy,
            )

            config = DatasetConfig(
                dataset_name=ds["dataset_name"],
                market=Market.CHINA_A_SHARE,
                source_name=self.source_name,
                job_type=JobType.INCREMENTAL,
                enabled=True,
                timezone_semantics=TimezoneSemantics.CHINA_SHANGHAI,
                runner_type=RunnerType.TUSHARE,
                watermark_strategy=WatermarkStrategy.DATE_BASED,
                metadata={
                    "source_of_truth": self.source_name,
                    "registered_by": "MidfreqRunner.register_datasets",
                },
                description=ds["description"],
            )

            self.dataset_registry.register(config)
            logger.info(f"Registered midfreq dataset: {ds['dataset_name']}")

    def _persist_current_to_history(self, dataset_name: str, version_id: str) -> int:
        """Copy current records to history table for versioning.

        Idempotency rule: a re-run should not grow history when the current-table
        business row is materially unchanged. Only rows whose business key exists
        with different payload, or does not exist yet, are written as a new
        history snapshot for the new version.
        """
        from sqlalchemy import text
        from ifa_data_platform.db.engine import make_engine

        engine = make_engine()
        table_map = {
            "equity_daily_bar": (
                "equity_daily_bar_current",
                "equity_daily_bar_history",
            ),
            "index_daily_bar": ("index_daily_bar_current", "index_daily_bar_history"),
            "etf_daily_bar": ("etf_daily_bar_current", "etf_daily_bar_history"),
            "northbound_flow": ("northbound_flow_current", "northbound_flow_history"),
            "limit_up_down_status": (
                "limit_up_down_status_current",
                "limit_up_down_status_history",
            ),
            "margin_financing": (
                "margin_financing_current",
                "margin_financing_history",
            ),
            "turnover_rate": ("turnover_rate_current", "turnover_rate_history"),
            "limit_up_detail": ("limit_up_detail_current", "limit_up_detail_history"),
            "southbound_flow": ("southbound_flow_current", "southbound_flow_history"),
            "main_force_flow": ("main_force_flow_current", "main_force_flow_history"),
            "sector_performance": (
                "sector_performance_current",
                "sector_performance_history",
            ),
            "dragon_tiger_list": (
                "dragon_tiger_list_current",
                "dragon_tiger_list_history",
            ),
        }

        if dataset_name not in table_map:
            logger.warning(f"No history mapping for {dataset_name}")
            return 0

        current_table, history_table = table_map[dataset_name]

        with engine.begin() as conn:
            current_exists = conn.execute(
                text("select to_regclass(:name)"),
                {"name": f"ifa2.{current_table}"},
            ).scalar()
            history_exists = conn.execute(
                text("select to_regclass(:name)"),
                {"name": f"ifa2.{history_table}"},
            ).scalar()
            if not current_exists or not history_exists:
                logger.warning(
                    f"Skipping history persistence for {dataset_name}: current/history table missing"
                )
                return 0
            key_columns = self._get_history_key_columns(dataset_name)
            material_match_columns = self._get_history_material_match_columns(dataset_name)
            result = conn.execute(
                text(f"""
                    INSERT INTO ifa2.{history_table} (id, version_id,
                        {self._get_columns_for_history(dataset_name)})
                    SELECT gen_random_uuid(), :version_id,
                        {self._get_columns_for_insert(dataset_name)}
                    FROM ifa2.{current_table} c
                    WHERE c.version_id = :version_id
                      AND NOT EXISTS (
                        SELECT 1
                        FROM ifa2.{history_table} h
                        WHERE {key_columns}
                          AND {material_match_columns}
                      )
                """),
                {"version_id": version_id},
            )
            return result.rowcount

    def _get_columns_for_history(self, dataset_name: str) -> str:
        """Get column list for history insert."""
        column_maps = {
            "equity_daily_bar": "ts_code, trade_date, open, high, low, close, vol, amount, pre_close, change, pct_chg",
            "index_daily_bar": "ts_code, trade_date, open, high, low, close, vol, amount, pre_close, change, pct_chg",
            "etf_daily_bar": "ts_code, trade_date, open, high, low, close, vol, amount, pre_close, change, pct_chg",
            "northbound_flow": "trade_date, north_money, north_bal, north_buy, north_sell",
            "limit_up_down_status": "trade_date, limit_up_count, limit_down_count, limit_up_streak_high, limit_down_streak_high",
            "margin_financing": "ts_code, trade_date, rzye, rzmre, rzche, rzrqye, rqryl",
            "turnover_rate": "ts_code, trade_date, turnover_rate, turnover_rate_f",
            "limit_up_detail": "ts_code, trade_date, \"limit\", pre_limit",
            "southbound_flow": "trade_date, south_money, south_bal, south_buy, south_sell",
            "main_force_flow": "ts_code, trade_date, main_force, main_force_pct",
            "sector_performance": "sector_code, trade_date, sector_name, close, pct_chg, turnover_rate",
            "dragon_tiger_list": "ts_code, trade_date, buy_amount, sell_amount, net_amount",
        }
        return column_maps.get(dataset_name, "*")

    def _get_columns_for_insert(self, dataset_name: str) -> str:
        """Get SELECT column list from current table for history insert."""
        current_column_maps = {
            "limit_up_detail": 'ts_code, trade_date, limit_status AS "limit", pre_limit_status AS pre_limit',
        }
        return current_column_maps.get(dataset_name, self._get_columns_for_history(dataset_name))

    def _get_history_key_columns(self, dataset_name: str) -> str:
        key_maps = {
            "equity_daily_bar": "h.ts_code = c.ts_code AND h.trade_date = c.trade_date",
            "index_daily_bar": "h.ts_code = c.ts_code AND h.trade_date = c.trade_date",
            "etf_daily_bar": "h.ts_code = c.ts_code AND h.trade_date = c.trade_date",
            "northbound_flow": "h.trade_date = c.trade_date",
            "limit_up_down_status": "h.trade_date = c.trade_date",
            "margin_financing": "h.ts_code = c.ts_code AND h.trade_date = c.trade_date",
            "turnover_rate": "h.ts_code = c.ts_code AND h.trade_date = c.trade_date",
            "limit_up_detail": 'h.ts_code = c.ts_code AND h.trade_date = c.trade_date',
            "southbound_flow": "h.trade_date = c.trade_date",
            "main_force_flow": "h.ts_code = c.ts_code AND h.trade_date = c.trade_date",
            "sector_performance": "h.sector_code = c.sector_code AND h.trade_date = c.trade_date",
            "dragon_tiger_list": "h.ts_code = c.ts_code AND h.trade_date = c.trade_date",
        }
        return key_maps[dataset_name]

    def _get_history_material_match_columns(self, dataset_name: str) -> str:
        material_maps = {
            "equity_daily_bar": " AND ".join([
                "h.open IS NOT DISTINCT FROM c.open",
                "h.high IS NOT DISTINCT FROM c.high",
                "h.low IS NOT DISTINCT FROM c.low",
                "h.close IS NOT DISTINCT FROM c.close",
                "h.vol IS NOT DISTINCT FROM c.vol",
                "h.amount IS NOT DISTINCT FROM c.amount",
                "h.pre_close IS NOT DISTINCT FROM c.pre_close",
                "h.change IS NOT DISTINCT FROM c.change",
                "h.pct_chg IS NOT DISTINCT FROM c.pct_chg",
            ]),
            "index_daily_bar": " AND ".join([
                "h.open IS NOT DISTINCT FROM c.open",
                "h.high IS NOT DISTINCT FROM c.high",
                "h.low IS NOT DISTINCT FROM c.low",
                "h.close IS NOT DISTINCT FROM c.close",
                "h.vol IS NOT DISTINCT FROM c.vol",
                "h.amount IS NOT DISTINCT FROM c.amount",
                "h.pre_close IS NOT DISTINCT FROM c.pre_close",
                "h.change IS NOT DISTINCT FROM c.change",
                "h.pct_chg IS NOT DISTINCT FROM c.pct_chg",
            ]),
            "etf_daily_bar": " AND ".join([
                "h.open IS NOT DISTINCT FROM c.open",
                "h.high IS NOT DISTINCT FROM c.high",
                "h.low IS NOT DISTINCT FROM c.low",
                "h.close IS NOT DISTINCT FROM c.close",
                "h.vol IS NOT DISTINCT FROM c.vol",
                "h.amount IS NOT DISTINCT FROM c.amount",
                "h.pre_close IS NOT DISTINCT FROM c.pre_close",
                "h.change IS NOT DISTINCT FROM c.change",
                "h.pct_chg IS NOT DISTINCT FROM c.pct_chg",
            ]),
            "northbound_flow": " AND ".join([
                "h.north_money IS NOT DISTINCT FROM c.north_money",
                "h.north_bal IS NOT DISTINCT FROM c.north_bal",
                "h.north_buy IS NOT DISTINCT FROM c.north_buy",
                "h.north_sell IS NOT DISTINCT FROM c.north_sell",
            ]),
            "limit_up_down_status": " AND ".join([
                "h.limit_up_count IS NOT DISTINCT FROM c.limit_up_count",
                "h.limit_down_count IS NOT DISTINCT FROM c.limit_down_count",
                "h.limit_up_streak_high IS NOT DISTINCT FROM c.limit_up_streak_high",
                "h.limit_down_streak_high IS NOT DISTINCT FROM c.limit_down_streak_high",
            ]),
            "margin_financing": " AND ".join([
                "h.rzye IS NOT DISTINCT FROM c.rzye",
                "h.rzmre IS NOT DISTINCT FROM c.rzmre",
                "h.rzche IS NOT DISTINCT FROM c.rzche",
                "h.rzrqye IS NOT DISTINCT FROM c.rzrqye",
                "h.rqryl IS NOT DISTINCT FROM c.rqryl",
            ]),
            "turnover_rate": " AND ".join([
                "h.turnover_rate IS NOT DISTINCT FROM c.turnover_rate",
                "h.turnover_rate_f IS NOT DISTINCT FROM c.turnover_rate_f",
            ]),
            "limit_up_detail": " AND ".join([
                'h."limit" IS NOT DISTINCT FROM c.limit_status',
                "h.pre_limit IS NOT DISTINCT FROM c.pre_limit_status",
            ]),
            "southbound_flow": " AND ".join([
                "h.south_money IS NOT DISTINCT FROM c.south_money",
                "h.south_bal IS NOT DISTINCT FROM c.south_bal",
                "h.south_buy IS NOT DISTINCT FROM c.south_buy",
                "h.south_sell IS NOT DISTINCT FROM c.south_sell",
            ]),
            "main_force_flow": " AND ".join([
                "h.main_force IS NOT DISTINCT FROM c.main_force",
                "h.main_force_pct IS NOT DISTINCT FROM c.main_force_pct",
            ]),
            "sector_performance": " AND ".join([
                "h.sector_name IS NOT DISTINCT FROM c.sector_name",
                "h.close IS NOT DISTINCT FROM c.close",
                "h.pct_chg IS NOT DISTINCT FROM c.pct_chg",
                "h.turnover_rate IS NOT DISTINCT FROM c.turnover_rate",
            ]),
            "dragon_tiger_list": " AND ".join([
                "h.buy_amount IS NOT DISTINCT FROM c.buy_amount",
                "h.sell_amount IS NOT DISTINCT FROM c.sell_amount",
                "h.net_amount IS NOT DISTINCT FROM c.net_amount",
            ]),
        }
        return material_maps[dataset_name]
