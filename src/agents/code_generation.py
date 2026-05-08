"""代码生成 Agent：根据数据字典、策略与 DB 连接信息生成可执行 Python 源码。"""

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
    """流水线第三步：输出单一字符串源码，供沙箱装载运行。"""

    @property
    def name(self) -> str:
        return "CodeGenerationAgent"

    @property
    def description(self) -> str:
        return "Generates executable Python code for data analysis"

    async def execute(self, input_data: CodeGenerationInput) -> str:
        """提示词内嵌 JSON 化的策略与连接配置，模型返回 markdown 代码块或裸代码。"""
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
        """优先截取 ```python 围栏；否则退回全文，兼容模型直接输出源码。"""
        if response.startswith("["):
            try:
                items = json.loads(response)
                for item in items:
                    if isinstance(item, dict) and item.get("type") == "text":
                        response = item.get("text", "")
                        break
            except json.JSONDecodeError:
                pass

        # 尝试从 markdown 围栏抽取 python 代码块
        code_block_start = response.find("```python")
        if code_block_start == -1:
            code_block_start = response.find("```")

        if code_block_start != -1:
            # 定位闭合围栏并跳过可选的语言标记
            code_block_end = response.find("```", code_block_start + 3)
            if code_block_end != -1:
                # code_start 跳过 ``` 后的 "python" 字样
                code_start = code_block_start + 3
                if response[code_start:code_start + 6] == "python":
                    code_start += 6

                code = response[code_start:code_block_end].strip()
                return code

        # 无围栏时视为裸 Python，避免生成步骤反复失败
        return response.strip()
