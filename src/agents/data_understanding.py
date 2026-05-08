"""Data Understanding Agent - understands data structure and business semantics."""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.db.connector import DatabaseConnector
from src.llm.prompts import PromptTemplates
from src.models.result import DataDictionary
from src.models.task import DatabaseConfig


class DataUnderstandingAgent(BaseAgent[DatabaseConfig, DataDictionary]):
    """Agent that understands data structure and generates data dictionary."""

    @property
    def name(self) -> str:
        return "DataUnderstandingAgent"

    @property
    def description(self) -> str:
        return "Analyzes database structure and generates data dictionary"

    async def execute(self, input_data: DatabaseConfig) -> DataDictionary:
        """Execute data understanding.

        Args:
            input_data: Database configuration

        Returns:
            DataDictionary with table info and relations
        """
        return await self.execute_with_context(input_data, "")

    def _parse_response(self, response: str) -> DataDictionary:
        """Parse LLM response to DataDictionary."""
        try:
            # Handle response that might be a list with thinking/text blocks
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

            # Clean response - remove markdown code blocks if present
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

        # Return empty dictionary if parsing fails
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
        """Execute with business context.

        Args:
            db_config: Database configuration
            business_doc: Business documentation

        Returns:
            DataDictionary with enriched business context
        """
        self._log_execution("Connecting to database...")
        connector = DatabaseConnector(db_config)

        try:
            # Database operations
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

            # LLM operation
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
