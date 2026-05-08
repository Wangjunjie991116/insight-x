"""数据理解 Agent：拉取 schema/样本，调用 LLM 产出结构化 DataDictionary。"""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.db.connector import DatabaseConnector
from src.llm.prompts import PromptTemplates
from src.models.result import DataDictionary
from src.models.task import DatabaseConfig


class DataUnderstandingAgent(BaseAgent[DatabaseConfig, DataDictionary]):
    """流水线第一步：把物理库结构与客户业务文档对齐为机器可读字典。"""

    @property
    def name(self) -> str:
        return "DataUnderstandingAgent"

    @property
    def description(self) -> str:
        return "Analyzes database structure and generates data dictionary"

    async def execute(self, input_data: DatabaseConfig) -> DataDictionary:
        """兼容仅传入 DatabaseConfig 的调用；业务文档为空字符串。"""
        return await self.execute_with_context(input_data, "")

    def _parse_response(self, response: str) -> DataDictionary:
        """清洗 markdown/JSON 边界并解析为 DataDictionary；失败时返回占位对象而非抛异常。"""
        try:
            # 处理可能是 thinking/text 块组成的 JSON 数组响应
            if response.startswith("["):
                # Try to parse as list and extract text content
                try:
                    items = json.loads(response)
                    for item in items:
                        if isinstance(item, dict) and item.get("type") == "text":
                            response = item.get("text", "")
                            break
                except json.JSONDecodeError:
                    pass

            # 去掉 ```json 围栏，提取首尾花括号之间的 JSON
            cleaned = response.strip()
            if cleaned.startswith("```"):
                # Remove opening ```json or ```
                first_newline = cleaned.find("\n")
                if first_newline != -1:
                    cleaned = cleaned[first_newline + 1 :]
                # Remove closing ```
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3].strip()

            # Try to extract JSON from response
            json_start = cleaned.find("{")
            json_end = cleaned.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = cleaned[json_start:json_end]
                data = json.loads(json_str)
                return DataDictionary(**data)
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
            self._log_execution(f"Failed to parse LLM response: {e}")

        # 解析失败：返回空壳字典，编排器仍可继续但下游质量受限
        return DataDictionary(
            tables=[],
            relations=[],
            key_fields=[],
            summary="Failed to parse LLM response",
        )

    async def execute_with_context(
        self,
        db_config: DatabaseConfig,
        business_doc: str,
    ) -> DataDictionary:
        """推荐入口：并发-safe 的数据库访问 + LLM；finally 中确保关闭连接器。"""
        self._log_execution("Connecting to database...")
        connector = DatabaseConnector(db_config)

        try:
            # 数据库侧：schema + 表枚举 + 每表抽样（最多前 10 张表控制体量）
            try:
                self._log_execution("Fetching schema information...")
                schema_info = await connector.get_schema_info()

                self._log_execution("Fetching table names...")
                table_names = await connector.get_table_names()

                self._log_execution(f"Fetching sample data for {len(table_names)} tables...")
                sample_data: dict[str, list[dict[str, Any]]] = {}
                for table in table_names[:10]:
                    sample_data[table] = await connector.get_sample_data(table, limit=50)
            except Exception as e:
                self._log_execution(f"Database operation failed: {e}")
                raise

            # LLM 侧：拼装 PromptTemplates 数据理解模板
            try:
                self._log_execution("Generating data dictionary with LLM...")
                system_prompt, user_prompt = PromptTemplates.format_data_understanding(
                    business_doc=business_doc,
                    schema_info=json.dumps(schema_info, indent=2, default=str),
                    sample_data=json.dumps(sample_data, indent=2, default=str),
                )
                response = await self._call_llm(system_prompt, user_prompt)
            except Exception as e:
                self._log_execution(f"LLM call failed: {e}")
                raise

            result = self._parse_response(response)
            self._log_execution("Data dictionary generated successfully")
            return result

        finally:
            await connector.close()
