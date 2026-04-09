# Migration Notes

## v0.1.0 - Initial Schema

Initial migration creating `ifa2` schema with core tables:

- `source_registry`
- `job_runs`
- `raw_records`
- `items`
- `official_events`
- `market_bars`
- `filings`
- `facts`
- `fact_sources`
- `slot_materializations`

## Running Migrations

Once PostgreSQL is available:

```bash
# Create database (adjust PGPASSWORD/PGUSER as needed)
createdb ifa_data_platform

# Run migrations
alembic upgrade head
```

## Blockers

**PostgreSQL not running or not accessible**
- No PostgreSQL server found at localhost:5432
- To enable: install and start PostgreSQL, set PGPASSWORD/PGUSER env vars
- Run: `alembic upgrade head` after database is available
