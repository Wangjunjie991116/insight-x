"""Configuration management using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Insight-X"
    debug: bool = False

    # LLM Configuration
    llm_provider: str = "anthropic"  # "anthropic" or "openai"
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""  # Optional, for custom API endpoint
    openai_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"  # or "gpt-4o"

    # Database
    database_url: str = "sqlite+aiosqlite:///./insight_x.db"

    # Docker Sandbox
    sandbox_image: str = "python:3.11-slim"
    sandbox_memory_limit: str = "2g"
    sandbox_cpu_quota: int = 100000  # 1 CPU
    sandbox_timeout: int = 300  # 5 minutes

    # Redis (optional, for task queue)
    redis_url: str = ""


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
