"""代码执行 Agent：在线程池中调用 SandboxExecutor，避免阻塞事件循环。"""

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
    """流水线第四步：同步沙箱封装为 async 接口；异常时降级为失败 ExecutionResult。"""

    def __init__(self) -> None:
        """显式传入 llm_client=None：本 Agent 不调用语言模型。"""
        super().__init__(llm_client=None)
        self._sandbox = SandboxExecutor()

    @property
    def name(self) -> str:
        return "CodeExecutionAgent"

    @property
    def description(self) -> str:
        return "Executes Python code in a secure Docker sandbox"

    async def execute(self, input_data: CodeExecutionInput) -> ExecutionResult:
        """run_in_executor 包装同步沙箱；失败返回结构化错误而非抛到编排器。"""
        self._log_execution("Executing code in sandbox...")
        try:
            # 沙箱为阻塞 IO/子进程，默认线程池卸载以防卡住 asyncio
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
