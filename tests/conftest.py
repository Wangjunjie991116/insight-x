"""Pytest configuration and fixtures."""

import pytest

from src.config import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        app_name="Insight-X-Test",
        debug=True,
        llm_provider="anthropic",
        anthropic_api_key="test-key",
        database_url="sqlite+aiosqlite:///./test_insight_x.db",
    )
