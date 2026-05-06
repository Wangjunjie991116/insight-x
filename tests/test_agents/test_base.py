"""Tests for base agent."""

from src.agents.base import AgentResult, BaseAgent


class MockAgent(BaseAgent[str, str]):
    """Mock agent for testing."""

    @property
    def name(self) -> str:
        return "MockAgent"

    @property
    def description(self) -> str:
        return "Mock agent for testing"

    async def execute(self, input_data: str) -> str:
        return f"Processed: {input_data}"


def test_agent_result_ok():
    """Test successful agent result."""
    result = AgentResult.ok("test output", key="value")
    assert result.success is True
    assert result.output == "test output"
    assert result.metadata["key"] == "value"


def test_agent_result_fail():
    """Test failed agent result."""
    result = AgentResult.fail("test error")
    assert result.success is False
    assert result.error == "test error"


def test_mock_agent_properties():
    """Test mock agent properties."""
    agent = MockAgent()
    assert agent.name == "MockAgent"
    assert agent.description == "Mock agent for testing"
