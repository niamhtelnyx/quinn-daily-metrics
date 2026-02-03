# AGENTS.md - AI Coding Assistant Guide

This document provides context for AI coding assistants working on the codebase.

## Architecture Overview

This is a **LangGraph-based agentic service** built with FastAPI. The service hosts AI agents that can reason, use tools via MCP (Model Context Protocol), and participate in A2A (Agent-to-Agent) networks.

### Tech Stack

- **Runtime**: Python 3.13
- **Web Framework**: FastAPI with Uvicorn
- **Agent Framework**: LangGraph (from LangChain)
- **LLM Access**: LiteLLM proxy
- **Tool Protocol**: MCP (Model Context Protocol)
- **Database**: PostgreSQL with SQLAlchemy + Alembic
- **Observability**: OpenTelemetry, Prometheus, Bugsnag

## Project Structure

```
my_agentic_serviceservice_order_specialist/
├── platform/                    # AI Platform infrastructure (extensible, mind template updates)
│   ├── __init__.py              # Exports key platform components
│   ├── settings.py              # Pydantic settings
│   ├── constants.py             # Shared constants
│   │
│   ├── agent/                   # Agent infrastructure
│   │   ├── protocol.py          # Agent protocol definition
│   │   ├── config.py            # Configuration dataclasses
│   │   ├── langgraph.py         # LangGraph integration
│   │   ├── mcp.py               # MCP client
│   │   ├── a2a.py               # A2A protocol adapter
│   │   ├── messages.py          # Message types
│   │   ├── metrics.py           # Agent/tool metrics
│   │   └── registration.py      # Agent registry client
│   │
│   ├── server/                  # HTTP layer
│   │   ├── app.py               # FastAPI app factory
│   │   ├── health.py            # Health check logic
│   │   ├── routes/              # Platform HTTP routes
│   │   │   ├── base.py          # Health, metrics endpoints
│   │   │   ├── a2a.py           # A2A protocol endpoints
│   │   │   └── conversations.py # Conversation history endpoints
│   │   ├── dependencies/        # FastAPI dependency injection
│   │   │   ├── settings.py      # Settings dependency
│   │   │   ├── db.py            # Database dependencies
│   │   │   └── agents.py        # Agent dependencies
│   │   └── middlewares/         # HTTP middlewares
│   │       └── correlation.py   # Correlation ID middleware
│   │
│   ├── database/                # Persistence
│   │   ├── engine.py            # Database engine factory
│   │   ├── setup.py             # DB lifecycle (startup/shutdown)
│   │   ├── tables.py            # SQLAlchemy models
│   │   └── repositories/        # Data access layer
│   │       └── conversations.py # Conversation queries
│   │
│   └── observability/           # Monitoring
│       ├── metrics.py           # Prometheus metrics
│       ├── errors.py            # Bugsnag error reporting
│       └── logging.py           # Structured logging setup
│
├── agents/                      # YOUR CODE GOES HERE
│   ├── README.md                # Guide for creating agents
│   └── knowledge/               # Example agent implementation
│       ├── agent.py             # Agent builder class
│       ├── routes.py            # Agent's HTTP endpoints
│       ├── state.py             # LangGraph state definition
│       ├── prompt.py            # System prompt
│       ├── card.py              # A2A capabilities card
│       ├── a2a_setup.py         # A2A registration helper
│       ├── nodes/               # Graph nodes
│       │   ├── base.py          # Node protocol
│       │   ├── reasoner.py      # LLM reasoning node
│       │   └── tools.py         # Tool execution node
│       └── tools/               # Agent-specific tools
│           └── inspect_artifact.py  # Artifact inspection tool
│
├── __init__.py                  # Exports FastAPI app
└── __main__.py                  # Entry point
```

## Key Concepts

### Platform vs Agents

| Folder | Maintained By | Your Squad Can | Template Updates |
|--------|---------------|----------------|------------------|
| `platform/` | AI Platform | Extend (add tables, repos, business logic) | May need merge resolution |
| `agents/` | Your Squad | Full ownership | No conflicts |

