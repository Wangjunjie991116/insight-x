# Insight-X (智析)

AI Agent 自动化数据分析平台 - 用户只需提供数据源和业务目标，AI 自动完成全链路分析。

## 目录结构

```
insight-x/
├── src/
│   ├── main.py                    # FastAPI 入口
│   ├── orchestrator.py            # Agent 编排器
│   ├── config.py                  # 配置管理
│   ├── models/
│   │   ├── task.py                # 任务模型 (AnalysisTask, DatabaseConfig)
│   │   └── result.py              # 结果模型 (DataDictionary, Insight, Strategy)
│   ├── agents/
│   │   ├── base.py                # Agent 抽象基类
│   │   ├── data_understanding.py  # Agent 1: 数据理解
│   │   ├── analysis_strategy.py   # Agent 2: 分析策略
│   │   ├── code_generation.py     # Agent 3: 代码生成
│   │   ├── code_execution.py      # Agent 4: 代码执行
│   │   └── insight_generation.py  # Agent 5: 洞察生成
│   ├── llm/
│   │   ├── client.py              # LLM 客户端 (Anthropic/OpenAI)
│   │   └── prompts.py             # Prompt 模板库
│   ├── db/
│   │   └── connector.py           # 异步数据库连接器
│   └── sandbox/
│       └── executor.py            # Docker 沙箱执行器
├── tests/                         # 测试套件
├── pyproject.toml                 # 项目配置
├── requirements.txt               # 依赖清单
├── Dockerfile                     # API 服务镜像
├── Dockerfile.sandbox             # 沙箱执行镜像
├── docker-compose.yml             # 容器编排配置
└── .env.example                   # 环境变量模板
```

## 技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| **语言** | Python 3.11+ | 类型注解、async/await |
| **Web框架** | FastAPI | 异步 API、自动 OpenAPI 文档 |
| **Agent框架** | LangChain | LLM 应用开发框架 |
| **LLM** | Claude / GPT-4 | Anthropic 或 OpenAI API |
| **数据库** | PostgreSQL + SQLAlchemy | 异步 ORM、连接池 |
| **沙箱** | Docker | 安全隔离、资源限制 |
| **任务队列** | Redis + Celery | 异步任务处理 (可选) |
| **测试** | pytest + pytest-asyncio | 异步测试支持 |

## 工作流

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户输入                                  │
│         数据源配置 + 业务文档 + 业务目标                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Agent 编排层                                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│  │ Agent 1 │──▶│ Agent 2 │──▶│ Agent 3 │──▶│ Agent 4 │──▶│ Agent 5 │
│  │数据理解 │   │策略设计 │   │代码生成 │   │代码执行 │   │洞察生成 │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
│       ↓             ↓             ↓             ↓             ↓
│  数据字典      分析计划      Python代码     执行结果      业务洞察
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        输出层                                    │
│         分析报告 + 策略建议 + 埋点代码                           │
└─────────────────────────────────────────────────────────────────┘
```

### Agent 职责

| Agent | 输入 | 输出 | 职责 |
|-------|------|------|------|
| **Agent 1** 数据理解 | 数据库配置 | DataDictionary | 分析表结构、字段语义、关联关系 |
| **Agent 2** 分析策略 | 数据字典 + 业务目标 | AnalysisPlan | 设计分析指标、统计量、步骤 |
| **Agent 3** 代码生成 | 数据字典 + 分析策略 | Python Code | 生成可执行分析代码 |
| **Agent 4** 代码执行 | Python Code | ExecutionResult | Docker 沙箱安全执行 |
| **Agent 5** 洞察生成 | 统计结果 | List[Insight] | 提取业务洞察和建议 |

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd /Users/didi/Documents/project/private/insight-x

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
```

### 2. 配置 .env

