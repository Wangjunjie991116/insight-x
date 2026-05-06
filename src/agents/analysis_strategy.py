"""Analysis Strategy Agent - designs analysis strategies based on goals."""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.llm.prompts import PromptTemplates
from src.models.result import DataDictionary


class AnalysisStrategyInput:
    """Input for Analysis Strategy Agent."""

    def __init__(
        self,
        data_dict: DataDictionary,
        business_goal: str,
    ) -> None:
        self.data_dict = data_dict
        self.business_goal = business_goal


class AnalysisStrategyAgent(BaseAgent[AnalysisStrategyInput, dict[str, Any]]):
    """Agent that designs analysis strategies."""

    @property
    def name(self) -> str:
        return "AnalysisStrategyAgent"

    @property
    def description(self) -> str:
        return "Designs data analysis strategies based on data dictionary and business goals"

    async def execute(self, input_data: AnalysisStrategyInput) -> dict[str, Any]:
        """Execute strategy design."""
        self._log_execution("Designing analysis strategy...")
        try:
            system_prompt, user_prompt = PromptTemplates.format_analysis_strategy(
                data_dict=input_data.data_dict,
                business_goal=input_data.business_goal,
            )
            response = await self._call_llm(system_prompt, user_prompt)
            strategy = self._parse_response(response)
            self._log_execution("Analysis strategy designed successfully")
            return strategy
        except Exception as e:
            self._log_execution(f"Error: {e}")
            raise

    def _parse_response(self, response: str) -> dict[str, Any]:
        """Parse LLM response to strategy dict."""
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError, TypeError, KeyError):
            pass
        return {
            "metrics": [],
            "statistics": [],
            "comparisons": [],
            "steps": [],
            "raw_response": response,
        }
