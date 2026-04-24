from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from ifa_data_platform.config.settings import get_settings


@lru_cache(maxsize=1)
def make_engine() -> Engine:
    settings = get_settings()
    return make_engine_for_url(settings.database_url)


def make_engine_for_url(database_url: str) -> Engine:
    return create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_recycle=1800,
    )
