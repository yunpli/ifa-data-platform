"""Compatibility entrypoint for archive daemon.

Canonical implementation lives in `archive_daemon.py`.
This module exists so docs/CLI can consistently use:

    python -m ifa_data_platform.archive.daemon

without breaking older references.
"""

from ifa_data_platform.archive.archive_daemon import main


if __name__ == "__main__":
    raise SystemExit(main())
