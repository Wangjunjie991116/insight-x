"""Base agent class for all agents."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from src.llm.client import LLMClient

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")


class BaseAgent(ABC, Generic[InputType, OutputType]):
    """Base class for all AI agents."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        """Initialize agent with LLM client."""
        self._llm = llm_client or LLMClient()

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Agent description."""
        pass

    @abstractmethod
    async def execute(self, input_data: InputType) -> OutputType:
        """Execute agent logic."""
        pass

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM with prompts."""
        return await self._llm.ainvoke_with_system(system_prompt, user_prompt)

    def _log_execution(self, message: str) -> None:
        """Log execution message."""
        print(f"[{self.name}] {message}")


class AgentResult(Generic[OutputType]):
    """Result from agent execution."""

    def __init__(
        self,
        success: bool,
        output: OutputType | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.success = success
        self.output = output
        self.error = error
        self.metadata = metadata or {}

    @classmethod
    def ok(cls, output: OutputType, **metadata: Any) -> "AgentResult[OutputType]":
        """Create successful result."""
        return cls(success=True, output=output, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata: Any) -> "AgentResult[OutputType]":
        """Create failed result."""
        return cls(success=False, error=error, metadata=metadata)
