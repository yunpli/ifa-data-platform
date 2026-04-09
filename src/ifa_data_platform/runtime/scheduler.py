from __future__ import annotations

from dataclasses import dataclass

from ifa_data_platform.runtime.worker import DummyWorker


@dataclass
class SchedulerResult:
    dispatched_job_id: str
    status: str


class Scheduler:
    def __init__(self) -> None:
        self.worker = DummyWorker()

    def tick(self) -> SchedulerResult:
        job_id = self.worker.run_dummy_job()
        return SchedulerResult(dispatched_job_id=job_id, status="ok")
