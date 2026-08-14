import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """SovereignForge API Gateway production settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SovereignForge API Gateway"
    version: str = "1.0.0"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sovereignforge"
    redis_url: str = "redis://localhost:6379/0"
    default_rpm_limit: int = 60
    token_bucket_capacity: int = 60
    log_level: str = "INFO"


settings = Settings()