```env
# LLM 配置
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-api-key-here
LLM_MODEL=claude-sonnet-4-20250514

# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/insight_x

# Docker 沙箱
SANDBOX_IMAGE=python:3.11-slim
SANDBOX_MEMORY_LIMIT=2g
SANDBOX_CPU_QUOTA=100000
SANDBOX_TIMEOUT=300
```

### 3. 启动服务

**开发模式：**
```bash
uvicorn src.main:app --reload --port 8000
```

**Docker 模式：**
```bash
docker-compose up -d
docker-compose logs -f insight-x-api
docker-compose down
```

### 4. 访问文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v1/tasks` | POST | 创建分析任务 |
| `/api/v1/tasks/{id}` | GET | 获取任务状态 |
| `/api/v1/tasks/{id}/run` | POST | 执行分析 |
| `/api/v1/tasks/{id}/result` | GET | 获取分析结果 |

### 创建任务

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "team-001",
    "db_config": {
      "host": "localhost",
      "port": 5432,
      "database": "mydb",
      "user": "postgres",
      "password": "secret",
      "schema": "public"
    },
    "business_doc": "电商用户行为分析",
    "business_goal": "分析转化漏斗，找出流失点"
  }'
```

### 执行分析

```bash
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/run
```

### 获取结果

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}/result
```

## 命令脚本

### 开发命令

```bash
# 运行开发服务器
uvicorn src.main:app --reload

# 运行测试
pytest tests/ -v

# 运行测试 (带覆盖率)
pytest tests/ -v --cov=src

# 类型检查
mypy src/

# 代码格式化
ruff format src/ tests/

# 代码检查
ruff check src/ tests/
```

### Docker 命令

```bash
# 构建镜像
docker build -t insight-x:latest .

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 清理数据
docker-compose down -v
```

### 数据库命令

```bash
# 创建数据库
createdb insight_x

# 运行迁移 (如有)
alembic upgrade head
```

## 安全机制

### Docker 沙箱

| 配置 | 值 | 说明 |
|------|-----|------|
| `network_mode` | none | 禁用网络访问 |
| `mem_limit` | 2g | 内存限制 2GB |
| `cpu_quota` | 100000 | CPU 限制 1 核 |
| `timeout` | 300s | 执行超时 5 分钟 |
| `read_only` | true | 只读文件系统 |
| `no_new_privileges` | true | 禁止提权 |
| `cap_drop` | ALL | 移除所有能力 |

### SQL 安全

- 仅允许 SELECT 查询
- 表名正则校验 `^[a-zA-Z_][a-zA-Z0-9_]*$`
- 参数化查询防止注入

## 配置项

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 | anthropic |
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `LLM_MODEL` | 模型名称 | claude-sonnet-4-20250514 |
| `DATABASE_URL` | 数据库 URL | sqlite+aiosqlite:///./insight_x.db |
| `SANDBOX_IMAGE` | 沙箱镜像 | python:3.11-slim |
| `SANDBOX_MEMORY_LIMIT` | 内存限制 | 2g |
| `SANDBOX_CPU_QUOTA` | CPU 配额 | 100000 |
| `SANDBOX_TIMEOUT` | 超时时间 | 300 |

## 开发指南

### 添加新 Agent

1. 创建 `src/agents/new_agent.py`，继承 `BaseAgent[InputType, OutputType]`
2. 实现 `name`、`description` 属性和 `execute()` 方法
3. 在 `src/llm/prompts.py` 添加 Prompt 模板
4. 在 `src/agents/__init__.py` 导出
5. 在 `src/orchestrator.py` 集成到工作流

### 示例 Agent

```python
from src.agents.base import BaseAgent

class MyAgent(BaseAgent[str, str]):
    @property
    def name(self) -> str:
        return "MyAgent"

    @property
    def description(self) -> str:
        return "My custom agent"

    async def execute(self, input_data: str) -> str:
        self._log_execution("Processing...")
        response = await self._call_llm("system prompt", input_data)
        return response
```

## License

MIT