# Insight-X 项目指南

## 项目概述

Insight-X (洞察) 是一个 AI Agent 自动化数据分析平台。用户只需提供数据源配置和业务目标，AI 自动完成从数据理解到洞察生成的全链路分析。

## 核心架构

```
用户输入 → Agent 编排层 → 执行层 → 输出层
              │
              ├── Agent 1: 数据理解 (DataUnderstandingAgent)
              ├── Agent 2: 分析策略 (AnalysisStrategyAgent)
              ├── Agent 3: 代码生成 (CodeGenerationAgent)
              ├── Agent 4: 代码执行 (CodeExecutionAgent)
              └── Agent 5: 洞察生成 (InsightGenerationAgent)
```

## 开发规范

### 代码风格

- Python 3.11+ 类型注解
- 使用 `async/await` 异步模式
- Pydantic v2 模型定义
- 遵循 ruff 格式化规则

### Agent 开发

所有 Agent 必须继承 `BaseAgent[InputType, OutputType]`：

```python
from src.agents.base import BaseAgent

class MyAgent(BaseAgent[InputType, OutputType]):
    @property
    def name(self) -> str:
        return "MyAgent"

    @property
    def description(self) -> str:
        return "Agent description"

    async def execute(self, input_data: InputType) -> OutputType:
        # 1. 记录开始
        self._log_execution("Starting...")

        # 2. 调用 LLM
        response = await self._call_llm(system_prompt, user_prompt)

        # 3. 解析结果
        result = self._parse_response(response)

        return result
```

### 错误处理

```python
try:
    result = await some_operation()
except Exception as e:
    self._log_execution(f"Error: {e}")
    raise
```

### 资源管理

使用 `try/finally` 确保资源释放：

```python
connector = DatabaseConnector(config)
try:
    result = await connector.execute()
finally:
    await connector.close()
```

## 测试规范

### 测试文件结构

```
tests/
├── conftest.py           # 共享 fixtures
├── test_models/          # 模型测试
├── test_agents/          # Agent 测试
├── test_llm/             # LLM 客户端测试
└── test_sandbox/         # 沙箱测试
```

### 测试命名

- `test_<功能>_<场景>()` 例如 `test_agent_execute_success()`
- 异步测试使用 `@pytest.mark.asyncio`

### 运行测试

```bash
pytest tests/ -v                    # 运行所有测试
pytest tests/test_agents/ -v        # 运行指定目录
pytest -k "data_understanding" -v   # 运行匹配测试
```

## API 规范

### 端点设计

- RESTful 风格
- 版本前缀 `/api/v1/`
- Pydantic 模型验证

### 响应格式

成功：
```json
{
  "task_id": "xxx",
  "status": "completed",
  "result": {...}
}
```

失败：
```json
{
  "detail": "Error message"
}
```

## 安全规范

### Docker 沙箱

- 禁用网络 (`network_mode: none`)
- 内存限制 2GB
- CPU 限制 1 核
- 只读文件系统
- 禁止提权

### SQL 安全

- 仅允许 SELECT 查询
- 表名正则校验
- 参数化查询

### 敏感信息

- API Key 通过环境变量注入
- 数据库密码不在日志中输出
- `.env` 文件不提交到版本控制

## 常用命令

```bash
# 开发
uvicorn src.main:app --reload

# 测试
pytest tests/ -v --cov=src

# 代码检查
ruff check src/ tests/
mypy src/

# Docker
docker-compose up -d
docker-compose logs -f
```

## 配置说明

| 变量 | 必填 | 说明 |
|------|------|------|
| `LLM_PROVIDER` | 是 | anthropic 或 openai |
| `ANTHROPIC_API_KEY` | 是* | Anthropic API Key |
| `OPENAI_API_KEY` | 是* | OpenAI API Key |
| `DATABASE_URL` | 否 | 默认 SQLite |
| `SANDBOX_*` | 否 | 沙箱配置 |

*根据 LLM_PROVIDER 选择

## 项目约束

### 不要修改

- `src/agents/base.py` - Agent 基类稳定
- `src/models/task.py` - 任务模型已标准化
- Docker 安全配置 - 已加固

### 扩展点

- 添加新 Agent: `src/agents/`
- 添加 Prompt 模板: `src/llm/prompts.py`
- 添加 API 端点: `src/main.py`
- 添加测试: `tests/`

## 已知问题

1. 使用 `print()` 日志，需替换为 `logging`
2. 内存存储任务，重启丢失数据
3. 沙箱只读文件系统无法写输出，需 tmpfs 挂载

## 相关文档

- 设计文档: `docs/superpowers/specs/2026-05-06-ai-agent-data-analysis-platform-design.md`
- 实施计划: `docs/superpowers/plans/2026-05-07-insight-x-mvp.md`
- OpenAPI 规范: `docs/openapi.yaml`