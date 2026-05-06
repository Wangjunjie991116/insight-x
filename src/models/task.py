"""Task model definitions."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    host: str = Field(..., description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(..., description="Database name")
    user: str = Field(..., description="Database user")
    password: str = Field(..., description="Database password")
    schema_: str = Field(default="public", alias="schema", description="Database schema")

    @property
    def connection_url(self) -> str:
        """Build PostgreSQL connection URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class AnalysisTask(BaseModel):
    """Analysis task model."""

    model_config = ConfigDict(validate_assignment=True)

    task_id: str = Field(..., description="Unique task identifier")
    team_id: str = Field(..., description="Team identifier for data isolation")
    db_config: DatabaseConfig = Field(..., description="Database configuration")
    business_doc: str = Field(..., description="Business context documentation")
    business_goal: str = Field(..., description="Analysis goal")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Update timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def mark_running(self) -> None:
        """Mark task as running."""
        self.status = TaskStatus.RUNNING
        self.updated_at = datetime.now(timezone.utc)

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)
