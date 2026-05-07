# Insight-X (洞察)

AI Agent 自动化数据分析平台 - 用户只需提供数据源和业务目标，AI 自动完成全链路分析。

## 概述

Insight-X 是一个**完全自动化**的 AI Agent 数据分析平台，核心理念是**最小化人工干预**：凡是能通过 AI 完成的，就不人工手动编码。

### 核心能力

- **数据理解**：自动分析数据库结构，生成数据字典
- **策略设计**：根据业务目标自动设计分析策略
- **代码生成**：自动生成可执行的 Python 分析代码
- **安全执行**：在 Docker 沙箱中安全执行代码
- **洞察生成**：从数据中提取业务洞察
- **策略输出**（未来）：生成可执行的转化策略
- **埋点实现**（未来）：自动设计和实现埋点代码

### 适用场景

- 多业务团队数据分析（5+ 团队，数据完全隔离）
- 埋点数据自动分析
- 转化策略自动生成
- 埋点自动设计与实现

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
│   │   ├── insight_generation.py  # Agent 5: 洞察生成
│   │   ├── strategy_design.py     # Agent 6: 策略设计（未来）
│   │   └── tracking_impl.py       # Agent 7: 埋点实现（未来）
│   ├── llm/
│   │   ├── client.py              # LLM 客户端 (Anthropic/OpenAI)
│   │   └── prompts.py             # Prompt 模板库
│   ├── db/
│   │   └── connector.py           # 异步数据库连接器
│   └── sandbox/
│       └── executor.py            # Docker 沙箱执行器
├── tests/                         # 测试套件
├── docs/
│   └── openapi.yaml               # OpenAPI 规范
├── pyproject.toml                 # 项目配置
├── requirements.txt               # 依赖清单
├── Dockerfile                     # API 服务镜像
├── Dockerfile.sandbox             # 沙箱执行镜像
├── docker-compose.yml             # 容器编排配置
├── CLAUDE.md                      # 开发指南
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
| **任务队列** | Redis + Celery | 异步任务处理（可选） |
| **测试** | pytest + pytest-asyncio | 异步测试支持 |

## 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户输入层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ 数据源配置   │  │ 业务文档     │  │ 业务目标     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    AI Agent 编排层                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Agent 1 │ │ Agent 2 │ │ Agent 3 │ │ Agent 4 │ │ Agent 5 │  │
│  │数据理解 │ │策略设计 │ │代码生成 │ │执行分析 │ │洞察生成 │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
│  ┌─────────┐ ┌─────────┐                                      │
│  │ Agent 6 │ │ Agent 7 │  （未来实现）                        │
│  │策略输出 │ │埋点实现 │                                      │
│  └─────────┘ └─────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      执行层                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Docker沙箱   │  │ 数据库       │  │ 代码仓库     │         │
│  │ (代码执行)   │  │ (数据存储)   │  │ (埋点代码)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      输出层                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ 分析报告     │  │ 策略建议     │  │ 埋点代码     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 弹性云部署架构

```
┌─────────────────────────────────────────────────────────┐
│                   负载均衡器                             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              API 网关容器 (FastAPI)                      │
│  - 请求路由                                             │
│  - 认证授权                                             │
│  - 限流控制                                             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌───────────────┬───────────────┬─────────────────────────┐
│ Agent Worker  │ Agent Worker  │ Agent Worker           │
│ (容器实例 1)  │ (容器实例 2)  │ (容器实例 N)           │
└───────────────┴───────────────┴─────────────────────────┘
        ↓               ↓               ↓
┌─────────────────────────────────────────────────────────┐
│                   共享服务层                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Redis    │  │ PostgreSQL│  │ 对象存储 │             │
│  │ (队列)   │  │ (元数据)  │  │ (结果)   │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
```

### 多团队数据隔离

应用级隔离策略，每个团队拥有独立的：
- 数据库连接配置
- 工作空间目录
- 执行上下文

## 工作流

### Agent 流程

```
用户输入 (数据源 + 业务文档 + 业务目标)
    ↓
[Agent 1] 数据理解 Agent
    → 分析表结构、字段语义、关联关系
    → 输出：数据字典
    ↓
[Agent 2] 分析策略 Agent
    → 设计分析指标、统计量、步骤
    → 输出：分析计划
    ↓
[Agent 3] 代码生成 Agent
    → 生成可执行 Python 代码
    → 输出：Python 代码
    ↓
[Agent 4] 代码执行 Agent
    → Docker 沙箱安全执行
    → 输出：执行结果
    ↓
[Agent 5] 洞察生成 Agent
    → 提取业务洞察和建议
    → 输出：业务洞察列表
    ↓
[Agent 6] 策略设计 Agent（未来）
    → 生成可执行的转化策略
    → 输出：策略配置
    ↓
[Agent 7] 埋点实现 Agent（未来）
    → 设计和实现埋点代码
    → 输出：埋点代码 PR
    ↓
输出结果
```

### Agent 职责

