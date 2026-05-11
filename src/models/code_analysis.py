"""代码分析与代码修改相关的模型定义。"""

from typing import Any

from pydantic import BaseModel, Field


class FileNode(BaseModel):
    """代码仓库中的文件节点。"""

    path: str = Field(..., description="相对于仓库根目录的文件路径")
    content: str = Field(default="", description="文件内容")
    is_directory: bool = Field(default=False, description="是否为目录")


class CodeRepository(BaseModel):
    """代码仓库快照，由 Git 服务拉取后填充。"""

    repo_url: str = Field(..., description="Git 仓库地址")
    branch: str = Field(default="main", description="分支名")
    commit_hash: str = Field(default="", description="当前 commit hash")
    files: list[FileNode] = Field(default_factory=list, description="文件列表")
    tech_stack: list[str] = Field(default_factory=list, description="识别出的技术栈")

    def get_file(self, path: str) -> FileNode | None:
        """按路径查找文件。"""
        for f in self.files:
            if f.path == path and not f.is_directory:
                return f
        return None

    def list_source_files(self) -> list[FileNode]:
        """过滤出常见的源代码文件。"""
        exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".vue", ".java", ".go", ".rb", ".php"}
        return [f for f in self.files if not f.is_directory and any(f.path.endswith(e) for e in exts)]


class CodeChangeSuggestion(BaseModel):
    """Agent 6-1 产出的单条代码优化建议。"""

    file_path: str = Field(..., description="目标文件路径")
    line_range: tuple[int, int] = Field(default=(0, 0), description="建议修改的行号范围")
    current_code: str = Field(default="", description="现有代码片段")
    suggested_code: str = Field(default="", description="建议修改后的代码")
    rationale: str = Field(..., description="修改理由，需关联对应洞察")
    target_metric: str = Field(default="", description="期望优化的业务指标")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="信心分")


class TrackingEventDesign(BaseModel):
    """Agent 6-2 产出的单条埋点事件设计。"""

    event_name: str = Field(..., description="埋点事件名")
    trigger_condition: str = Field(..., description="触发条件描述")
    code_location: str = Field(default="", description="建议植入的代码位置")
    implementation_hint: str = Field(default="", description="实现提示")
    business_hypothesis: str = Field(..., description="待验证的业务假设")
    related_insight: str = Field(default="", description="关联的洞察标题")
    priority: str = Field(default="medium", description="优先级: high/medium/low")


class TrackingStrategyReport(BaseModel):
    """Agent 6-2 的完整输出。"""

    new_events: list[TrackingEventDesign] = Field(default_factory=list, description="建议新增的埋点")
    gap_analysis: str = Field(default="", description="现有埋点缺口分析")
    priority_summary: list[str] = Field(default_factory=list, description="按 ROI 排序的事件名列表")


class FileChange(BaseModel):
    """Agent 7 产出的单文件修改。"""

    file_path: str = Field(..., description="文件路径")
    diff: str = Field(..., description="unified diff 格式的补丁内容")
    change_type: str = Field(default="modify", description="modify | add | delete")


class CodeImplementationOutput(BaseModel):
    """Agent 7 的完整输出。"""

    changes: list[FileChange] = Field(default_factory=list, description="文件变更列表")
    pr_description: str = Field(default="", description="可用于 PR 的描述文本")
    test_suggestions: list[str] = Field(default_factory=list, description="建议补充的测试")


class PatchDownload(BaseModel):
    """供 API 层返回的 patch 下载信息。"""

    patch_content: str = Field(..., description="完整 patch 文件内容")
    filename: str = Field(default="insight-x-changes.patch", description="下载文件名")
