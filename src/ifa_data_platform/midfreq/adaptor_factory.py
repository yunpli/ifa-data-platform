"""Adaptor factory for mid-frequency datasets."""

from ifa_data_platform.midfreq.adaptor import BaseAdaptor


def get_midfreq_adaptor(source_name: str = "tushare") -> BaseAdaptor:
    """Factory function to get a midfreq adaptor instance.

    Args:
        source_name: Name of the source (tushare, dummy).

    Returns:
        Configured adaptor instance.

    Raises:
        ValueError: If source_name is not supported.
    """
    if source_name == "tushare":
        from ifa_data_platform.midfreq.adaptors.tushare import MidfreqTushareAdaptor

        return MidfreqTushareAdaptor()
    elif source_name == "dummy":
        from ifa_data_platform.midfreq.adaptors.dummy import DummyMidfreqAdaptor

        return DummyMidfreqAdaptor()
    else:
        raise ValueError(f"Unsupported midfreq source: {source_name}")
