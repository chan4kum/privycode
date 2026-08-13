import os
from pydantic import Field
from pydantic_settings import BaseSettings

class CommonSettings(BaseSettings):
    """Shared configuration settings across all SovereignForge microservices."""
    environment: str = Field(default="development", env="ENVIRONMENT")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/sovereignforge",
        env="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    gateway_url: str = Field(default="http://localhost:8000", env="GATEWAY_URL")
    mock_worker_url: str = Field(default="http://localhost:8001", env="MOCK_WORKER_URL")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        extra = "ignore"

common_settings = CommonSettings()
