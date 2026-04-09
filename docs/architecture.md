# Architecture

## Overview

Provider-agnostic data platform for IFA/FIT processing.

## Data Model

- `source_registry`: Track data sources
- `job_runs`: Execution tracking
- `raw_records`: Raw ingested data
- `items`: Processed items
- `official_events`: Regulatory events
- `market_bars`: Market data bars
- `filings`: SEC filings
- `facts`: Normalized facts
- `fact_sources`: Fact source definitions
- `slot_materializations`: Slot cache data

## Technology Stack

- Python 3.11+
- SQLAlchemy 2.0+ (ORM)
- Alembic (migrations)
- PostgreSQL (target database)

## Schema

All core tables reside in `ifa2` schema.