| Agent | 输入 | 输出 | 职责 | 状态 |
|-------|------|------|------|------|
| Agent 1 数据理解 | 数据库配置 | DataDictionary | 分析表结构、字段语义、关联关系 | ✅ 已实现 |
| Agent 2 分析策略 | 数据字典 + 业务目标 | AnalysisPlan | 设计分析指标、统计量、步骤 | ✅ 已实现 |
| Agent 3 代码生成 | 数据字典 + 分析策略 | Python Code | 生成可执行分析代码 | ✅ 已实现 |
| Agent 4 代码执行 | Python Code | ExecutionResult | Docker 沙箱安全执行 | ✅ 已实现 |
| Agent 5 洞察生成 | 统计结果 | List[Insight] | 提取业务洞察和建议 | ✅ 已实现 |
| Agent 6 策略设计 | 业务洞察 + 业务目标 | Strategy | 生成可执行的转化策略 | 🔜 未来 |
| Agent 7 埋点实现 | 策略配置 + 代码仓库 | PR | 设计和实现埋点代码 | 🔜 未来 |

## 快速开始

### 1. 环境准备

```bash
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

## 风险评估

### 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM API 不稳定 | 高 | 多供应商备份 + 本地缓存 |
| 代码执行安全漏洞 | 高 | Docker 沙箱隔离 + 资源限制 |
| Token 消耗超预算 | 中 | 采样策略 + 结果缓存 |
| 数据隐私泄露 | 高 | 应用级隔离 + 权限控制 |

### 业务风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| AI 分析结果不准确 | 中 | 人工审核关键决策 |
| 埋点代码质量问题 | 中 | 代码审查 + 测试覆盖 |
| 策略实施效果不佳 | 低 | A/B 测试验证 |

## 增强优化

### 扩展性设计

**插件化 Agent**：支持注册自定义 Agent

```python
registry.register(AgentPlugin(
    name="CustomAnalysisAgent",
    input_schema=CustomInputSchema,
    output_schema=CustomOutputSchema,
    executor=custom_analysis_logic
))
```

**自定义分析模板**：业务方可定义分析流程

```python
custom_template = {
    "name": "UserRetentionAnalysis",
    "agents": [
        {"type": "DataUnderstanding", "config": {...}},
        {"type": "CustomAnalysis", "config": {...}},
        {"type": "InsightGeneration", "config": {...}}
    ],
    "workflow": "sequential"  # or "parallel", "conditional"
}
```

### 错误自愈

Agent 执行失败时自动重试，并根据错误信息自我修正：

```python
def execute_with_retry(agent_func, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = agent_func()
            validate_result(result)
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            # Agent 自我修正
            agent_func = create_correction_agent(agent_func, error_context)
```

### 监控指标

- **执行时长**：每个 Agent 的执行时间
- **Token 消耗**：LLM API 调用的 token 数
- **成功率**：Agent 执行成功率
- **重试次数**：错误重试次数

## 实施路线图

| 阶段 | 时间 | 内容 | 状态 |
|------|------|------|------|
| **Phase 1: MVP** | 2周 | Agent 1-5、单团队支持、基础分析能力 | ✅ 已完成 |
| **Phase 2: 平台化** | 3周 | 多团队隔离、Agent 6-7、完整工作流 | 🔜 待开始 |
| **Phase 3: 增强优化** | 2周 | 错误自愈机制、性能优化、监控告警 | 🔜 待开始 |
| **Phase 4: 智能化** | 持续 | 模型微调、策略推荐优化、自动化程度提升 | 🔜 待开始 |

## 成功标准

### 功能指标

| 指标 | 目标 | 当前状态 |
|------|------|---------|
| 支持业务团队数 | ≥ 5 | 🔜 待验证 |
| 数据隔离 | 完全隔离 | ✅ 已实现 |
| 分析准确率 | > 80% | 🔜 待验证 |
| 策略采纳率 | > 60% | 🔜 待验证 |

### 性能指标

| 指标 | 目标 | 当前状态 |
|------|------|---------|
| 分析任务完成时间 | < 30 分钟 | 🔜 待验证 |
| 系统可用性 | > 99% | 🔜 待验证 |
| Token 成本优化 | 40%+ | 🔜 待验证 |

### 用户体验

| 指标 | 目标 | 当前状态 |
|------|------|---------|
| 用户输入 | 仅需 3 个输入 | ✅ 已实现 |
| 流程自动化 | 全流程自动化 | ✅ 已实现 |
| 结果可用性 | 可直接使用 | ✅ 已实现 |

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

## 相关文档

- [开发指南](CLAUDE.md) - 项目开发规范
- [OpenAPI 规范](docs/openapi.yaml) - API 接口定义
- [设计文档](docs/superpowers/specs/2026-05-06-ai-agent-data-analysis-platform-design.md) - 架构设计详情
- [实施计划](docs/superpowers/plans/2026-05-07-insight-x-mvp.md) - MVP 实施步骤

## License

MIT