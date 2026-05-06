"""Data Understanding Agent - understands data structure and business semantics."""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.db.connector import DatabaseConnector
from src.llm.client import LLMClient
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
        self._log_execution("Connecting to database...")
        connector = DatabaseConnector(input_data)

        try:
            # Step 1: Get schema information
            self._log_execution("Fetching schema information...")
            schema_info = await connector.get_schema_info()

            # Step 2: Get table names
            table_names = await connector.get_table_names()

            # Step 3: Get sample data for each table (limited)
            self._log_execution(f"Fetching sample data for {len(table_names)} tables...")
            sample_data: dict[str, list[dict[str, Any]]] = {}
            for table in table_names[:10]:  # Limit to first 10 tables
                sample_data[table] = await connector.get_sample_data(table, limit=50)

            # Step 4: Call LLM to generate data dictionary
            self._log_execution("Generating data dictionary with LLM...")
            system_prompt, user_prompt = PromptTemplates.format_data_understanding(
                business_doc="",  # Will be passed separately
                schema_info=json.dumps(schema_info, indent=2, default=str),
                sample_data=json.dumps(sample_data, indent=2, default=str),
            )

            response = await self._call_llm(system_prompt, user_prompt)

            # Step 5: Parse response to DataDictionary
            data_dict = self._parse_response(response)

            self._log_execution("Data dictionary generated successfully")
            return data_dict

        finally:
            await connector.close()

    def _parse_response(self, response: str) -> DataDictionary:
        """Parse LLM response to DataDictionary."""
        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                return DataDictionary(**data)
        except (json.JSONDecodeError, ValueError):
            pass

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
            schema_info = await connector.get_schema_info()
            table_names = await connector.get_table_names()

            sample_data: dict[str, list[dict[str, Any]]] = {}
            for table in table_names[:10]:
                sample_data[table] = await connector.get_sample_data(table, limit=50)

            system_prompt, user_prompt = PromptTemplates.format_data_understanding(
                business_doc=business_doc,
                schema_info=json.dumps(schema_info, indent=2, default=str),
                sample_data=json.dumps(sample_data, indent=2, default=str),
            )

            response = await self._call_llm(system_prompt, user_prompt)
            return self._parse_response(response)

        finally:
            await connector.close()
