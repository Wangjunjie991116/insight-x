"""Orchestrator for coordinating all agents in the analysis pipeline."""

import json
from typing import Any

from src.agents import (
    AnalysisStrategyAgent,
    AnalysisStrategyInput,
    CodeExecutionAgent,
    CodeExecutionInput,
    CodeGenerationAgent,
    CodeGenerationInput,
    DataUnderstandingAgent,
    InsightGenerationAgent,
    InsightGenerationInput,
)
from src.db.connector import DatabaseConnector
from src.models.result import AnalysisResult, DataDictionary, ExecutionResult, Insight
from src.models.task import AnalysisTask, DatabaseConfig


class AnalysisOrchestrator:
    """Orchestrates the complete analysis pipeline."""

    def __init__(self) -> None:
        """Initialize orchestrator with all agents."""
        self._data_understanding_agent = DataUnderstandingAgent()
        self._strategy_agent = AnalysisStrategyAgent()
        self._code_gen_agent = CodeGenerationAgent()
        self._code_exec_agent = CodeExecutionAgent()
        self._insight_agent = InsightGenerationAgent()

    async def run_analysis(self, task: AnalysisTask) -> AnalysisResult:
        """Run complete analysis pipeline.

        Args:
            task: Analysis task with configuration

        Returns:
            Complete analysis result with insights
        """
        print(f"\n{'=' * 60}")
        print(f"Starting Analysis Pipeline for Task: {task.task_id}")
        print(f"Team: {task.team_id}")
        print(f"Goal: {task.business_goal}")
        print(f"{'=' * 60}\n")

        result = AnalysisResult(task_id=task.task_id)

        try:
            # Step 1: Data Understanding
            print("[Step 1/5] Data Understanding...")
            data_dict = await self._run_data_understanding(task.db_config, task.business_doc)
            result.data_dict = data_dict
            print(f"  - Found {len(data_dict.tables)} tables")
            print(f"  - Identified {len(data_dict.key_fields)} key fields\n")

            # Step 2: Analysis Strategy
            print("[Step 2/5] Designing Analysis Strategy...")
            strategy = await self._run_strategy_design(data_dict, task.business_goal)
            result.analysis_plan = strategy
            print(f"  - Strategy includes {len(strategy.get('metrics', []))} metrics")
            print(f"  - {len(strategy.get('steps', []))} analysis steps planned\n")

            # Step 3: Code Generation
            print("[Step 3/5] Generating Analysis Code...")
            db_config_dict = self._build_db_config_dict(task.db_config)
            code = await self._run_code_generation(data_dict, strategy, db_config_dict)
            result.generated_code = code
            print(f"  - Generated {len(code)} characters of Python code\n")

            # Step 4: Code Execution
            print("[Step 4/5] Executing Analysis Code...")
            exec_result = await self._run_code_execution(code, db_config_dict)
            result.execution_result = exec_result
            if exec_result.success:
                print(f"  - Execution completed in {exec_result.duration_ms}ms")
                print(f"  - Output keys: {list(exec_result.output.keys())}\n")
            else:
                print(f"  - Execution failed: {exec_result.error}\n")
                # Continue even if execution fails to provide partial results

            # Step 5: Insight Generation
            print("[Step 5/5] Generating Business Insights...")
            stats = exec_result.output if exec_result.success else {}
            insights = await self._run_insight_generation(data_dict, stats, task.business_goal)
            result.insights = insights
            print(f"  - Generated {len(insights)} business insights\n")

            print(f"{'=' * 60}")
            print("Analysis Pipeline Completed Successfully")
            print(f"{'=' * 60}\n")

            return result

        except Exception as e:
            print(f"\n[ERROR] Pipeline failed: {e}")
            raise

    async def _run_data_understanding(
        self, db_config: DatabaseConfig, business_doc: str
    ) -> DataDictionary:
        """Run data understanding agent."""
        return await self._data_understanding_agent.execute_with_context(
            db_config=db_config,
            business_doc=business_doc,
        )

    async def _run_strategy_design(
        self, data_dict: DataDictionary, business_goal: str
    ) -> dict[str, Any]:
        """Run analysis strategy agent."""
        input_data = AnalysisStrategyInput(
            data_dict=data_dict,
            business_goal=business_goal,
        )
        return await self._strategy_agent.execute(input_data)

    async def _run_code_generation(
        self,
        data_dict: DataDictionary,
        strategy: dict[str, Any],
        db_config: dict[str, Any],
    ) -> str:
        """Run code generation agent."""
        input_data = CodeGenerationInput(
            data_dict=data_dict,
            strategy=strategy,
            db_config=db_config,
        )
        return await self._code_gen_agent.execute(input_data)

    async def _run_code_execution(
        self, code: str, db_config: dict[str, Any]
    ) -> ExecutionResult:
        """Run code execution agent."""
        input_data = CodeExecutionInput(
            code=code,
            db_config=db_config,
        )
        return await self._code_exec_agent.execute(input_data)

    async def _run_insight_generation(
        self,
        data_dict: DataDictionary,
        stats: dict[str, Any],
        business_goal: str,
    ) -> list[Insight]:
        """Run insight generation agent."""
        input_data = InsightGenerationInput(
            data_dict=data_dict,
            stats=stats,
            business_goal=business_goal,
        )
        return await self._insight_agent.execute(input_data)

    def _build_db_config_dict(self, db_config: DatabaseConfig) -> dict[str, Any]:
        """Build db config dict for code execution."""
        return {
            "host": db_config.host,
            "port": db_config.port,
            "database": db_config.database,
            "user": db_config.user,
            "password": db_config.password,
            "schema": db_config.schema_,
            "connection_url": db_config.connection_url,
        }


async def run_full_analysis(task: AnalysisTask) -> AnalysisResult:
    """Convenience function to run full analysis pipeline."""
    orchestrator = AnalysisOrchestrator()
    return await orchestrator.run_analysis(task)