**Note:** `platform/` is not read-only. You can add database tables, repositories, and business logic for your tools/use cases. Just be mindful that `make update-template` may touch the same files, requiring conflict resolution.

### Agent Builder Pattern

Agents are constructed via builder classes:

```python
# Location: my_agentic_serviceservice_order_specialist/agents/knowledge/agent.py
class KnowledgeAgentBuilder:
    def __init__(self, agent_config, llm_config, mcp_configs, checkpointer, identity):
        # mcp_configs is a list of MCPConfig to support multiple MCP servers
        ...

    async def build(self) -> LangGraphAgent:
        # 1. Create LLM client (ChatLiteLLM)
        # 2. Fetch tools from all MCP servers concurrently
        # 3. Add agent-specific tools (e.g., inspect_artifact)
        # 4. Create graph nodes (ReasonerNode, ToolNodeFactory)
        # 5. Build StateGraph with edges and compile with checkpointer
        # 6. Return LangGraphAgent wrapper with identity

    @classmethod
    def default_builder(cls, llm_base_url, llm_api_key, checkpointer, identity=None):
        # Factory method with sensible defaults
        # Sets up LlmConfig, MCPConfig list, AgentConfig, and default AgentIdentity
```

### LangGraph State

Agent state is defined as a TypedDict:

```python
# Location: my_agentic_serviceservice_order_specialist/agents/knowledge/state.py
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    reasoning_steps: int
    thread_id: str
    agent_slug: str                         # Identifier for the agent type
    input_tokens_by_model: dict[str, int]   # Cumulative input tokens by model
    output_tokens_by_model: dict[str, int]  # Cumulative output tokens by model
```

### Graph Nodes

Each node returns **updates** (not full state). LangGraph merges them:

```python
# Location: my_agentic_serviceservice_order_specialist/agents/knowledge/nodes/base.py
@runtime_checkable
class Node(Protocol):
    """Nodes are callable objects that transform AgentState."""
    async def __call__(self, state: AgentState) -> AgentState:
        ...

# Location: my_agentic_serviceservice_order_specialist/agents/knowledge/nodes/reasoner.py
class ReasonerNode(Node):
    async def __call__(self, state: AgentState) -> dict:
        # Returns partial state updates - LangGraph merges them
        return {
            "messages": [result],
            "reasoning_steps": steps + 1,
            "input_tokens_by_model": input_by_model,
            "output_tokens_by_model": output_by_model,
        }
```

### Token Tracking

The agent automatically tracks input/output tokens by model. The `ReasonerNode` extracts token counts from the LLM response and accumulates them in state. This data is available in the final `ExecutionResult.metadata`:

```python
result = await agent.run(message, thread_id)
print(result.metadata)  # {"input_tokens_by_model": {...}, "output_tokens_by_model": {...}}
```

### Artifact Pattern

Large tool outputs are automatically hidden to prevent context overflow. The `ToolNodeFactory` wraps tool execution and replaces outputs exceeding `artifact_threshold` (default: 5000 chars) with a summary + artifact ID. The agent can use `inspect_artifact` to query the hidden data.

Configuration via `AgentConfig`:
- `artifact_threshold`: Hide outputs larger than this (set to `None` to disable)
- `always_visible_tools`: Set of tool names that are never hidden

## Common Tasks

### Adding a New Agent - Complete Checklist

#### Step 1: Create Agent Directory Structure
```bash
mkdir -p my_agentic_serviceservice_order_specialist/agents/your_agent/nodes
mkdir -p my_agentic_serviceservice_order_specialist/agents/your_agent/tools
touch my_agentic_serviceservice_order_specialist/agents/your_agent/__init__.py
touch my_agentic_serviceservice_order_specialist/agents/your_agent/nodes/__init__.py
touch my_agentic_serviceservice_order_specialist/agents/your_agent/tools/__init__.py
```

#### Step 2: Create Core Files (copy from `knowledge/` as template)

