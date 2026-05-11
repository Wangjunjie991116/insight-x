"""Agent 6-2：埋点策略建议 Agent。

基于当前代码、业务文档、业务目标与已有埋点数据，从 AI 视角提出需要补充采集的数据策略，
输出可指导埋点实现的结构化报告。
"""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.llm.prompts import PromptTemplates
from src.models.code_analysis import CodeRepository, TrackingStrategyReport
from src.models.result import Insight


class TrackingStrategyInput:
    """Agent 6-2 的输入。"""

    def __init__(
        self,
        insights: list[Insight],
        business_goal: str,
        business_doc: str,
        repo: CodeRepository,
        existing_events: list[str] | None = None,
    ) -> None:
        self.insights = insights
        self.business_goal = business_goal
        self.business_doc = business_doc
        self.repo = repo
        self.existing_events = existing_events or []


class TrackingStrategyAgent(BaseAgent[TrackingStrategyInput, TrackingStrategyReport]):
    """流水线第 6-2 步：识别数据缺口并设计埋点策略。"""

    @property
    def name(self) -> str:
        return "TrackingStrategyAgent"

    @property
    def description(self) -> str:
        return "Designs tracking event strategies to fill data gaps and validate business hypotheses"

    async def execute(self, input_data: TrackingStrategyInput) -> TrackingStrategyReport:
        """分析洞察与代码，输出需要新增的埋点事件设计。"""
        self._log_execution("Designing tracking strategy...")

        repo_map = self._build_repo_map(input_data.repo)
        insights_json = json.dumps(
            [i.model_dump() for i in input_data.insights],
            indent=2,
            ensure_ascii=False,
        )

        try:
            system_prompt, user_prompt = PromptTemplates.format_tracking_strategy(
                insights=insights_json,
                business_goal=input_data.business_goal,
                business_doc=input_data.business_doc,
                repo_map=repo_map,
                existing_events=json.dumps(input_data.existing_events, ensure_ascii=False),
                tech_stack=", ".join(input_data.repo.tech_stack),
            )
            response = await self._call_llm(system_prompt, user_prompt)
            report = self._parse_response(response)
            self._log_execution(
                f"Designed {len(report.new_events)} tracking events, "
                f"priority: {report.priority_summary}"
            )
            return report
        except Exception as e:
            self._log_execution(f"Error: {e}")
            raise

    def _build_repo_map(self, repo: CodeRepository) -> str:
        """提取与埋点相关的文件摘要（组件、页面、事件处理函数）。"""
        lines: list[str] = []
        for f in repo.list_source_files()[:50]:
            # 只保留前 15 行，帮助 LLM 定位事件触发位置
            summary = "\n".join(f.content.splitlines()[:15])
            lines.append(f"--- {f.path} ---")
            lines.append(summary)
            lines.append("")
        return "\n".join(lines)

    def _parse_response(self, response: str) -> TrackingStrategyReport:
        """兼容多种 LLM 输出格式解析为 TrackingStrategyReport。"""
        try:
            if response.startswith("["):
                try:
                    items = json.loads(response)
                    if items and isinstance(items[0], dict) and "type" in items[0]:
                        for item in items:
                            if item.get("type") == "text":
                                response = item.get("text", "")
                                break
                except json.JSONDecodeError:
                    pass

            cleaned = response.strip()
            if cleaned.startswith("```"):
                first_newline = cleaned.find("\n")
                if first_newline != -1:
                    cleaned = cleaned[first_newline + 1 :]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3].strip()

            json_start = cleaned.find("{")
            json_end = cleaned.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(cleaned[json_start:json_end])
                return TrackingStrategyReport(**data)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            self._log_execution(f"Failed to parse tracking report: {e}")

        return TrackingStrategyReport(
            new_events=[],
            gap_analysis="Failed to parse LLM response",
            priority_summary=[],
        )
