# Insight-X

AI-powered data analysis platform that transforms raw data into actionable business insights.

## Overview

Insight-X is a multi-agent system that automates the complete data analysis workflow:

1. **Data Understanding Agent** - Analyzes database structure and generates data dictionaries
2. **Analysis Strategy Agent** - Designs optimal analysis strategies based on business goals
3. **Code Generation Agent** - Generates executable Python code for data analysis
4. **Code Execution Agent** - Runs analysis code securely in Docker sandbox
5. **Insight Generation Agent** - Extracts actionable business insights from results

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Server                         │
│                    (src/main.py)                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Orchestrator                           │
│                 (src/orchestrator.py)                       │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│    Agent 1    │   │    Agent 2    │   │    Agent 3    │
│    Data       │──▶│   Strategy    │──▶│    Code       │
│  Understanding│   │    Design     │   │  Generation   │
└───────────────┘   └───────────────┘   └───────────────┘
                                              │
        ┌─────────────────────────────────────┘
        ▼                     ▼
┌───────────────┐   ┌───────────────┐
│    Agent 4    │   │    Agent 5    │
│     Code      │──▶│   Insight     │
│   Execution   │   │  Generation   │
└───────────────┘   └───────────────┘
        │
        ▼
┌───────────────┐
│   Docker      │
│   Sandbox     │
└───────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (for sandbox execution)
- PostgreSQL database (for analysis)
- Anthropic or OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/insight-x.git
cd insight-x
```

2. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Configuration

Create a `.env` file with the following variables:

```env
# LLM Configuration
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-api-key-here
LLM_MODEL=claude-sonnet-4-20250514

# Database (for task persistence)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/insight_x

# Docker Sandbox
SANDBOX_IMAGE=python:3.11-slim
SANDBOX_MEMORY_LIMIT=2g
SANDBOX_CPU_QUOTA=100000
SANDBOX_TIMEOUT=300
```

### Running the Server

#### Development Mode

```bash
python -m uvicorn src.main:app --reload --port 8000
```

#### Using Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f insight-x-api

# Stop services
docker-compose down
```

## API Usage

### Interactive Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Endpoints

#### Health Check

```bash
curl http://localhost:8000/health
```

#### Create Analysis Task

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
    "business_doc": "E-commerce platform analyzing user behavior",
    "business_goal": "Understand why users drop off at checkout"
  }'
```

Response:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "team_id": "team-001",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "message": "Task created successfully"
}
```

#### Run Analysis

```bash
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/run
```

#### Get Results

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}/result
```

### Example Workflow

```python
import httpx
import asyncio

async def run_analysis():
    async with httpx.AsyncClient() as client:
        # 1. Create task
        response = await client.post(
            "http://localhost:8000/api/v1/tasks",
            json={
                "team_id": "team-001",
                "db_config": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "ecommerce",
                    "user": "postgres",
                    "password": "secret",
                    "schema": "public"
                },
                "business_doc": "E-commerce platform with orders, users, and products tables",
                "business_goal": "Analyze conversion funnel and identify drop-off points"
            }
        )
        task = response.json()
        task_id = task["task_id"]
        print(f"Task created: {task_id}")

        # 2. Run analysis
        response = await client.post(
            f"http://localhost:8000/api/v1/tasks/{task_id}/run"
        )
        result = response.json()
        print(f"Analysis completed with {len(result['insights'])} insights")

        # 3. Print insights
        for insight in result["insights"]:
            print(f"\n{insight['title']}")
            print(f"  {insight['description']}")

asyncio.run(run_analysis())
```

## Project Structure

```
insight-x/
├── src/
│   ├── agents/                 # AI Agents
│   │   ├── base.py            # Base agent class
│   │   ├── data_understanding.py   # Agent 1
│   │   ├── analysis_strategy.py    # Agent 2
│   │   ├── code_generation.py      # Agent 3
│   │   ├── code_execution.py       # Agent 4
│   │   └── insight_generation.py   # Agent 5
│   ├── db/
│   │   └── connector.py       # Database connector
│   ├── llm/
│   │   ├── client.py          # LLM client (Anthropic/OpenAI)
│   │   └── prompts.py         # Prompt templates
│   ├── models/
│   │   ├── task.py            # Task models
│   │   └── result.py          # Result models
│   ├── sandbox/
│   │   └── executor.py        # Docker sandbox executor
│   ├── main.py                # FastAPI application
│   ├── orchestrator.py        # Agent orchestration
│   └── config.py              # Configuration
├── tests/                     # Test suite
├── Dockerfile                 # API server image
├── Dockerfile.sandbox         # Sandbox execution image
├── docker-compose.yml         # Docker Compose config
├── requirements.txt           # Python dependencies
└── pyproject.toml             # Project configuration
```

## Security

### Sandbox Execution

All user-generated code runs in Docker containers with:

- **Network isolation**: No network access (`network_mode: none`)
- **Memory limits**: Configurable memory limit (default: 2GB)
- **CPU limits**: Configurable CPU quota (default: 1 CPU)
- **Timeout**: Configurable execution timeout (default: 5 minutes)
- **No new privileges**: Security option prevents privilege escalation
- **Drop all capabilities**: All Linux capabilities dropped
- **Read-only filesystem**: Container filesystem is read-only

### Database Security

- Only SELECT queries are allowed for aggregation
- Table names are validated with strict regex
- Connection credentials are passed securely

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/
```

### Adding New Agents

1. Create a new agent file in `src/agents/`
2. Inherit from `BaseAgent[InputType, OutputType]`
3. Implement `name`, `description`, and `execute` properties/methods
4. Add prompt templates in `src/llm/prompts.py`
5. Update `src/agents/__init__.py` to export the new agent
6. Update `src/orchestrator.py` to integrate the agent

## Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | Insight-X |
| `DEBUG` | Debug mode | false |
| `LLM_PROVIDER` | LLM provider (anthropic/openai) | anthropic |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `LLM_MODEL` | Model to use | claude-sonnet-4-20250514 |
| `DATABASE_URL` | Task database URL | sqlite+aiosqlite:///./insight_x.db |
| `SANDBOX_IMAGE` | Docker image for sandbox | python:3.11-slim |
| `SANDBOX_MEMORY_LIMIT` | Memory limit per execution | 2g |
| `SANDBOX_CPU_QUOTA` | CPU quota (100000 = 1 CPU) | 100000 |
| `SANDBOX_TIMEOUT` | Execution timeout (seconds) | 300 |

## License

MIT License
