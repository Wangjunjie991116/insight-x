"""Database connector for querying data."""

from typing import Any

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.models.task import DatabaseConfig


class DatabaseConnector:
    """Async database connector."""

    def __init__(self, config: DatabaseConfig) -> None:
        """Initialize database connector."""
        self._config = config
        # Convert postgresql:// to postgresql+asyncpg:// for async support
        connection_url = config.connection_url
        if connection_url.startswith("postgresql://"):
            connection_url = connection_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        self._engine = create_async_engine(
            connection_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def get_schema_info(self) -> list[dict[str, Any]]:
        """Get database schema information."""
        query = text("""
            SELECT
                table_name,
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = :schema
            ORDER BY table_name, ordinal_position
        """)

        async with self._session_factory() as session:
            result = await session.execute(query, {"schema": self._config.schema_})
            return [dict(row._mapping) for row in result.fetchall()]

    async def get_table_names(self) -> list[str]:
        """Get list of table names."""
        query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema
            AND table_type = 'BASE TABLE'
        """)

        async with self._session_factory() as session:
            result = await session.execute(query, {"schema": self._config.schema_})
            return [row[0] for row in result.fetchall()]

    async def get_sample_data(self, table_name: str, limit: int = 100) -> list[dict[str, Any]]:
        """Get sample data from a table."""
        # Use parameterized query safely
        if not table_name.replace("_", "").isalnum():
            raise ValueError(f"Invalid table name: {table_name}")

        query = text(f'SELECT * FROM "{table_name}" LIMIT {limit}')

        async with self._session_factory() as session:
            result = await session.execute(query)
            return [dict(row._mapping) for row in result.fetchall()]

    async def execute_query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a SQL query and return results."""
        query = text(sql)

        async with self._session_factory() as session:
            result = await session.execute(query)
            return [dict(row._mapping) for row in result.fetchall()]

    async def execute_aggregation(self, sql: str) -> dict[str, Any]:
        """Execute aggregation query for statistics."""
        query = text(sql)

        async with self._session_factory() as session:
            result = await session.execute(query)
            rows = result.fetchall()
            if rows:
                return dict(rows[0]._mapping)
            return {}

    async def close(self) -> None:
        """Close database connection."""
        await self._engine.dispose()
