#!/usr/bin/env python3
from pprint import pprint

from ifa_data_platform.runtime.health import healthcheck
from ifa_data_platform.runtime.scheduler import Scheduler
from ifa_data_platform.runtime.job_store import JobStore


def main() -> None:
    scheduler = Scheduler()
    result = scheduler.tick()
    store = JobStore()
    print("=== scheduler result ===")
    pprint(result)
    print("=== health ===")
    pprint(healthcheck())
    print("=== recent job runs ===")
    pprint(store.recent_runs(limit=5))


if __name__ == "__main__":
    main()
