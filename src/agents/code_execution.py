"""Code Execution Agent - executes Python code in sandbox."""

from typing import Any

from src.agents.base import BaseAgent
from src.models.result import ExecutionResult
from src.sandbox.executor import SandboxExecutor


class CodeExecutionInput:
    """Input for Code Execution Agent."""

    def __init__(
        self,
        code: str,
        db_config: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> None:
        self.code = code
        self.db_config = db_config or {}
        self.timeout = timeout


class CodeExecutionAgent(BaseAgent[CodeExecutionInput, ExecutionResult]):
    """Agent that executes Python code in Docker sandbox."""

    def __init__(self) -> None:
        """Initialize with sandbox executor."""
        super().__init__(llm_client=None)
        self._sandbox = SandboxExecutor()

    @property
    def name(self) -> str:
        return "CodeExecutionAgent"

    @property
    def description(self) -> str:
        return "Executes Python code in a secure Docker sandbox"

    async def execute(self, input_data: CodeExecutionInput) -> ExecutionResult:
        """Execute code in sandbox."""
        self._log_execution("Executing code in sandbox...")
        try:
            # Run sandbox execution (it's synchronous, so we wrap it)
            import asyncio

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._sandbox.execute(
                    code=input_data.code,
                    db_config=input_data.db_config,
                    timeout=input_data.timeout,
                ),
            )

            execution_result = result.to_execution_result()

            if result.success:
                self._log_execution(f"Code executed successfully in {result.duration_ms}ms")
            else:
                self._log_execution(f"Code execution failed: {result.error}")

            return execution_result

        except Exception as e:
            self._log_execution(f"Error: {e}")
            return ExecutionResult(
                success=False,
                output={},
                logs="",
                error=str(e),
                duration_ms=0,
            )
