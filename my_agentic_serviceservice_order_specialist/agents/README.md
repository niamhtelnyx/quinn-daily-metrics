# Agents Directory

**This is where YOUR code goes.**

The `agents/` directory contains your squad's agent implementations. Each agent is a self-contained module that uses the platform infrastructure provided in `../platform/`.

## Quick Start: Create a New Agent

1. **Copy the example agent:**
   ```bash
   cp -r knowledge/ my_agent/
   ```

2. **Rename and customize:**
   - `agent.py` - Update the builder class name and default config
   - `prompt.py` - Write your agent's system prompt
   - `state.py` - Adjust state if needed
   - `routes.py` - Update route prefix and handler names

3. **Register HTTP routes** in `platform/server/app.py`:
   ```python
   from my_agentic_serviceservice_order_specialist.agents.my_agent.routes import my_agent_router
   app.include_router(my_agent_router)
   ```

4. **For A2A support**, create `a2a_setup.py` in your agent folder (copy from knowledge), then register in `platform/server/routes/a2a.py`:
   ```python
   from my_agentic_serviceservice_order_specialist.agents.my_agent.a2a_setup import build_and_mount_my_agent

   # In add_a2a_routes_to_app():
   agent_registrations.append(
       await build_and_mount_my_agent(app, task_store)
   )
   ```

## Agent Structure

Each agent directory should contain:

```
my_agent/
├── __init__.py           # Exports (optional)
├── agent.py              # AgentBuilder class - main entry point
├── routes.py             # FastAPI routes for this agent
├── state.py              # LangGraph state TypedDict
├── prompt.py             # System prompt generation
├── card.py               # A2A capabilities card builder
├── a2a_setup.py          # A2A registration helper (builds and mounts agent)
├── nodes/                # Graph nodes
│   ├── __init__.py       # Exports ReasonerNode, ToolNodeFactory
│   ├── base.py           # Node protocol
│   ├── reasoner.py       # LLM reasoning node
│   └── tools.py          # Tool execution node + artifact handling
└── tools/                # Agent-specific tools (optional)
    ├── __init__.py
    └── my_tool.py
```

## Key Components

### 1. Agent Builder (`agent.py`)

The builder pattern assembles your agent:

```python
from my_agentic_serviceservice_order_specialist.platform import (
    AgentConfig, LlmConfig, MCPConfig, LangGraphAgent, AgentIdentity
)

class MyAgentBuilder:
    def __init__(self, agent_config, llm_config, mcp_configs, checkpointer, identity):
        # mcp_configs is a list[MCPConfig] to support multiple MCP servers
        ...

    async def build(self) -> LangGraphAgent:
        # 1. Create LLM client (ChatLiteLLM)
        # 2. Fetch tools from all MCP servers concurrently
        # 3. Add agent-specific tools
        # 4. Build graph nodes (ReasonerNode, ToolNodeFactory)
        # 5. Compile StateGraph with checkpointer
        # 6. Return LangGraphAgent wrapper with identity

    @classmethod
    def default_builder(cls, llm_base_url, llm_api_key, checkpointer, identity=None):
        # Factory with sensible defaults for LlmConfig, MCPConfig, AgentConfig
```

### 2. State (`state.py`)

Define what your agent tracks:

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

class MyAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    reasoning_steps: int
    thread_id: str
    agent_slug: str                         # Identifier for the agent type
    input_tokens_by_model: dict[str, int]   # Cumulative input tokens by model
    output_tokens_by_model: dict[str, int]  # Cumulative output tokens by model
    # Add your custom fields
```

### 3. System Prompt (`prompt.py`)

Define your agent's persona:

```python
def build_system_prompt() -> str:
    return """You are a helpful assistant specialized in...

    ## Your Capabilities
    - ...

    ## Guidelines
    - ...
    """
```

### 4. Routes (`routes.py`)

Expose HTTP endpoints:

```python
from fastapi import APIRouter, Depends
from my_agentic_serviceservice_order_specialist.platform.server.dependencies.db import get_db_checkpointer
from my_agentic_serviceservice_order_specialist.platform.server.dependencies.settings import get_settings

