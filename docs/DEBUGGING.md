# Debugging Guide

This guide covers how to debug agent execution, trace requests, and investigate issues.

## Log Levels and Configuration

### Setting Log Level

```bash
# In your env file
APP_HTTP__LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR
```

### Log Format

- **Local development**: Colored console output (human-readable)
- **Docker/Production**: JSON structured logs (machine-parseable)

Control format explicitly:
```bash
APP_HTTP__LOG_JSON=true   # Force JSON
APP_HTTP__LOG_JSON=false  # Force console
```

---

## Correlation IDs

Every request is assigned a unique correlation ID that propagates through all log entries.

### Finding Correlation IDs

In logs:
```
correlation_id=abc-123-def | Processing request...
correlation_id=abc-123-def | Agent run completed
```

In responses (when enabled):
```json
{
  "response": "...",
  "metadata": {
    "correlation_id": "abc-123-def"
  }
}
```

### Filtering Logs by Correlation ID

```bash
# In Docker logs
docker logs my-agentic-serviceservice-order-specialist 2>&1 | grep "abc-123-def"

# In structured JSON logs
cat logs.json | jq 'select(.correlation_id == "abc-123-def")'
```

---

## Phoenix UI (OpenTelemetry Tracing)

Phoenix provides visual tracing for agent execution.

### Starting Phoenix

```bash
make run-docker  # Starts Phoenix alongside the service
# Phoenix UI: http://localhost:6006
```

### What Phoenix Shows

1. **Request Timeline**: See each step of agent execution
2. **LLM Calls**: Input/output for each model invocation
3. **Tool Calls**: Which tools were called and their responses
4. **Token Usage**: Input/output tokens per call
5. **Latency**: Time spent in each component

### Navigating Phoenix

1. Open http://localhost:6006
2. Find your trace by timestamp or thread_id
3. Click a trace to see the full execution graph
4. Expand nodes to see:
   - Input messages
   - Output messages
   - Tool calls and results
   - Token counts

### Filtering in Phoenix

- **By thread_id**: Search for the conversation thread
- **By time**: Use the time range picker
- **By status**: Filter successful/failed executions

---

## Agent State Inspection

### During Development

Add state logging to your agent builder:

```python
# In your agent's build() method
import structlog
logger = structlog.get_logger()

# After each graph node
@graph.node
async def my_node(state):
    logger.debug("node_state",
        messages_count=len(state.get("messages", [])),
        reasoning_steps=state.get("reasoning_steps", 0)
    )
    # ... node logic
```

### Via API

The `/invoke` response includes state metadata:

```json
{
  "response": "The answer is...",
  "messages": [...],
  "reasoning_steps": 3,
  "thread_id": "abc-123",
  "metadata": {
    "framework": "langgraph",
    "raw_state": {...}  // Full LangGraph state
  }
}
```

### Checkpointer State

To inspect persisted conversation state:

```python
# In a debug session or script
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def inspect_thread(thread_id: str):
    async with AsyncPostgresSaver.from_conn_string(db_url) as saver:
        config = {"configurable": {"thread_id": thread_id}}
        state = await saver.aget(config)
        print(f"Messages: {len(state.values.get('messages', []))}")
        print(f"Reasoning steps: {state.values.get('reasoning_steps')}")
```

---

## Verifying MCP Tools

### Check Tool Discovery on Startup

Look for this log on service startup:
```
Discovered 15 tools from MCP servers
```

If 0 tools, check MCP server connectivity.

### List Available Tools

```python
# Debug script
from my_agentic_serviceservice_order_specialist.platform.agent.mcp import MCPClient

async def list_tools():
    client = MCPClient(server_url="http://your-mcp-server")
    tools = await client.list_tools()
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")
```

### Test Individual Tool Calls

```python
async def test_tool(tool_name: str, args: dict):
    client = MCPClient(server_url="http://your-mcp-server")
    result = await client.call_tool(tool_name, args)
    print(f"Result: {result}")
```

---

## Common Debug Scenarios

### Agent Loops Forever

**Symptoms**: Reasoning steps keep incrementing, no final answer.

**Debug steps**:
1. Check `max_reasoning_steps` in AgentConfig (default: 15)
2. Enable DEBUG logging to see each step
3. In Phoenix, look for repeated identical tool calls
4. Check system prompt for clear termination conditions

### Tools Not Being Called

**Symptoms**: Agent responds without using tools.

**Debug steps**:
1. Verify tools are discovered (check startup logs)
2. Check system prompt instructs tool usage
3. In Phoenix, verify tool schemas are valid
4. Look for warning: `Invalid tool schema for '<name>'`

### Wrong Tool Called

**Symptoms**: Agent picks inappropriate tool.

**Debug steps**:
1. Review tool descriptions (shown to LLM)
2. Check for name collisions (multiple MCP servers)
3. Verify tool_prefix is set correctly for disambiguation

### Memory Issues

**Symptoms**: Out of memory or slow responses with long conversations.

**Debug steps**:
1. Check message count in response metadata
2. Verify `max_context_tokens` is set appropriately
3. Look for large tool responses (artifact threshold)

---

## Database Debugging

### Check Connection Pool

```sql
-- In PostgreSQL
SELECT count(*) FROM pg_stat_activity
WHERE application_name LIKE '%my_agentic_serviceservice_order_specialist%';
```

### Inspect Checkpointer Table

```sql
-- View recent checkpoints
SELECT thread_id, created_at, metadata
FROM checkpoints
ORDER BY created_at DESC
LIMIT 10;
```

### Clear Thread State

```sql
-- Reset a specific thread (development only!)
DELETE FROM checkpoints WHERE thread_id = 'your-thread-id';
```

---

## Metrics Endpoint

The `/metrics` endpoint exposes Prometheus metrics:

```bash
curl http://localhost:8000/metrics
```

Key metrics:
- `agent_execution_duration_seconds` - Agent run time
- `agent_tool_call_duration_seconds` - Per-tool latency
- `agent_tokens_total` - Token usage by model
- `agent_execution_total` - Success/error counts

---

## Debug Mode Checklist

When debugging an issue:

- [ ] Set `APP_HTTP__LOG_LEVEL=DEBUG`
- [ ] Note the correlation ID from your request
- [ ] Check Phoenix UI for trace details
- [ ] Filter logs by correlation ID
- [ ] Verify MCP tools are discovered
- [ ] Check reasoning step count
- [ ] Review token usage
- [ ] Inspect checkpointer state if persistence issue

---

## Getting More Help

If you can't resolve an issue:

1. Gather: correlation ID, log snippets, Phoenix trace link
2. Note: environment (local/docker/k8s), steps to reproduce
3. Check: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues
4. Create: issue in the repository with reproduction steps
