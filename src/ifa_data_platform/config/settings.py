from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://localhost/ifa_data_platform"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
