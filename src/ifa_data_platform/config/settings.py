from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp"
    log_level: str = "INFO"
    env: str = "dev"
    db_schema: str = "ifa2"
    job_poll_interval_sec: int = 30
    job_default_timeout_sec: int = 300
    job_default_retries: int = 3
    redis_url: str = "redis://localhost:6379/0"
    tushare_token: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
