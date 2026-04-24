from __future__ import annotations

import os
from pathlib import Path

from ifa_data_platform.config.settings import get_settings


CANONICAL_DATABASE_URL = "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp"
REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_ARTIFACT_ROOT = REPO_ROOT / "artifacts"


class TestLiveIsolationError(RuntimeError):
    """Raised when a test-oriented FSJ flow points at canonical/live roots."""


def _is_test_oriented_flow() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _resolve_database_url() -> str:
    explicit = os.environ.get("DATABASE_URL")
    if explicit:
        return explicit.strip()
    return get_settings().database_url.strip()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def enforce_non_live_test_roots(*, flow_name: str, output_path: str | Path | None) -> None:
    if not _is_test_oriented_flow():
        return

    database_url = _resolve_database_url()
    if database_url == CANONICAL_DATABASE_URL:
        raise TestLiveIsolationError(
            f"{flow_name} blocked under pytest: DATABASE_URL points at canonical/live DB; set DATABASE_URL to an explicit test DB before invoking this flow"
        )

    if output_path is None:
        return

    resolved_output = Path(output_path).expanduser().resolve()
    if _is_within(resolved_output, CANONICAL_ARTIFACT_ROOT):
        raise TestLiveIsolationError(
            f"{flow_name} blocked under pytest: output path resolves inside canonical artifacts root {CANONICAL_ARTIFACT_ROOT}; use a temp/test output root instead"
        )
