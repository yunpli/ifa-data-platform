# IFA Data Platform

Clean Python data platform for IFA/FIT processing, independent from old ICD chains and OpenClaw.

## Architecture

See [docs/architecture.md](docs/architecture.md) for system architecture.

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Run tests
pytest
```

## Documentation

- [Architecture](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [Migration Notes](docs/migration_notes.md)
