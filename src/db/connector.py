"""异步数据库访问：元数据查询、抽样读数与受限 SQL（仅 SELECT）。"""

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.task import DatabaseConfig


class DatabaseConnector:
    """基于 SQLAlchemy asyncio 引擎的统一入口；PostgreSQL 走 asyncpg，SQLite 走 aiosqlite。"""

    def __init__(self, config: DatabaseConfig) -> None:
        """根据 DatabaseConfig 构造引擎；自动将 postgresql:// 转为异步驱动 URL。"""
        self._config = config
        self._is_sqlite = config.db_type == "sqlite"
        connection_url = config.connection_url
        if connection_url.startswith("postgresql://"):
            connection_url = connection_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        engine_kwargs: dict[str, Any] = {"echo": False}
        if not self._is_sqlite:
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 10

        self._engine = create_async_engine(connection_url, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def get_schema_info(self) -> list[dict[str, Any]]:
        """返回列级 schema（表名、列名、类型、可空性）；SQLite 用 PRAGMA 模拟同样结构。"""
        if self._is_sqlite:
            return await self._get_sqlite_schema_info()

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

        try:
            async with self._session_factory() as session:
                result = await session.execute(query, {"schema": self._config.schema_})
                return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            raise RuntimeError(f"Failed to get schema info: {e}") from e

    async def _get_sqlite_schema_info(self) -> list[dict[str, Any]]:
        """枚举用户表并对每张表执行 PRAGMA table_info，对齐 PG information_schema 字段语义。"""
        try:
            async with self._session_factory() as session:
                tables_result = await session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                )
                table_names = [row[0] for row in tables_result.fetchall()]

                columns = []
                for table_name in table_names:
                    pragma_result = await session.execute(
                        text(f"PRAGMA table_info('{table_name}')")
                    )
                    for row in pragma_result.fetchall():
                        mapping = row._mapping
                        columns.append({
                            "table_name": table_name,
                            "column_name": mapping["name"],
                            "data_type": mapping["type"],
                            "is_nullable": "NO" if mapping["notnull"] else "YES",
                        })
                return columns
        except Exception as e:
            raise RuntimeError(f"Failed to get SQLite schema info: {e}") from e

    async def get_table_names(self) -> list[str]:
        """列出当前 schema（PG）或 SQLite 文件内的业务表名。"""
        if self._is_sqlite:
            return await self._get_sqlite_table_names()

        query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema
            AND table_type = 'BASE TABLE'
        """)

        try:
            async with self._session_factory() as session:
                result = await session.execute(query, {"schema": self._config.schema_})
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            raise RuntimeError(f"Failed to get table names: {e}") from e

    async def _get_sqlite_table_names(self) -> list[str]:
        """通过 sqlite_master 过滤系统表。"""
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                )
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            raise RuntimeError(f"Failed to get SQLite table names: {e}") from e

    async def get_sample_data(self, table_name: str, limit: int = 100) -> list[dict[str, Any]]:
        """按表拉取最多 limit 行样本；表名经正则白名单校验以防标识符注入。"""
        # 仅允许字母数字下划线且不以数字开头，避免动态 SQL 中的标识符注入
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            raise ValueError(f"Invalid table name: {table_name}")

        query = text(f'SELECT * FROM "{table_name}" LIMIT {limit}')

        try:
            async with self._session_factory() as session:
                result = await session.execute(query)
                return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            raise RuntimeError(f"Failed to get sample data from table '{table_name}': {e}") from e

    async def execute_query(self, sql: str) -> list[dict[str, Any]]:
        """执行只读查询并返回行字典列表；非 SELECT 一律拒绝。"""
        # 安全：限制为 SELECT，降低 Agent 生成代码时的写入风险
        if not sql.strip().upper().startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed for security reasons")

        query = text(sql)

        try:
            async with self._session_factory() as session:
                result = await session.execute(query)
                return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            raise RuntimeError(f"Failed to execute query: {e}") from e

    async def execute_aggregation(self, sql: str) -> dict[str, Any]:
        """执行聚合类 SELECT，取首行映射为 dict（空结果返回 {}）。"""
        # 安全：限制为 SELECT，降低 Agent 生成代码时的写入风险
        if not sql.strip().upper().startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed for security reasons")

        query = text(sql)

        try:
            async with self._session_factory() as session:
                result = await session.execute(query)
                rows = result.fetchall()
                if rows:
                    return dict(rows[0]._mapping)
                return {}
        except Exception as e:
            raise RuntimeError(f"Failed to execute aggregation query: {e}") from e

    async def close(self) -> None:
        """释放连接池与底层引擎。"""
        await self._engine.dispose()
