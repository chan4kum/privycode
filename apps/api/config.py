import os
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "SovereignForge API Gateway"
    version: str = "1.0.0"
    environment: str = "development"
    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/sovereignforge")
    redis_url: str = Field(default="redis://localhost:6379/0")
    default_rpm_limit: int = 60
    token_bucket_capacity: int = 60
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
