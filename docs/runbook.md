# Runbook

## Prerequisites

- Python 3.11+
- PostgreSQL 14+

## Setup

1. Copy `.env.example` to `.env` and configure
2. Install dependencies: `pip install -e ".[dev]"`
3. Run migrations: `alembic upgrade head`

## Running

```bash
# Development
pytest

# Migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```
