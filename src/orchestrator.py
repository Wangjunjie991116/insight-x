"""分析流水线编排器：按固定顺序串联各 Agent，聚合为单次 AnalysisResult。"""

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
from src.models.result import AnalysisResult, DataDictionary, ExecutionResult, Insight
from src.models.task import AnalysisTask, DatabaseConfig


class AnalysisOrchestrator:
    """封装五步流水线（数据理解→策略→代码生成→执行→洞察），对外暴露单一入口。"""

    def __init__(self) -> None:
        """初始化五个 Agent 实例；不负责数据库或 Docker，由各 Agent 内部按需连接。"""
        self._data_understanding_agent = DataUnderstandingAgent()
        self._strategy_agent = AnalysisStrategyAgent()
        self._code_gen_agent = CodeGenerationAgent()
        self._code_exec_agent = CodeExecutionAgent()
        self._insight_agent = InsightGenerationAgent()

    async def run_analysis(self, task: AnalysisTask) -> AnalysisResult:
        """执行完整分析流水线。

        顺序依赖：数据字典为空则后续步骤缺少语义上下文；代码执行失败时仍会生成洞察（stats 为空 dict）。
        """
        print(f"\n{'=' * 60}")
        print(f"Starting Analysis Pipeline for Task: {task.task_id}")
        print(f"Team: {task.team_id}")
        print(f"Goal: {task.business_goal}")
        print(f"{'=' * 60}\n")

        result = AnalysisResult(task_id=task.task_id)

        try:
            # 步骤 1：连接库表，抽样并由 LLM 产出结构化数据字典
            print("[Step 1/5] Data Understanding...")
            data_dict = await self._run_data_understanding(task.db_config, task.business_doc)
            result.data_dict = data_dict
            print(f"  - Found {len(data_dict.tables)} tables")
            print(f"  - Identified {len(data_dict.key_fields)} key fields\n")

            # 步骤 2：依据业务目标与数据字典设计指标与分析步骤（JSON 形态）
            print("[Step 2/5] Designing Analysis Strategy...")
            strategy = await self._run_strategy_design(data_dict, task.business_goal)
            result.analysis_plan = strategy
            print(f"  - Strategy includes {len(strategy.get('metrics', []))} metrics")
            print(f"  - {len(strategy.get('steps', []))} analysis steps planned\n")

            # 步骤 3：结合连接信息与策略生成可在沙箱中运行的 Python 分析脚本
            print("[Step 3/5] Generating Analysis Code...")
            db_config_dict = self._build_db_config_dict(task.db_config)
            code = await self._run_code_generation(data_dict, strategy, db_config_dict)
            result.generated_code = code
            print(f"  - Generated {len(code)} characters of Python code\n")

            # 步骤 4：沙箱执行生成的代码，产出统计字典（失败时不中止流水线）
            print("[Step 4/5] Executing Analysis Code...")
            exec_result = await self._run_code_execution(code, db_config_dict)
            result.execution_result = exec_result
            if exec_result.success:
                print(f"  - Execution completed in {exec_result.duration_ms}ms")
                print(f"  - Output keys: {list(exec_result.output.keys())}\n")
            else:
                print(f"  - Execution failed: {exec_result.error}\n")
                # 执行失败仍继续：洞察步骤可使用空 stats，便于排查或产出弱化结论

            # 步骤 5：将执行产出与业务目标对照，生成可行动的洞察列表
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
        """调用数据理解 Agent（含库表元数据与抽样）。"""
        return await self._data_understanding_agent.execute_with_context(
            db_config=db_config,
            business_doc=business_doc,
        )

    async def _run_strategy_design(
        self, data_dict: DataDictionary, business_goal: str
    ) -> dict[str, Any]:
        """调用分析策略 Agent，返回 metrics/steps 等结构化计划。"""
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
        """调用代码生成 Agent，产出待执行的 Python 源码字符串。"""
        input_data = CodeGenerationInput(
            data_dict=data_dict,
            strategy=strategy,
            db_config=db_config,
        )
        return await self._code_gen_agent.execute(input_data)

    async def _run_code_execution(
        self, code: str, db_config: dict[str, Any]
    ) -> ExecutionResult:
        """在沙箱中执行生成代码，封装成功/失败与输出字典。"""
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
        """基于数据字典与执行统计调用洞察 Agent。"""
        input_data = InsightGenerationInput(
            data_dict=data_dict,
            stats=stats,
            business_goal=business_goal,
        )
        return await self._insight_agent.execute(input_data)

    def _build_db_config_dict(self, db_config: DatabaseConfig) -> dict[str, Any]:
        """将 Pydantic 配置转为可 JSON 序列化 dict，供生成代码与沙箱注入。"""
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
    """便捷入口：每次新建编排器实例并执行完整流水线（适合 HTTP 单次请求模型）。"""
    orchestrator = AnalysisOrchestrator()
    return await orchestrator.run_analysis(task)
