"""FastAPI application entry point for Insight-X."""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import get_settings
from src.models.result import AnalysisResult
from src.models.task import AnalysisTask, DatabaseConfig, TaskStatus
from src.orchestrator import run_full_analysis


# In-memory task storage (replace with database in production)
_task_store: dict[str, AnalysisTask] = {}
_result_store: dict[str, AnalysisResult] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name}...")
    print(f"Debug mode: {settings.debug}")
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"LLM Model: {settings.llm_model}")
    yield
    # Shutdown
    print("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Insight-X",
    description="""
Insight-X is an AI-powered data analysis platform that transforms raw data into actionable business insights.

## Features

- **Data Understanding**: Automatically analyzes database structure and generates data dictionaries
- **Analysis Strategy**: Designs optimal analysis strategies based on business goals
- **Code Generation**: Generates executable Python code for data analysis
- **Safe Execution**: Runs analysis code in Docker sandbox for security
- **Insight Generation**: Extracts actionable business insights from analysis results

## Workflow

1. Create a task with database configuration and business goals
2. Run analysis to execute the full pipeline
3. Retrieve results with insights and recommendations
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class DatabaseConfigRequest(BaseModel):
    """Database configuration request."""

    host: str = Field(default="", description="Database host", example="localhost")
    port: int = Field(default=5432, description="Database port", example=5432)
    database: str = Field(..., description="Database name or path for SQLite", example="mydb")
    user: str = Field(default="", description="Database user", example="postgres")
    password: str = Field(default="", description="Database password", example="secret")
    schema_: str = Field(
        default="public",
        alias="schema",
        description="Database schema",
        example="public",
    )
    db_type: str = Field(
        default="postgresql",
        description="Database type: postgresql or sqlite",
        example="sqlite",
    )


class CreateTaskRequest(BaseModel):
    """Request to create a new analysis task."""

    team_id: str = Field(..., description="Team identifier", example="team-001")
    db_config: DatabaseConfigRequest = Field(..., description="Database configuration")
    business_doc: str = Field(
        ...,
        description="Business context documentation",
        example="E-commerce platform analyzing user conversion funnel",
    )
    business_goal: str = Field(
        ...,
        description="Analysis goal",
        example="Understand why users drop off at checkout and suggest improvements",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class TaskResponse(BaseModel):
    """Task response."""

    task_id: str
    team_id: str
    status: TaskStatus
    created_at: datetime
    message: str = "Task created successfully"


class TaskStatusResponse(BaseModel):
    """Task status response."""

    task_id: str
    team_id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    business_goal: str


class AnalysisResultResponse(BaseModel):
    """Full analysis result response."""

    task_id: str
    status: TaskStatus
    data_dict: dict[str, Any] | None = None
    analysis_plan: dict[str, Any] | None = None
    generated_code: str | None = None
    execution_result: dict[str, Any] | None = None
    insights: list[dict[str, Any]] = []
    error: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "0.1.0"
    timestamp: datetime


# API Endpoints
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )


@app.post("/api/v1/tasks", response_model=TaskResponse, tags=["Tasks"])
async def create_task(request: CreateTaskRequest) -> TaskResponse:
    """Create a new analysis task.

    Creates a task with database configuration and analysis goals.
    The task will be in PENDING status until analysis is run.
    """
    task_id = str(uuid.uuid4())

    # Create database config
    db_config = DatabaseConfig(
        host=request.db_config.host,
        port=request.db_config.port,
        database=request.db_config.database,
        user=request.db_config.user,
        password=request.db_config.password,
        schema_=request.db_config.schema_,
        db_type=request.db_config.db_type,
    )

    # Create task
    task = AnalysisTask(
        task_id=task_id,
        team_id=request.team_id,
        db_config=db_config,
        business_doc=request.business_doc,
        business_goal=request.business_goal,
        metadata=request.metadata,
    )

    _task_store[task_id] = task

    return TaskResponse(
        task_id=task_id,
        team_id=request.team_id,
        status=TaskStatus.PENDING,
        created_at=task.created_at,
    )


@app.get("/api/v1/tasks/{task_id}", response_model=TaskStatusResponse, tags=["Tasks"])
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get task status by ID."""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=task.task_id,
        team_id=task.team_id,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        business_goal=task.business_goal,
    )


@app.post("/api/v1/tasks/{task_id}/run", response_model=AnalysisResultResponse, tags=["Analysis"])
async def run_analysis(task_id: str) -> AnalysisResultResponse:
    """Run analysis for a task.

    Executes the full analysis pipeline:
    1. Data Understanding - Analyzes database structure
    2. Strategy Design - Creates analysis strategy
    3. Code Generation - Generates Python analysis code
    4. Code Execution - Runs code in sandbox
    5. Insight Generation - Extracts business insights
    """
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Task is already running")

    # Mark task as running
    task.mark_running()
    _task_store[task_id] = task

    try:
        # Run full analysis
        result = await run_full_analysis(task)

        # Store result and mark completed
        _result_store[task_id] = result
        task.mark_completed()
        _task_store[task_id] = task

        return AnalysisResultResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            data_dict=result.data_dict.model_dump() if result.data_dict else None,
            analysis_plan=result.analysis_plan,
            generated_code=result.generated_code,
            execution_result=result.execution_result.model_dump() if result.execution_result else None,
            insights=[insight.model_dump() for insight in result.insights],
        )

    except Exception as e:
        task.mark_failed()
        _task_store[task_id] = task

        return AnalysisResultResponse(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=str(e),
        )


@app.get("/api/v1/tasks/{task_id}/result", response_model=AnalysisResultResponse, tags=["Analysis"])
async def get_analysis_result(task_id: str) -> AnalysisResultResponse:
    """Get analysis result for a completed task."""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == TaskStatus.PENDING:
        raise HTTPException(status_code=400, detail="Task has not been run yet")

    if task.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Task is still running")

    result = _result_store.get(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    return AnalysisResultResponse(
        task_id=task_id,
        status=task.status,
        data_dict=result.data_dict.model_dump() if result.data_dict else None,
        analysis_plan=result.analysis_plan,
        generated_code=result.generated_code,
        execution_result=result.execution_result.model_dump() if result.execution_result else None,
        insights=[insight.model_dump() for insight in result.insights],
        error=None if task.status == TaskStatus.COMPLETED else "Analysis failed",
    )


@app.get("/api/v1/tasks", response_model=list[TaskStatusResponse], tags=["Tasks"])
async def list_tasks(team_id: str | None = None, limit: int = 100) -> list[TaskStatusResponse]:
    """List all tasks, optionally filtered by team."""
    tasks = list(_task_store.values())

    if team_id:
        tasks = [t for t in tasks if t.team_id == team_id]

    tasks = tasks[:limit]

    return [
        TaskStatusResponse(
            task_id=t.task_id,
            team_id=t.team_id,
            status=t.status,
            created_at=t.created_at,
            updated_at=t.updated_at,
            business_goal=t.business_goal,
        )
        for t in tasks
    ]


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "Insight-X API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