my_agent_router = APIRouter(prefix="/my-agent", tags=["agents"])

@my_agent_router.post("/invoke")
async def invoke(payload: Payload, settings=Depends(get_settings), ...):
    builder = MyAgentBuilder.default_builder(...)
    agent = await builder.build()
    return await agent.run(payload.question, thread_id=str(payload.thread_id))
```

## Using Platform Infrastructure

Import from the platform module:

```python
# Core types
from my_agentic_serviceservice_order_specialist.platform import Agent, LangGraphAgent

# Configuration
from my_agentic_serviceservice_order_specialist.platform import AgentConfig, LlmConfig, MCPConfig, AgentIdentity

# Audience enum for AgentIdentity
from my_agentic_serviceservice_order_specialist.platform.agent.config import Audience
# Audience.CUSTOMER, Audience.INTERNAL, Audience.PUBLIC

# Tools
from my_agentic_serviceservice_order_specialist.platform import MCPClient, LangGraphMCPTools

# Messages
from my_agentic_serviceservice_order_specialist.platform import ExecutionResult, StreamEvent, Message

# Settings (for dependency injection)
from my_agentic_serviceservice_order_specialist.platform import Settings
```

### Configuration Quick Reference

```python
# LLM Configuration
LlmConfig(
    model="litellm_proxy/anthropic/claude-sonnet-4-5",
    api_key="your-key",
    base_url="http://litellm-proxy:4000/v1",
    temperature=0.7,
)

# MCP Server Configuration (supports multiple servers)
MCPConfig(
    server_url="http://mcp-server:8000/mcp/",
    tool_prefix="mytools",  # Optional: prefix for tool names
)

# Agent Behavior Configuration
AgentConfig(
    max_reasoning_steps=15,        # Max reasoning iterations
    artifact_threshold=5000,       # Hide large outputs (chars)
    always_visible_tools=frozenset({"inspect_artifact"}),  # Never hide these (exact match)
    always_visible_tool_suffixes=frozenset({"_fetch_relevant_tools"}),  # Never hide (suffix match)
    recursion_limit=50,            # LangGraph recursion limit
)

# Agent Identity
AgentIdentity(
    name="My Agent",
    description="An agent that helps with...",
    slug="my-agent",               # Used in API routes
    squad="my.squad",
    origin="my-service",
    audience=Audience.INTERNAL,    # CUSTOMER, INTERNAL, or PUBLIC
)
```

## Node Implementation

### ReasonerNode
The reasoner node calls the LLM with bound tools. Key responsibilities:
- Message trimming (prevents context overflow)
- Token tracking (input/output by model)
- Step limiting (forces final answer when max reached)

### ToolNodeFactory
Creates tool nodes with optional artifact wrapping:
- Intercepts tool execution to hide large outputs
- Tracks tool call metrics (duration, errors)
- Returns `ToolMessage` with content or artifact reference

## A2A Setup

To enable A2A (Agent-to-Agent) protocol for your agent:

1. **Create `card.py`** - Define skills and capabilities:
```python
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

class YourAgentCardBuilder:
    def build(self) -> AgentCard:
        return AgentCard(
            name=self.agent.name,
            description=self.agent.description,
            url=f"{self.a2a_base_url}/{self.agent.slug}/rpc",
            version=self.a2a_protocol_version,
            capabilities=AgentCapabilities(streaming=True),
            skills=[AgentSkill(id="...", name="...", description="...")],
        )
```

2. **Create `a2a_setup.py`** - Factory function:
```python
async def build_and_mount_your_agent(app: FastAPI, task_store: TaskStore):
    builder = YourAgentBuilder.default_builder(...)
    agent = await builder.build()
    agent_card = YourAgentCardBuilder(agent, ...).build()
    a2a_app = await create_a2a_application(agent, agent_card, task_store)
    a2a_app.add_routes_to_app(app, ...)
    return agent_card, agent.identity, tools
