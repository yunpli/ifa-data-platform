from __future__ import annotations

from ifa_data_platform.runtime.job_state import JobStatus
from ifa_data_platform.runtime.job_store import JobStore


class DummyWorker:
    def __init__(self) -> None:
        self.store = JobStore()

    def run_dummy_job(self, job_name: str = "dummy_source_healthcheck") -> str:
        record = self.store.create_run(job_name)
        self.store.update_status(record.id, JobStatus.RUNNING)
        self.store.update_status(record.id, JobStatus.SUCCEEDED)
        return record.id
