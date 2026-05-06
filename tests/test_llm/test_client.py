"""Tests for LLM client."""

from unittest.mock import MagicMock, patch

import pytest

from src.llm.client import LLMClient, get_llm_client


def test_llm_client_creation():
    """Test LLM client creation."""
    mock_model = MagicMock()
    client = LLMClient(model=mock_model)
    assert client._model == mock_model


@pytest.mark.asyncio
async def test_llm_client_ainvoke():
    """Test async invoke."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Test response"
    mock_model.ainvoke = MagicMock(return_value=mock_response)

    client = LLMClient(model=mock_model)

    # Mock the await
    async def mock_ainvoke(*args):
        return mock_response

    mock_model.ainvoke = mock_ainvoke

    result = await client.ainvoke("test prompt")
    assert result == "Test response"
