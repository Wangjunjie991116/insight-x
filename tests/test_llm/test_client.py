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


def test_llm_client_invoke():
    """Test synchronous invoke."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Test sync response"
    mock_model.invoke = MagicMock(return_value=mock_response)

    client = LLMClient(model=mock_model)
    result = client.invoke("test prompt")

    assert result == "Test sync response"
    mock_model.invoke.assert_called_once_with("test prompt")


@pytest.mark.asyncio
async def test_llm_client_ainvoke_with_system():
    """Test async invoke with system prompt."""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Test response with system"

    async def mock_ainvoke(messages):
        return mock_response

    mock_model.ainvoke = mock_ainvoke

    client = LLMClient(model=mock_model)
    result = await client.ainvoke_with_system(
        system_prompt="You are helpful",
        user_prompt="Hello"
    )

    assert result == "Test response with system"
