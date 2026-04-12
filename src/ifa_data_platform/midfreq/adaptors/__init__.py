"""Midfreq adaptor exports."""

from ifa_data_platform.midfreq.adaptor import BaseAdaptor, FetchResult
from ifa_data_platform.midfreq.adaptor_factory import get_midfreq_adaptor
from ifa_data_platform.midfreq.adaptors.dummy import DummyMidfreqAdaptor
from ifa_data_platform.midfreq.adaptors.tushare import MidfreqTushareAdaptor

__all__ = [
    "BaseAdaptor",
    "FetchResult",
    "get_midfreq_adaptor",
    "DummyMidfreqAdaptor",
    "MidfreqTushareAdaptor",
]
