"""Adaptor factory for creating adaptors by runner type."""

from ifa_data_platform.lowfreq.adaptor import BaseAdaptor
from ifa_data_platform.lowfreq.models import RunnerType


def get_adaptor(runner_type: RunnerType) -> BaseAdaptor:
    """Get an adaptor instance based on runner type.

    This is a simple factory that returns the appropriate adaptor.
    In production, this could be extended to support plugin discovery
    or configuration-based adaptor selection.

    Args:
        runner_type: The runner type identifier.

    Returns:
        BaseAdaptor instance.

    Raises:
        ValueError: If runner type is not supported.
    """
    if runner_type == RunnerType.DUMMY:
        from ifa_data_platform.lowfreq.adaptors.dummy import DummyAdaptor

        return DummyAdaptor()
    elif runner_type == RunnerType.TUSHARE:
        from ifa_data_platform.lowfreq.adaptors.tushare import TushareAdaptor

        return TushareAdaptor()
    elif runner_type == RunnerType.GENERIC:
        from ifa_data_platform.lowfreq.adaptors.dummy import DummyAdaptor

        return DummyAdaptor()
    else:
        raise ValueError(f"Unsupported runner type: {runner_type}")


__all__ = ["get_adaptor"]
