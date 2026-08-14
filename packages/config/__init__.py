import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CommonSettings(BaseSettings):
    """Shared configuration settings across all SovereignForge microservices."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sovereignforge"
    redis_url: str = "redis://localhost:6379/0"
    gateway_url: str = "http://localhost:8000"
    mock_worker_url: str = "http://localhost:8001"
    vllm_base_url: str = "http://localhost:8000/v1"
    ollama_base_url: str = "http://localhost:11434"
    groq_api_key: str = ""
    default_model: str = "mock-qwen-32b"
    log_level: str = "INFO"


common_settings = CommonSettings()
