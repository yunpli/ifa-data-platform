"""Stock minute archiver using Tushare stk_mins."""

from __future__ import annotations

from datetime import datetime

from ifa_data_platform.archive.stock_15min_archiver import Stock15MinArchiver


class StockMinuteArchiver(Stock15MinArchiver):
    def run_archive(
        self,
        dataset_name: str = "stock_minute_history",
        end_time: datetime | None = None,
        limit_stocks: int = 5,
        symbols: list[str] | None = None,
    ) -> int:
        checkpoint = self.get_checkpoint(dataset_name)
        default_start, resolved_end = self._default_window(end_time)

        checkpoint_usable = bool(checkpoint and checkpoint.get("last_completed_at")) and self._table_has_rows(dataset_name)
        if checkpoint_usable:
            resolved_start = checkpoint["last_completed_at"]
        else:
            resolved_start = default_start

        # Intraday 1min archive is forward-only by business policy. No historical backfill before official start.
        resolved_start = max(resolved_start, default_start)

        stocks = self.fetch_stock_universe(limit=limit_stocks if not symbols else len(symbols), symbols=symbols)
        total_inserted = 0
        batch_no = 0
        watermark = None
        last_symbol = None

        for ts_code in stocks:
            batch_no += 1
            last_symbol = ts_code
            records = self.fetch_stock_15min(
                ts_code,
                resolved_start,
                resolved_end,
                freq="1min",
            )
            inserted = self.persist_records(records, table_name=dataset_name)
            total_inserted += inserted
            if records:
                watermark = records[-1]["trade_time"]
                self.checkpoint_store.upsert_checkpoint(
                    dataset_name=dataset_name,
                    asset_type="stock",
                    last_completed_date=watermark.date(),
                    last_completed_at=watermark,
                    shard_id=ts_code,
                    batch_no=batch_no,
                    status="in_progress",
                )

        if watermark is not None:
            self.checkpoint_store.upsert_checkpoint(
                dataset_name=dataset_name,
                asset_type="stock",
                last_completed_date=watermark.date(),
                last_completed_at=watermark,
                shard_id=last_symbol,
                batch_no=batch_no,
                status="completed",
            )

        return total_inserted
