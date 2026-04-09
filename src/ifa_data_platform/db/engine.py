from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from ifa_data_platform.config.settings import get_settings


def make_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, future=True)
