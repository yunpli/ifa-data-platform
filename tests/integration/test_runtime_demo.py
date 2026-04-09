from ifa_data_platform.runtime.job_state import JobStatus


def test_job_status_enum_contains_expected_values():
    assert JobStatus.PENDING == "pending"
    assert JobStatus.SUCCEEDED == "succeeded"
