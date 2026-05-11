"""Insight-X HTTP API：任务创建、触发五步分析与结果查询（任务与结果当前为内存存储）。"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import get_settings
from src.models.code_analysis import CodeImplementationOutput
from src.models.result import AnalysisResult, Insight
from src.models.task import AnalysisTask, DatabaseConfig, TaskStatus
from src.orchestrator import (
    CodeOptimizationOrchestrator,
    run_full_analysis,
)


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


# ─── 代码优化与埋点相关请求/响应模型 ───────────────────────────

class RunCodeOptimizationRequest(BaseModel):
    """运行代码优化分析请求。"""

    repo_url: str = Field(..., description="Git 仓库地址")
    branch: str = Field(default="main", description="分支名")


class CodeOptimizationResponse(BaseModel):
    """代码优化分析响应。"""

    task_id: str
    suggestions: list[dict[str, Any]] = []
    suggestion_count: int = 0
    status: str = "completed"


class RunTrackingStrategyRequest(BaseModel):
    """运行埋点策略分析请求。"""

    repo_url: str = Field(..., description="Git 仓库地址")
    branch: str = Field(default="main", description="分支名")
    existing_events: list[str] = Field(default_factory=list, description="已有埋点事件列表")


class TrackingStrategyResponse(BaseModel):
    """埋点策略分析响应。"""

    task_id: str
    new_events: list[dict[str, Any]] = []
    gap_analysis: str = ""
    priority_summary: list[str] = []
    status: str = "completed"


class RunCodeImplementationRequest(BaseModel):
    """运行代码实现请求。"""

    repo_url: str = Field(..., description="Git 仓库地址")
    branch: str = Field(default="main", description="分支名")
    use_code_optimization: bool = Field(default=True, description="是否使用已生成的代码优化建议")
    use_tracking_strategy: bool = Field(default=True, description="是否使用已生成的埋点策略")


class CodeImplementationResponse(BaseModel):
    """代码实现响应。"""

    task_id: str
    changed_files: list[str] = []
    pr_description: str = ""
    test_suggestions: list[str] = []
    status: str = "completed"


# ─── 扩展内存存储（代码优化、埋点策略、代码实现） ─────────────────

_code_opt_store: dict[str, list[dict[str, Any]]] = {}
_tracking_store: dict[str, dict[str, Any]] = {}
_code_impl_store: dict[str, dict[str, Any]] = {}


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


# ─── Agent 6-1 / 6-2 / 7 端点 ───────────────────────────────────

@app.post(
    "/api/v1/tasks/{task_id}/code-optimization",
    response_model=CodeOptimizationResponse,
    tags=["Code Optimization"],
)
async def run_code_optimization(
    task_id: str, request: RunCodeOptimizationRequest
) -> CodeOptimizationResponse:
    """独立运行 Agent 6-1：基于任务洞察分析代码优化点。"""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = _result_store.get(task_id)
    if not result or not result.insights:
        raise HTTPException(status_code=400, detail="Task has no insights yet. Run analysis first.")

    orchestrator = CodeOptimizationOrchestrator()
    suggestions = await orchestrator.run_code_optimization(
        insights=result.insights,
        business_goal=task.business_goal,
        repo_url=request.repo_url,
        branch=request.branch,
    )

    suggestions_dict = [s.model_dump() for s in suggestions]
    _code_opt_store[task_id] = suggestions_dict

    return CodeOptimizationResponse(
        task_id=task_id,
        suggestions=suggestions_dict,
        suggestion_count=len(suggestions_dict),
    )


@app.post(
    "/api/v1/tasks/{task_id}/tracking-strategy",
    response_model=TrackingStrategyResponse,
    tags=["Tracking Strategy"],
)
async def run_tracking_strategy(
    task_id: str, request: RunTrackingStrategyRequest
) -> TrackingStrategyResponse:
    """独立运行 Agent 6-2：基于任务洞察设计埋点策略。"""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = _result_store.get(task_id)
    if not result or not result.insights:
        raise HTTPException(status_code=400, detail="Task has no insights yet. Run analysis first.")

    orchestrator = CodeOptimizationOrchestrator()
    report = await orchestrator.run_tracking_strategy(
        insights=result.insights,
        business_goal=task.business_goal,
        business_doc=task.business_doc,
        repo_url=request.repo_url,
        branch=request.branch,
        existing_events=request.existing_events,
    )

    report_dict = report.model_dump()
    _tracking_store[task_id] = report_dict

    return TrackingStrategyResponse(
        task_id=task_id,
        new_events=[e.model_dump() for e in report.new_events],
        gap_analysis=report.gap_analysis,
        priority_summary=report.priority_summary,
    )


@app.post(
    "/api/v1/tasks/{task_id}/code-implementation",
    response_model=CodeImplementationResponse,
    tags=["Code Implementation"],
)
async def run_code_implementation(
    task_id: str, request: RunCodeImplementationRequest
) -> CodeImplementationResponse:
    """运行 Agent 7：将代码优化建议和/或埋点策略转换为 patch。"""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    code_suggestions = None
    tracking_report = None

    if request.use_code_optimization:
        opts = _code_opt_store.get(task_id)
        if opts:
            from src.models.code_analysis import CodeChangeSuggestion
            code_suggestions = [CodeChangeSuggestion(**o) for o in opts]

    if request.use_tracking_strategy:
        trk = _tracking_store.get(task_id)
        if trk:
            from src.models.code_analysis import TrackingStrategyReport
            tracking_report = TrackingStrategyReport(**trk)

    if not code_suggestions and not tracking_report:
        raise HTTPException(
            status_code=400,
            detail="No code optimization or tracking strategy found for this task.",
        )

    orchestrator = CodeOptimizationOrchestrator()
    impl = await orchestrator.run_code_implementation(
        repo_url=request.repo_url,
        code_suggestions=code_suggestions,
        tracking_report=tracking_report,
        branch=request.branch,
    )

    impl_dict = impl.model_dump()
    _code_impl_store[task_id] = impl_dict

    return CodeImplementationResponse(
        task_id=task_id,
        changed_files=[c.file_path for c in impl.changes],
        pr_description=impl.pr_description,
        test_suggestions=impl.test_suggestions,
    )


@app.get(
    "/api/v1/tasks/{task_id}/patch",
    tags=["Code Implementation"],
)
async def download_patch(task_id: str) -> dict[str, Any]:
    """下载 Agent 7 生成的 patch 文件内容。"""
    impl = _code_impl_store.get(task_id)
    if not impl:
        raise HTTPException(status_code=404, detail="No implementation result found")

    changes = impl.get("changes", [])
    patch_parts = []
    for change in changes:
        patch_parts.append(change.get("diff", ""))

    full_patch = "\n".join(patch_parts)

    return {
        "task_id": task_id,
        "filename": f"{task_id}.patch",
        "patch": full_patch,
    }


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
