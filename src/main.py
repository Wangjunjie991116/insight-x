"""Insight-X HTTP API：任务创建、触发五步分析与结果查询（任务与结果当前为内存存储）。"""

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


# MVP：进程内字典存放任务与分析结果，重启即丢失；生产环境需替换为持久化存储
_task_store: dict[str, AnalysisTask] = {}
_result_store: dict[str, AnalysisResult] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """应用生命周期：启动时打印关键配置，关闭时清理钩子占位。"""
    # 启动阶段：便于本地确认 LLM 提供方与模型是否读到环境变量
    settings = get_settings()
    print(f"Starting {settings.app_name}...")
    print(f"Debug mode: {settings.debug}")
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"LLM Model: {settings.llm_model}")
    yield
    # 关闭阶段：此处可扩展为关闭连接池等
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

    host: str = Field(default="", description="Database host", examples=["localhost"])
    port: int = Field(default=5432, description="Database port", examples=[5432])
    database: str = Field(..., description="Database name or path for SQLite", examples=["mydb"])
    user: str = Field(default="", description="Database user", examples=["postgres"])
    password: str = Field(default="", description="Database password", examples=["secret"])
    schema_: str = Field(
        default="public",
        alias="schema",
        description="Database schema",
        examples=["public"],
    )
    db_type: str = Field(
        default="postgresql",
        description="Database type: postgresql or sqlite",
        examples=["sqlite"],
    )


class CreateTaskRequest(BaseModel):
    """Request to create a new analysis task."""

    team_id: str = Field(..., description="Team identifier", examples=["team-001"])
    db_config: DatabaseConfigRequest = Field(..., description="Database configuration")
    business_doc: str = Field(
        ...,
        description="Business context documentation",
        examples=["E-commerce platform analyzing user conversion funnel"],
    )
    business_goal: str = Field(
        ...,
        description="Analysis goal",
        examples=["Understand why users drop off at checkout and suggest improvements"],
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
    """负载均衡/探活：不访问数据库与 LLM。"""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )


@app.post("/api/v1/tasks", response_model=TaskResponse, tags=["Tasks"])
async def create_task(request: CreateTaskRequest) -> TaskResponse:
    """创建分析任务：写入内存仓库，状态为 PENDING，直至调用 run。"""
    task_id = str(uuid.uuid4())

    # 将请求体中的数据库字段映射为领域模型 DatabaseConfig
    db_config = DatabaseConfig(
        host=request.db_config.host,
        port=request.db_config.port,
        database=request.db_config.database,
        user=request.db_config.user,
        password=request.db_config.password,
        schema=request.db_config.schema_,
        db_type=request.db_config.db_type,
    )

    # 组装任务并写入内存索引
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
    """按 task_id 查询当前状态与时间戳。"""
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
    """触发完整五步流水线；并发防护：同一任务 RUNNING 时返回 400。

    成功则将 AnalysisResult 落入 `_result_store` 并将任务标为 COMPLETED；
    异常则标 FAILED，并在响应体中带 error 文本。
    """
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Task is already running")

    # 标记运行中，防止重复触发长时间流水线
    task.mark_running()
    _task_store[task_id] = task

    try:
        result = await run_full_analysis(task)

        # 持久化（内存）分析产物并翻转任务状态
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
    """读取已完成任务的分析产物；PENDING/RUNNING 分别返回 400。"""
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
    """列出内存中的任务摘要，可按 team_id 过滤并限制条数。"""
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
    """网关首页提示文档与健康检查路径。"""
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