```

## Testing Your Agent

Tests live in the `tests/` directory at the project root. When creating a new agent, add corresponding tests.

### Test Directory Structure

```
tests/
├── unit/                    # Fast, isolated tests (no external services)
│   └── agents/
│       └── my_agent/
│           ├── test_prompt.py     # System prompt tests
│           └── test_state.py      # State helpers tests
│
├── integration/             # Tests with mocked database and services
│   └── agents/
│       └── my_agent/
│           ├── test_routes.py     # HTTP endpoint tests
│           └── test_agent.py      # Agent builder tests
│
└── e2e/                     # Full-stack tests (optional)
    └── test_my_agent_e2e.py
```

### Available Test Fixtures

Use these fixtures from `tests/integration/conftest.py`:

| Fixture | Type | Purpose |
|---------|------|---------|
| `stub_agent` | Stub | Returns predetermined results. Use for route/handler testing. |
| `stub_execution_result` | Stub | Canned ExecutionResult with test data. |
| `stub_stream_events` | Stub | Canned stream events for streaming tests. |
| `fake_db` | Fake | In-memory database-like interface. Use for persistence testing. |
| `stub_settings` | Stub | Canned settings with test configuration. |
| `test_app` | FastAPI | Minimal test app with routes (no middleware). |
| `client` | TestClient | HTTP client for the test app. |

**Fixture Terminology:**
- **Stub**: Provides predetermined return values (canned responses)
- **Fake**: Simplified working implementation (e.g., in-memory DB)
- **Mock**: Tracks interactions for verification (use `unittest.mock.Mock`)

### What to Test

1. **Route handlers** - Use `stub_agent` and `client`:
   ```python
   def test_invoke_returns_response(client, stub_agent):
       response = client.post("/my-agent/invoke", json={"question": "test"})
       assert response.status_code == 200
       assert "response" in response.json()
   ```

2. **Streaming** - Test SSE format:
   ```python
   def test_stream_returns_events(client):
       with client.stream("POST", "/my-agent/stream", json={"question": "test"}) as r:
           events = list(r.iter_lines())
           assert any(b"data:" in e for e in events)
   ```

3. **Agent builder** - Test tool discovery and graph creation:
   ```python
   async def test_builder_creates_agent(mock_mcp_client, checkpointer):
       builder = MyAgentBuilder.default_builder(...)
       agent = await builder.build()
       assert agent.name == "My Agent"
   ```

4. **Error handling** - Test edge cases:
   ```python
   def test_empty_question_rejected(client):
       response = client.post("/my-agent/invoke", json={"question": ""})
       assert response.status_code == 422  # Validation error
   ```

### Running Tests

```bash
# Run all tests locally
make check

# Run specific test file
pytest tests/integration/agents/my_agent/test_routes.py -v

# Run with coverage
pytest --cov=my_agentic_serviceservice_order_specialist.agents.my_agent tests/

# Run in Docker (CI environment)
make test
```

### Mocking MCP Servers

For tests that need tool discovery without a real MCP server:

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_mcp_tools():
    with patch("my_agentic_serviceservice_order_specialist.platform.agent.langgraph.LangGraphMCPTools") as mock:
        mock.fetch_all = AsyncMock(return_value=[])  # No tools
        yield mock
```

---

## Best Practices

1. **Be cautious modifying `platform/`** - Template updates via `make update-template` use copier's merge mechanism. If you add tables, repositories, or extend platform code, review conflicts carefully during updates.
2. **Use config dataclasses** - Never hardcode URLs, keys, or limits
3. **Follow the builder pattern** - Makes testing and customization easier
4. **Keep prompts in `prompt.py`** - Easy to find and modify
5. **Use MCP for shared tools** - Agent-specific tools go in `tools/`
6. **Initialize token tracking** - Always include `input_tokens_by_model: {}` and `output_tokens_by_model: {}` in initial state
7. **Test with streaming** - Both `/invoke` and `/stream` endpoints should work
8. **Write tests for your agent** - At minimum: routes, builder, and error cases
