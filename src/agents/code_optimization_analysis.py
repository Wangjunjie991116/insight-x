"""Agent 6-1：代码优化分析 Agent。

基于 Agent 5 产出的洞察报告，自动识别技术栈，定位源代码中可优化业务指标的具体位置。
"""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.llm.prompts import PromptTemplates
from src.models.code_analysis import CodeChangeSuggestion, CodeRepository
from src.models.result import Insight


class CodeOptimizationAnalysisInput:
    """Agent 6-1 的输入。"""

    def __init__(
        self,
        insights: list[Insight],
        business_goal: str,
        repo: CodeRepository,
    ) -> None:
        self.insights = insights
        self.business_goal = business_goal
        self.repo = repo


class CodeOptimizationAnalysisAgent(BaseAgent[CodeOptimizationAnalysisInput, list[CodeChangeSuggestion]]):
    """流水线第 6-1 步：数据洞察 → 代码层优化建议。"""

    @property
    def name(self) -> str:
        return "CodeOptimizationAnalysisAgent"

    @property
    def description(self) -> str:
        return "Analyzes source code based on data insights and suggests code-level optimizations"

    async def execute(self, input_data: CodeOptimizationAnalysisInput) -> list[CodeChangeSuggestion]:
        """两阶段分析：先技术栈与架构地图，再精细化定位优化点。"""
        self._log_execution("Starting code optimization analysis...")

        # 阶段 1：让 LLM 建立代码地图（控制 Token，只传文件路径和关键片段）
        repo_map = self._build_repo_map(input_data.repo)
        tech_stack = input_data.repo.tech_stack

        self._log_execution(f"Detected tech stack: {tech_stack}")
        self._log_execution(f"Repository has {len(input_data.repo.files)} files")

        # 阶段 2：基于洞察逐条分析
        all_suggestions: list[CodeChangeSuggestion] = []
        insights_json = json.dumps(
            [i.model_dump() for i in input_data.insights],
            indent=2,
            ensure_ascii=False,
        )

        try:
            system_prompt, user_prompt = PromptTemplates.format_code_optimization_analysis(
                insights=insights_json,
                business_goal=input_data.business_goal,
                repo_map=repo_map,
                tech_stack=", ".join(tech_stack),
            )
            response = await self._call_llm(system_prompt, user_prompt)
            suggestions = self._parse_response(response)
            self._log_execution(f"Generated {len(suggestions)} code optimization suggestions")
            return suggestions
        except Exception as e:
            self._log_execution(f"Error: {e}")
            raise

    def _build_repo_map(self, repo: CodeRepository) -> str:
        """构建轻量级仓库地图，只包含文件路径和每个文件的前 10 行摘要。"""
        lines: list[str] = []
        lines.append(f"Tech Stack: {', '.join(repo.tech_stack) or 'Unknown'}")
        lines.append(f"Total Files: {len(repo.files)}")
        lines.append("")

        for f in repo.list_source_files()[:50]:  # 限制 50 个文件
            summary = "\\n".join(f.content.splitlines()[:10])
            lines.append(f"--- {f.path} ---")
            lines.append(summary)
            lines.append("")

        return "\\n".join(lines)

    def _parse_response(self, response: str) -> list[CodeChangeSuggestion]:
        """解析 LLM 返回的 JSON 数组为结构化建议列表。"""
        try:
            # 处理 Anthropic 风格的块列表
            if response.startswith("["):
                try:
                    items = json.loads(response)
                    if items and isinstance(items[0], dict) and "type" in items[0]:
                        for item in items:
                            if item.get("type") == "text":
                                response = item.get("text", "")
                                break
                    else:
                        return [CodeChangeSuggestion(**item) for item in items if isinstance(item, dict)]
                except json.JSONDecodeError:
                    pass

            cleaned = response.strip()
            if cleaned.startswith("```"):
                first_newline = cleaned.find("\\n")
                if first_newline != -1:
                    cleaned = cleaned[first_newline + 1 :]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3].strip()

            json_start = cleaned.find("[")
            json_end = cleaned.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(cleaned[json_start:json_end])
                return [CodeChangeSuggestion(**item) for item in data if isinstance(item, dict)]
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            self._log_execution(f"Failed to parse suggestions: {e}")

        return []
