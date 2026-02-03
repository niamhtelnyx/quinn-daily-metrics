# Architecture Overview

This document explains the high-level architecture of the agentic service, the reasoning behind key design decisions, and how the components fit together.

## Core Principle: Platform vs Agents

The codebase is split into two areas:

```
my_agentic_serviceservice_order_specialist/
├── platform/    # Foundation - maintained by AI Platform, extensible by squads
└── agents/      # Your agents - fully owned by your squad
```

| Directory | Maintained By | Your Squad Can | Template Updates |
|-----------|---------------|----------------|------------------|
| `platform/` | AI Platform | Extend (add tables, repos, business logic) | May require merge conflict resolution |
| `agents/` | Your Squad | Full ownership | No conflicts |

**The key distinction:**
- `platform/` is a **foundation you build upon** - AI Platform maintains the core, but you can add database tables, repositories, and business logic for your tools/use cases
- `agents/` is **purely your code** - no template overlap, no merge concerns

**Why this model?**
- Squads get working infrastructure out of the box
- Platform improvements propagate via `make update-template`
- Squads can still customize without forking
- When extending `platform/`, be mindful that template updates may touch the same files

---

## Request Flow

When a request hits the service, it flows through these layers:

```
                                    ┌─────────────────────────────────────────┐
                                    │              HTTP Request               │
                                    └────────────────────┬────────────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                      MIDDLEWARE                                         │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐          │
│  │   Correlation ID    │ ─► │  Prometheus Metrics │ ─► │   Error Handling    │          │
│  │  (request tracing)  │    │    (duration, etc)  │    │     (Bugsnag)       │          │
│  └─────────────────────┘    └─────────────────────┘    └─────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                        ROUTES                                           │
│                                                                                         │
│  Platform Routes                          Agent Routes                                  │
│  ┌─────────────────────┐                  ┌─────────────────────┐                       │
│  │ /health, /info      │                  │ /{agent}/invoke     │                       │
│  │ /metrics            │                  │ /{agent}/stream     │                       │
│  │ /conversations      │                  │ /a2a/{agent}/...    │                       │
│  └─────────────────────┘                  └─────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                     DEPENDENCIES                                        │
│                              (FastAPI Dependency Injection)                             │
│                                                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                      │
│  │    Settings     │    │   DB Sessions   │    │  Agent Factory  │                      │
│  │  (from env)     │    │  (from pool)    │    │ (builds agent)  │                      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    AGENT EXECUTION                                      │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                            LangGraph State Machine                              │    │
│  │                                                                                 │    │
│  │    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐          │    │
│  │    │   START      │ ──────► │   Reasoner   │ ──────► │    Tools     │          │    │
│  │    └──────────────┘         │    (LLM)     │         │  (MCP/local) │          │    │
│  │                             └──────┬───────┘         └──────┬───────┘          │    │
│  │                                    │                        │                  │    │
│  │                                    │    ◄───────────────────┘                  │    │
│  │                                    │         (loop until done)                 │    │
│  │                                    ▼                                           │    │
│  │                             ┌──────────────┐                                   │    │
│  │                             │     END      │                                   │    │
│  │                             └──────────────┘                                   │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                       DATABASE                                          │
│                                                                                         │
│  ┌─────────────────────────────────┐    ┌─────────────────────────────────┐            │
│  │         Primary DB              │    │         Replica DB              │            │
│  │    (read-write, checkpoints)    │    │    (read-only, queries)         │            │
│  └─────────────────────────────────┘    └─────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### 1. Middlewares (`platform/server/middlewares/`)

Middleware processes every request before it reaches route handlers.

| Middleware | Purpose |
|------------|---------|
| Correlation ID | Adds `X-Request-ID` header for distributed tracing |
| Prometheus | Records request duration, status codes for metrics |

### 2. Routes (`platform/server/routes/` + `agents/*/routes.py`)

Routes define HTTP endpoints. Platform routes handle infrastructure concerns, agent routes handle business logic.

**Platform routes are fixed.** Agent routes are where you expose your agent's capabilities.

### 3. Dependencies (`platform/server/dependencies/`)

FastAPI's dependency injection system provides:
- **Settings**: Configuration from environment variables
- **Database sessions**: Connection from the pool
- **Agent instances**: Built and cached per request

**Why dependency injection?**
- Makes testing easy (swap real DB for fake)
- Centralizes resource management
- Avoids global state

### 4. Agent Execution

The agent uses LangGraph to orchestrate LLM reasoning and tool execution:

1. **Reasoner Node**: Calls the LLM with available tools
2. **Tools Node**: Executes any tools the LLM selected
3. **Loop**: Continues until the LLM produces a final answer or hits max steps

**Why LangGraph?**
- Built-in state management and checkpointing
- Supports streaming out of the box
- Graph model makes complex flows explicit

### 5. Database (`platform/database/`)

Two database connections serve different purposes:

| Connection | Pool Type | Purpose |
|------------|-----------|---------|
| Primary | psycopg (for LangGraph) | Checkpoints, writes |
| Replica | SQLAlchemy | Read-only queries |

**Why two pools?**
- LangGraph's checkpointer requires direct psycopg connections
- Read replicas reduce load on primary for queries
- If you only have one database, configure both to point to it

---

## Key Design Decisions

### 1. Builder Pattern for Agents

```python
builder = KnowledgeAgentBuilder.default_builder(...)
agent = await builder.build()
```

**Why?**
- Separates configuration from construction
- Makes testing easier (inject mock dependencies)
- Allows sensible defaults while permitting customization

### 2. MCP for Tool Integration

Tools are fetched from MCP (Model Context Protocol) servers at startup.

**Why MCP?**
- Standard protocol for tool discovery and execution
- Tools can be shared across agents and services
- Decouples tool implementation from agent code

### 3. Checkpointing for Conversation State

Every step of the agent's execution is saved to PostgreSQL.

**Why?**
- Conversations can be resumed after service restarts
- Enables the `/conversations` API for inspection
- Provides audit trail of agent behavior

### 4. Streaming via SSE

The `/stream` endpoint uses Server-Sent Events.

**Why SSE over WebSockets?**
- Simpler to implement and debug
- Works through most proxies and load balancers
- Sufficient for server-to-client streaming (agent responses)

### 5. A2A Protocol

Agents can communicate with each other via the A2A (Agent-to-Agent) protocol.

**Why?**
- Enables multi-agent architectures
- Standardized discovery via capability cards
- Agents can delegate tasks to specialized agents

---

## Directory Structure Explained

```
my_agentic_serviceservice_order_specialist/
├── __init__.py              # App factory (entry point for ASGI servers)
├── __main__.py              # CLI entry point (python -m my_agentic_serviceservice_order_specialist)
│
├── platform/                # ═══ INFRASTRUCTURE (don't modify) ═══
│   ├── settings.py          # All configuration via environment variables
│   ├── constants.py         # Service name, version, squad
│   │
│   ├── agent/               # Agent abstractions
│   │   ├── protocol.py      # Agent interface (what all agents must implement)
│   │   ├── config.py        # Configuration dataclasses (LlmConfig, etc.)
│   │   ├── langgraph.py     # LangGraph integration and MCP→LangChain adapter
│   │   ├── mcp.py           # MCP client for tool discovery
│   │   ├── a2a.py           # Agent-to-Agent protocol adapter
│   │   └── messages.py      # Framework-agnostic message types
│   │
│   ├── server/              # HTTP layer
│   │   ├── app.py           # FastAPI app factory with lifecycle management
│   │   ├── routes/          # Platform HTTP endpoints
│   │   ├── dependencies/    # Dependency injection providers
│   │   └── middlewares/     # Request/response middlewares
│   │
│   ├── database/            # Persistence layer
│   │   ├── engine.py        # Connection pool management
│   │   ├── tables.py        # SQLAlchemy table definitions
│   │   └── repositories/    # Data access layer
│   │
│   └── observability/       # Monitoring
│       ├── metrics.py       # Prometheus metrics
│       ├── logging.py       # Structured logging
│       └── errors.py        # Error reporting (Bugsnag)
│
└── agents/                  # ═══ YOUR CODE ═══
    └── knowledge/           # Example agent (copy this for new agents)
        ├── agent.py         # Builder class
        ├── routes.py        # HTTP endpoints
        ├── state.py         # LangGraph state definition
        ├── prompt.py        # System prompt
        ├── card.py          # A2A capability card
        ├── a2a_setup.py     # A2A registration
        ├── nodes/           # Graph nodes (reasoner, tools)
        └── tools/           # Agent-specific tools
```

---

## Where Do I Put X?

| I want to... | Put it in... | Notes |
|--------------|--------------|-------|
| Create a new agent | `agents/my_agent/` | Copy from `knowledge/` |
| Add a custom tool for one agent | `agents/my_agent/tools/` | Agent-specific |
| Add a shared tool for all agents | Create an MCP server | Separate service |
| Change the system prompt | `agents/my_agent/prompt.py` | |
| Add an HTTP endpoint for my agent | `agents/my_agent/routes.py` | |
| Modify agent state | `agents/my_agent/state.py` | |
| Add a database table | `platform/database/tables.py` | + Alembic migration |
| Add a database query/repository | `platform/database/repositories/` | Mind template updates |
| Add business logic for tools | `platform/` (appropriate subdir) | Mind template updates |
| Add environment config | `platform/settings.py` | Mind template updates |
| Change logging format | Don't modify | Core platform concern |

---

## Testing Strategy

```
tests/
├── unit/           # Fast, isolated, no external services
├── integration/    # Real database (via testcontainers), mocked MCP
└── e2e/            # Full system tests
```

**Guidelines:**
- Unit tests for pure logic (prompts, state helpers, utilities)
- Integration tests for routes, agent builder, database queries
- E2E tests for critical user journeys

See `agents/README.md` for detailed testing guidance and available fixtures.

---

## Configuration Flow

All configuration flows through `platform/settings.py` using Pydantic Settings:

```
Environment Variables
        │
        ▼
┌───────────────────┐
│  platform/        │
│  settings.py      │    Pydantic validates and types all config
│  (Settings class) │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Dependencies     │    FastAPI injects settings where needed
│  get_settings()   │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Your Code        │    Access via function parameters
│  (routes, agents) │
└───────────────────┘
```

**Nested config** uses `__` delimiter:
- `PRIMARY_DB__HOST` → `settings.primary_db.host`
- `LITELLM__PROXY_API_KEY` → `settings.litellm.proxy_api_key`

---

## Naming Conventions

| Context | Convention | Example |
|---------|------------|---------|
| Python packages | snake_case | `my_agentic_serviceservice_order_specialist` |
| Python files | snake_case | `agent_builder.py` |
| Python classes | PascalCase | `KnowledgeAgentBuilder` |
| HTTP routes | kebab-case | `/knowledge/invoke` |
| Environment variables | SCREAMING_SNAKE | `PRIMARY_DB__HOST` |
| Docker services | kebab-case | `my-agentic-serviceservice-order-specialist` |

**Note:** The package name uses underscores (`my_agentic_serviceservice_order_specialist`) because Python imports don't allow dashes. The repository and Docker names use dashes (`my-agentic-serviceservice-order-specialist`) per company standard.

---

## Further Reading

- [agents/README.md](../my_agentic_serviceservice_order_specialist/agents/README.md) - Detailed guide to creating agents
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues and solutions
- [DEBUGGING.md](./DEBUGGING.md) - Debugging techniques
