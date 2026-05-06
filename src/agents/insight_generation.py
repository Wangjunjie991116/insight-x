"""Insight Generation Agent - generates business insights from data."""

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
    """Agent that generates business insights from statistical results."""

    @property
    def name(self) -> str:
        return "InsightGenerationAgent"

    @property
    def description(self) -> str:
        return "Generates actionable business insights from data analysis results"

    async def execute(self, input_data: InsightGenerationInput) -> list[Insight]:
        """Execute insight generation."""
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
        """Parse LLM response to list of insights."""
        try:
            json_start = response.find("[")
            json_end = response.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
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

        # Return a single insight with raw response
        return [
            Insight(
                title="Raw Analysis Result",
                description=response[:500],
                data_support={},
                impact="",
                confidence=0.5,
            )
        ]
