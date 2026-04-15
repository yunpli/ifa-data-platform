"""Dataset registry for mid-frequency ingestion framework."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.midfreq.models import (
    DatasetConfig,
    JobType,
    Market,
    RunnerType,
    TimezoneSemantics,
    WatermarkStrategy,
)


class MidfreqDatasetRegistry:
    """Registry for managing mid-frequency dataset configurations."""

    def __init__(self) -> None:
        self.engine = make_engine()

    def _coerce_market(self, value: str) -> Market:
        legacy_map = {
            "B": Market.CHINA_A_SHARE,
            "china_a": Market.CHINA_A_SHARE,
            "china_a_share": Market.CHINA_A_SHARE,
            "us_equity": Market.US_EQUITY,
            "unknown": Market.UNKNOWN,
        }
        return legacy_map.get(value, Market.UNKNOWN)

    def _row_to_config(self, row) -> DatasetConfig:
        return DatasetConfig(
            dataset_name=row.dataset_name,
            market=self._coerce_market(row.market),
            source_name=row.source_name,
            job_type=JobType(row.job_type),
            enabled=bool(row.enabled),
            timezone_semantics=TimezoneSemantics(row.timezone_semantics),
            runner_type=RunnerType(row.runner_type),
            watermark_strategy=WatermarkStrategy(row.watermark_strategy),
            budget_records_max=row.budget_records_max,
            budget_seconds_max=row.budget_seconds_max,
            metadata=eval(row.metadata) if row.metadata else {},
            description=row.description or "",
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def register(self, config: DatasetConfig) -> str:
        """Register a new dataset configuration."""
        dataset_id = str(uuid.uuid4())
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.midfreq_datasets (
                        id, dataset_name, market, source_name, job_type,
                        enabled, timezone_semantics, runner_type, watermark_strategy,
                        budget_records_max, budget_seconds_max, metadata, description,
                        created_at, updated_at
                    )
                    VALUES (
                        :id, :dataset_name, :market, :source_name, :job_type,
                        :enabled, :timezone_semantics, :runner_type, :watermark_strategy,
                        :budget_records_max, :budget_seconds_max, :metadata, :description,
                        now(), now()
                    )
                    ON CONFLICT (dataset_name) DO UPDATE SET
                        market = EXCLUDED.market,
                        source_name = EXCLUDED.source_name,
                        job_type = EXCLUDED.job_type,
                        enabled = EXCLUDED.enabled,
                        timezone_semantics = EXCLUDED.timezone_semantics,
                        runner_type = EXCLUDED.runner_type,
                        watermark_strategy = EXCLUDED.watermark_strategy,
                        budget_records_max = EXCLUDED.budget_records_max,
                        budget_seconds_max = EXCLUDED.budget_seconds_max,
                        metadata = EXCLUDED.metadata,
                        description = EXCLUDED.description,
                        updated_at = now()
                    RETURNING id
                    """
                ),
                {
                    "id": dataset_id,
                    "dataset_name": config.dataset_name,
                    "market": config.market.value,
                    "source_name": config.source_name,
                    "job_type": config.job_type.value,
                    "enabled": bool(config.enabled),
                    "timezone_semantics": config.timezone_semantics.value,
                    "runner_type": config.runner_type.value,
                    "watermark_strategy": config.watermark_strategy.value,
                    "budget_records_max": config.budget_records_max,
                    "budget_seconds_max": config.budget_seconds_max,
                    "metadata": str(config.metadata),
                    "description": config.description,
                },
            )
        return dataset_id

    def get(self, dataset_name: str) -> Optional[DatasetConfig]:
        """Get a dataset configuration by name."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, market, source_name, job_type,
                           enabled, timezone_semantics, runner_type, watermark_strategy,
                           budget_records_max, budget_seconds_max, metadata, description,
                           created_at, updated_at
                    FROM ifa2.midfreq_datasets
                    WHERE dataset_name = :dataset_name
                    """
                ),
                {"dataset_name": dataset_name},
            ).fetchone()

            if not row:
                return None

            return self._row_to_config(row)

    def list_enabled(self) -> list[DatasetConfig]:
        """List all enabled datasets."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, market, source_name, job_type,
                           enabled, timezone_semantics, runner_type, watermark_strategy,
                           budget_records_max, budget_seconds_max, metadata, description,
                           created_at, updated_at
                    FROM ifa2.midfreq_datasets
                    WHERE enabled = true
                    ORDER BY dataset_name
                    """
                ),
            ).fetchall()

            return [self._row_to_config(row) for row in rows]

    def list_all(self) -> list[DatasetConfig]:
        """List all datasets."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, market, source_name, job_type,
                           enabled, timezone_semantics, runner_type, watermark_strategy,
                           budget_records_max, budget_seconds_max, metadata, description,
                           created_at, updated_at
                    FROM ifa2.midfreq_datasets
                    ORDER BY dataset_name
                    """
                ),
            ).fetchall()

            return [self._row_to_config(row) for row in rows]

    def enable(self, dataset_name: str) -> bool:
        """Enable a dataset."""
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE ifa2.midfreq_datasets
                    SET enabled = true, updated_at = now()
                    WHERE dataset_name = :dataset_name
                    """
                ),
                {"dataset_name": dataset_name},
            )
            return result.rowcount > 0

    def disable(self, dataset_name: str) -> bool:
        """Disable a dataset."""
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE ifa2.midfreq_datasets
                    SET enabled = false, updated_at = now()
                    WHERE dataset_name = :dataset_name
                    """
                ),
                {"dataset_name": dataset_name},
            )
            return result.rowcount > 0
