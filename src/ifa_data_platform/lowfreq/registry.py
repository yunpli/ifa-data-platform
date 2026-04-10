"""Dataset registry for low-frequency ingestion framework."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine
from ifa_data_platform.lowfreq.models import (
    DatasetConfig,
    JobType,
    Market,
    RunnerType,
    TimezoneSemantics,
    WatermarkStrategy,
)


class DatasetRegistry:
    """Registry for managing low-frequency dataset configurations.

    Datasets are stored in the database and can be registered, enabled/disabled,
    and queried for execution.
    """

    def __init__(self) -> None:
        self.engine = make_engine()

    def register(self, config: DatasetConfig) -> str:
        """Register a new dataset configuration.

        Args:
            config: Dataset configuration to register.

        Returns:
            Dataset ID (UUID string).
        """
        dataset_id = str(uuid.uuid4())
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ifa2.lowfreq_datasets (
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
                    "enabled": 1 if config.enabled else 0,
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
        """Get a dataset configuration by name.

        Args:
            dataset_name: Name of the dataset.

        Returns:
            DatasetConfig if found, None otherwise.
        """
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, market, source_name, job_type,
                           enabled, timezone_semantics, runner_type, watermark_strategy,
                           budget_records_max, budget_seconds_max, metadata, description,
                           created_at, updated_at
                    FROM ifa2.lowfreq_datasets
                    WHERE dataset_name = :dataset_name
                    """
                ),
                {"dataset_name": dataset_name},
            ).fetchone()

            if not row:
                return None

            return DatasetConfig(
                dataset_name=row.dataset_name,
                market=Market(row.market),
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

    def list_enabled(self) -> list[DatasetConfig]:
        """List all enabled datasets.

        Returns:
            List of enabled DatasetConfig objects.
        """
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, market, source_name, job_type,
                           enabled, timezone_semantics, runner_type, watermark_strategy,
                           budget_records_max, budget_seconds_max, metadata, description,
                           created_at, updated_at
                    FROM ifa2.lowfreq_datasets
                    WHERE enabled = 1
                    ORDER BY dataset_name
                    """
                ),
            ).fetchall()

            return [
                DatasetConfig(
                    dataset_name=row.dataset_name,
                    market=Market(row.market),
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
                for row in rows
            ]

    def list_all(self) -> list[DatasetConfig]:
        """List all datasets.

        Returns:
            List of all DatasetConfig objects.
        """
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, dataset_name, market, source_name, job_type,
                           enabled, timezone_semantics, runner_type, watermark_strategy,
                           budget_records_max, budget_seconds_max, metadata, description,
                           created_at, updated_at
                    FROM ifa2.lowfreq_datasets
                    ORDER BY dataset_name
                    """
                ),
            ).fetchall()

            return [
                DatasetConfig(
                    dataset_name=row.dataset_name,
                    market=Market(row.market),
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
                for row in rows
            ]

    def enable(self, dataset_name: str) -> bool:
        """Enable a dataset.

        Args:
            dataset_name: Name of the dataset to enable.

        Returns:
            True if updated, False if not found.
        """
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE ifa2.lowfreq_datasets
                    SET enabled = 1, updated_at = now()
                    WHERE dataset_name = :dataset_name
                    """
                ),
                {"dataset_name": dataset_name},
            )
            return result.rowcount > 0

    def disable(self, dataset_name: str) -> bool:
        """Disable a dataset.

        Args:
            dataset_name: Name of the dataset to disable.

        Returns:
            True if updated, False if not found.
        """
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE ifa2.lowfreq_datasets
                    SET enabled = 0, updated_at = now()
                    WHERE dataset_name = :dataset_name
                    """
                ),
                {"dataset_name": dataset_name},
            )
            return result.rowcount > 0
