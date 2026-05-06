"""Tests for sandbox executor."""

import pytest

from src.sandbox.executor import SandboxExecutor, SandboxResult


def test_sandbox_result_creation():
    """Test sandbox result creation."""
    result = SandboxResult(
        success=True,
        output={"test": "data"},
        logs="Test logs",
        duration_ms=100,
    )
    assert result.success is True
    assert result.output == {"test": "data"}
    assert result.duration_ms == 100


def test_sandbox_result_to_execution_result():
    """Test conversion to ExecutionResult."""
    result = SandboxResult(
        success=True,
        output={"test": "data"},
        logs="Test logs",
        duration_ms=100,
    )
    exec_result = result.to_execution_result()
    assert exec_result.success is True
    assert exec_result.output == {"test": "data"}


@pytest.mark.skip(reason="Requires Docker daemon running")
def test_sandbox_executor_simple_code():
    """Test executing simple code in sandbox."""
    executor = SandboxExecutor()
    result = executor.execute('result = {"message": "hello world"}')
    assert result.success is True
    assert result.output["message"] == "hello world"
