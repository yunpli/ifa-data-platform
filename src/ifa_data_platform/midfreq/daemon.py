"""Midfreq compatibility wrapper.

Official long-running production entry is the unified runtime daemon:
`python3 -m ifa_data_platform.runtime.unified_daemon --loop`

This module remains for direct/manual midfreq testing and compatibility only.
Do not treat `midfreq.daemon --loop` as the primary production runtime model.
"""

from __future__ import annotations

import argparse
import json

from ifa_data_platform.runtime.unified_daemon import UnifiedRuntimeDaemon


def main() -> None:
    parser = argparse.ArgumentParser(description="Midfreq compatibility wrapper")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--loop", action="store_true", help="Deprecated compatibility flag; use unified runtime daemon --loop instead")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--dry-run-manifest-only", action="store_true")
    parser.add_argument("--runtime-budget-sec", type=int)
    args = parser.parse_args()

    daemon = UnifiedRuntimeDaemon()

    if args.health:
        print(json.dumps(daemon.status(), ensure_ascii=False, indent=2, default=str))
        return

    if args.loop:
        raise SystemExit("midfreq --loop has been demoted. Use: python3 -m ifa_data_platform.runtime.unified_daemon --loop")

    result = daemon.run_manual(
        "midfreq",
        dry_run_manifest_only=args.dry_run_manifest_only or args.once,
        runtime_budget_sec=args.runtime_budget_sec,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
