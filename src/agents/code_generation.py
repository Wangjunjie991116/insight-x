"""Code Generation Agent - generates Python code for data analysis."""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.llm.prompts import PromptTemplates
from src.models.result import DataDictionary


class CodeGenerationInput:
    """Input for Code Generation Agent."""

    def __init__(
        self,
        data_dict: DataDictionary,
        strategy: dict[str, Any],
        db_config: dict[str, Any],
    ) -> None:
        self.data_dict = data_dict
        self.strategy = strategy
        self.db_config = db_config


class CodeGenerationAgent(BaseAgent[CodeGenerationInput, str]):
    """Agent that generates Python code for data analysis."""

    @property
    def name(self) -> str:
        return "CodeGenerationAgent"

    @property
    def description(self) -> str:
        return "Generates executable Python code for data analysis"

    async def execute(self, input_data: CodeGenerationInput) -> str:
        """Execute code generation."""
        self._log_execution("Generating analysis code...")
        try:
            system_prompt, user_prompt = PromptTemplates.format_code_generation(
                data_dict=input_data.data_dict,
                strategy=json.dumps(input_data.strategy, indent=2, default=str),
                db_config=json.dumps(input_data.db_config, indent=2, default=str),
            )
            response = await self._call_llm(system_prompt, user_prompt)
            code = self._parse_response(response)
            self._log_execution("Analysis code generated successfully")
            return code
        except Exception as e:
            self._log_execution(f"Error: {e}")
            raise

    def _parse_response(self, response: str) -> str:
        """Parse LLM response to extract Python code."""
        # Try to extract code from markdown code blocks
        code_block_start = response.find("```python")
        if code_block_start == -1:
            code_block_start = response.find("```")

        if code_block_start != -1:
            # Find the end of the code block
            code_block_end = response.find("```", code_block_start + 3)
            if code_block_end != -1:
                # Extract the code, skipping the language identifier if present
                code_start = code_block_start + 3
                if response[code_start:code_start + 6] == "python":
                    code_start += 6
                elif response[code_start:code_start + 1] == "\n":
                    code_start += 1

                code = response[code_start:code_block_end].strip()
                return code

        # If no code block found, return the entire response as code
        # This handles cases where the LLM returns raw Python code
        return response.strip()
