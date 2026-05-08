"""洞察生成 Agent：将执行阶段统计与数据字典对照，产出 Insight 列表。"""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.llm.prompts import PromptTemplates
from src.models.result import DataDictionary, Insight


class InsightGenerationInput:
    """Input for Insight Generation Agent."""

    def __init__(
        self,
        data_dict: DataDictionary,
        stats: dict[str, Any],
        business_goal: str = "",
    ) -> None:
        self.data_dict = data_dict
        self.stats = stats
        self.business_goal = business_goal


class InsightGenerationAgent(BaseAgent[InsightGenerationInput, list[Insight]]):
    """流水线第五步：输入可为空 stats（上游执行失败时），仍尝试给出弱化结论。"""

    @property
    def name(self) -> str:
        return "InsightGenerationAgent"

    @property
    def description(self) -> str:
        return "Generates actionable business insights from data analysis results"

    async def execute(self, input_data: InsightGenerationInput) -> list[Insight]:
        """LLM 输出既可能是 insights 数组，也可能是包装对象，解析逻辑见 _parse_response。"""
        self._log_execution("Generating business insights...")
        try:
            system_prompt, user_prompt = PromptTemplates.format_insight_generation(
                data_dict=input_data.data_dict,
                stats=json.dumps(input_data.stats, indent=2, default=str),
            )
            response = await self._call_llm(system_prompt, user_prompt)
            insights = self._parse_response(response)
            self._log_execution(f"Generated {len(insights)} insights successfully")
            return insights
        except Exception as e:
            self._log_execution(f"Error: {e}")
            raise

    def _parse_response(self, response: str) -> list[Insight]:
        """多分支兼容：① Anthropic 风格块列表 ② markdown JSON 数组 ③ {insights:[]} 对象 ④ 兜底单条 Insight。"""
        try:
            # Handle response that might be a list with thinking/text blocks
            if response.startswith("["):
                try:
                    items = json.loads(response)
                    # 块列表：逐项寻找 text
                    if items and isinstance(items[0], dict) and "type" in items[0]:
                        for item in items:
                            if item.get("type") == "text":
                                response = item.get("text", "")
                                break
                    else:
                        # 已是 Insight JSON 数组
                        return [Insight(**item) for item in items if isinstance(item, dict)]
                except json.JSONDecodeError:
                    pass

            # Clean response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                first_newline = cleaned.find("\n")
                if first_newline != -1:
                    cleaned = cleaned[first_newline + 1 :]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3].strip()

            json_start = cleaned.find("[")
            json_end = cleaned.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = cleaned[json_start:json_end]
                data = json.loads(json_str)
                return [Insight(**item) for item in data]
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
            self._log_execution(f"Failed to parse insights: {e}")

        # Try object format with insights key
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                if "insights" in data:
                    return [Insight(**item) for item in data["insights"]]
                elif "findings" in data:
                    return [Insight(**item) for item in data["findings"]]
        except (json.JSONDecodeError, ValueError, TypeError, KeyError):
            pass

        # 解析失败：截取原始文本作为描述，避免接口完全空白
        return [
            Insight(
                title="Raw Analysis Result",
                description=response[:500],
                data_support={},
                impact="",
                confidence=0.5,
            )
        ]