| File | Purpose |
|------|---------|
| `state.py` | Define your agent's `TypedDict` state |
| `prompt.py` | `build_system_prompt()` function for agent personality |
| `agent.py` | `YourAgentBuilder` class with `build()` and `default_builder()` |
| `routes.py` | FastAPI router with `/invoke` and `/stream` endpoints |
| `card.py` | A2A `AgentCard` builder for capability discovery |
| `a2a_setup.py` | `build_and_mount_your_agent()` factory function |
| `nodes/base.py` | Node protocol (can reuse from knowledge) |
| `nodes/reasoner.py` | LLM reasoning node |
| `nodes/tools.py` | Tool execution node with artifact handling |

#### Step 3: Implement Agent Identity
In your `agent.py`, define a unique identity:
```python
default_identity = AgentIdentity(
    name="Your Agent Name",
    description="What your agent does",
    slug="your-agent",           # Used in URL routes
    squad=SQUAD_NAME,            # Your team identifier
    origin=SERVICE_NAME,         # Service name constant
    audience=Audience.INTERNAL,  # CUSTOMER, INTERNAL, or PUBLIC
)
```

#### Step 4: Register HTTP Routes
In `platform/server/app.py`:
```python
from my_agentic_serviceservice_order_specialist.agents.your_agent.routes import your_agent_router
# ... in create_app():
app.include_router(your_agent_router)
```

#### Step 5: Register A2A Routes
In `platform/server/routes/a2a.py`:
```python
from my_agentic_serviceservice_order_specialist.agents.your_agent.a2a_setup import build_and_mount_your_agent

# In add_a2a_routes_to_app():
agent_registrations.append(
    await build_and_mount_your_agent(app, task_store)
)
```

#### Step 6: Test Your Agent
```bash
make check  # Run linters, typecheckers, formatters, and tests
make dev         # Start server and test manually
```

### A2A Integration Details

The A2A (Agent-to-Agent) protocol enables agent discovery and invocation by other agents.

**Key Components:**
- `card.py`: Builds `AgentCard` describing capabilities, skills, and endpoints
- `a2a_setup.py`: Factory function that builds agent and mounts A2A routes

**Generated Endpoints:**
- `GET /a2a/{slug}/.well-known/agent-card.json` - Capability card
- `POST /a2a/{slug}/rpc` - A2A RPC endpoint for invocation

**Registration Flow:**
1. Agent builds and mounts during app startup (`add_a2a_routes_to_app`)
2. If `AGENT_REGISTRY__URL` is configured, card is sent to external registry
3. Other agents discover via registry or direct card fetch

### Adding a New Tool

**Option A: MCP Tool** (preferred for shared tools)
- Add to the MCP server, agent discovers automatically via `MCPConfig`

**Option B: Local Tool** (agent-specific)
```python
# In agent.py build() method:
all_tools = await self._fetch_tools(self.mcp_configs)
all_tools.append(your_custom_tool)  # Add your StructuredTool
llm_with_tools = llm.bind_tools(all_tools)
```

### Configuration Classes

All configuration is via frozen dataclasses in `platform/agent/config.py`:

```python
@dataclass(frozen=True)
class LlmConfig:
    model: str           # e.g., "litellm_proxy/anthropic/claude-sonnet-4-5"
    api_key: str | None
    base_url: str | None
    temperature: float = 0.7

@dataclass(frozen=True)
class MCPConfig:
    server_url: str              # MCP server endpoint
    tool_prefix: str | None      # Prefix for tool names (collision avoidance)
    headers: dict | None         # Optional HTTP headers
    timeout: float = 60.0
    sse_read_timeout: float = 300.0
    read_timeout: float = 120.0

@dataclass(frozen=True)
class AgentConfig:
    max_reasoning_steps: int     # Max iterations before forcing completion
    always_visible_tools: set[str]  # Tools never hidden by artifact pattern
    recursion_limit: int         # LangGraph recursion limit
    artifact_threshold: int = 5000  # Hide outputs larger than this
    max_context_tokens: int = 150000  # Trim messages if exceeded

class Audience(StrEnum):
    CUSTOMER = "customer"   # Customer-facing agents
    INTERNAL = "internal"   # Internal tools
    PUBLIC = "public"       # Public API agents

@dataclass(frozen=True)
class AgentIdentity:
    name: str           # Human-readable display name
    description: str    # Brief description of capabilities
    slug: str           # URL-safe identifier (used in routes)
    squad: str          # Team identifier
    origin: str         # Service name
    audience: Audience = Audience.INTERNAL
```

### Modifying Agent Behavior

- **Change reasoning**: Edit `nodes/reasoner.py`
- **Change persona**: Edit `prompt.py`
- **Change limits**: Edit `AgentConfig` in builder's `default_builder()`

### Database Changes

1. Modify models in `platform/database/tables.py`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Apply: `alembic upgrade head`

## Testing

### Running Tests

```bash
make check    # Run all tests with coverage
```

Tests run in parallel via pytest-xdist. Coverage threshold is 70%.

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures (mock_mcp_client, mock_llm)
├── unit/                    # Pure logic, no I/O
│   ├── test_settings.py
│   └── platform/agent/
├── integration/             # Component interactions with mocks
│   ├── conftest.py          # Integration fixtures (mock_agent, test_client)
│   └── test_*.py
└── e2e/                     # Multi-layer flows
    └── test_*.py
```

### Test Classification Criteria

| Type | Criteria | What to Mock | Examples |
|------|----------|--------------|----------|
| **Unit** | Pure functions, no I/O, no external mocks. Tests isolated logic, validators, data transformations. | Nothing | Config validation, dataclass behavior, string builders |
| **Integration** | Component interactions with mocked external dependencies. Uses TestClient, mock MCP servers, mock DBs. | System boundaries (DB, HTTP, MCP, LLM) | HTTP endpoints with mock agent, MCP client with mock server |
| **E2E** | Full request-response cycles through multiple layers. Minimal mocking, testing real component wiring. | Only external services (LLM APIs) | Agent invoke/stream flows, error propagation across layers |

### Writing Tests

#### For Humans

1. **Choose the right level**: Unit for pure logic, integration for component interactions, e2e for flows
2. **Use existing fixtures**: Check `conftest.py` files before creating new mocks
3. **One assertion focus**: Each test should verify one behavior
4. **Descriptive names**: `test_invoke_returns_execution_result` not `test_invoke`

#### For Code Agents

When writing tests:

1. **Determine test type** by what you're testing:
   - Pure function with no dependencies → `tests/unit/`
   - Component with mocked dependencies → `tests/integration/`
   - Multi-component flow → `tests/e2e/`

2. **Use existing fixtures** from `conftest.py`:
   ```python
   # Integration fixtures (tests/integration/conftest.py)
   stub_agent            # Stub agent with canned responses
   stub_execution_result # Canned ExecutionResult with test data
   stub_stream_events    # Canned stream events for streaming tests
   stub_settings         # Canned settings with test configuration
   fake_db               # Fake database with in-memory interface
   test_app              # Minimal test FastAPI app (no middleware)
   client                # FastAPI TestClient
   ```

3. **Test file location** mirrors source:
   ```
   my_agentic_serviceservice_order_specialist/platform/agent/config.py
   → tests/unit/platform/agent/test_config.py

   my_agentic_serviceservice_order_specialist/agents/knowledge/routes.py
   → tests/integration/test_knowledge_routes.py
   ```

4. **Async tests** work automatically (no decorator needed due to `asyncio_mode = "auto"`):
   ```python
   async def test_agent_run_returns_result(mock_agent):
       result = await mock_agent.run(message="test", thread_id="t1")
       assert result.response is not None
   ```

5. **Mock patterns**:
   ```python
   # Mock async function
   from unittest.mock import AsyncMock, Mock
   mock_obj.async_method = AsyncMock(return_value=expected)

   # Mock async generator
   async def mock_stream(*args, **kwargs):
       yield event1
       yield event2
   mock_obj.astream = mock_stream

   # Mock context manager
   from contextlib import asynccontextmanager
   @asynccontextmanager
   async def mock_session():
       yield mock_db_session
   ```

6. **Avoid weak tests** that don't assert meaningful behavior:
   ```python
   # BAD: Just tests that async works with delays
   async def test_slow_operation():
       await asyncio.sleep(0.1)
       result = await thing.do()
       assert result  # What are we actually testing?

   # GOOD: Tests specific behavior
   async def test_operation_timeout_raises():
       with pytest.raises(TimeoutError):
           await thing.do(timeout=0.001)
   ```

7. **Run tests after changes**:
   ```bash
   make check  # Runs style, lint, type check, then tests
   ```

## Important Files Reference

| File | Purpose |
|------|---------|
| `my_agentic_serviceservice_order_specialist/__init__.py` | Application factory |
| `my_agentic_serviceservice_order_specialist/platform/settings.py` | All configuration |
| `my_agentic_serviceservice_order_specialist/platform/agent/protocol.py` | Agent protocol |
| `my_agentic_serviceservice_order_specialist/platform/agent/config.py` | Config dataclasses |
| `my_agentic_serviceservice_order_specialist/platform/server/app.py` | FastAPI app factory |
| `my_agentic_serviceservice_order_specialist/agents/knowledge/agent.py` | Example agent builder |
| `example.env` | Environment variable template |

## Code Conventions

- **Imports**: Absolute imports from package root
  ```python
  from my_agentic_serviceservice_order_specialist.platform import Agent, LangGraphAgent
  from my_agentic_serviceservice_order_specialist.agents.knowledge.state import AgentState
  ```
- **Type hints**: Required on all public functions
- **Docstrings**: Google style
- **Async**: Use `async/await` for I/O operations
- **Config**: Never hardcode, use Settings or dataclass configs
- **Formatting**: `ruff format` (run `make style`)
- **Linting**: `ruff check` (run `make lint`)

## Environment Variables

Key variables (see `example.env` for full list). Uses `__` delimiter for nested Pydantic settings:

| Variable | Description |
|----------|-------------|
| `APP_HTTP__HOST` | HTTP server bind address (default: 0.0.0.0) |
| `APP_HTTP__PORT` | Service HTTP port (default: 8000) |
| `APP_HTTP__LOG_LEVEL` | Logging level: DEBUG, INFO, WARNING, ERROR |
| `APP_HTTP__LOG_JSON` | Force JSON logging (auto-detects by release stage) |
| `PRIMARY_DB__HOST` | PostgreSQL primary host |
| `PRIMARY_DB__DATABASE` | Database name |
| `REPLICA_DB__HOST` | PostgreSQL replica host (read-only queries) |
| `LITELLM__PROXY_API_BASE` | LiteLLM proxy URL for LLM access |
| `LITELLM__PROXY_API_KEY` | LiteLLM API key |
| `A2A__PATH` | Path prefix for A2A endpoints (default: /a2a) |
| `A2A__PROTOCOL_VERSION` | A2A protocol version |
| `AGENT_REGISTRY__URL` | External agent registry URL (optional) |
| `AGENT_REGISTRY__SHOULD_REGISTER` | Enable/disable registry registration |
| `OPENTELEMETRY__ENABLED` | Enable OpenTelemetry tracing |
| `OPENTELEMETRY__HOST` | Jaeger/OTLP collector host |
| `BUGSNAG__API_KEY` | Bugsnag error tracking API key |
| `BUGSNAG__RELEASE_STAGE` | Environment: local, development, production |

## Documentation

| Document | When to Read |
|----------|--------------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Before making structural changes. Explains the "why" behind design decisions, request flow diagrams, and layer responsibilities. |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | When something isn't working. Common issues and solutions. |
| [docs/DEBUGGING.md](docs/DEBUGGING.md) | When you need to investigate behavior. Debugging techniques and tools. |
| [agents/README.md](my_agentic_serviceservice_order_specialist/agents/README.md) | When creating or modifying agents. Detailed guide with code examples, testing patterns, and best practices. |
