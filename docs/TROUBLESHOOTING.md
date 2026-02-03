# Troubleshooting Guide

This guide helps diagnose and resolve common issues when working with the agentic service.

## Agent Returns Empty Response

**Symptoms:** Agent invocation succeeds but returns empty or no content.

**Possible Causes & Solutions:**

1. **LLM Configuration Issues**
   - Check `LITELLM__PROXY_API_BASE` and `LITELLM__PROXY_API_KEY` in your env file
   - Verify the LiteLLM proxy is accessible: `curl $LITELLM__PROXY_API_BASE/health`
   - Check logs for authentication errors

2. **System Prompt Issues**
   - Review the system prompt in `agents/knowledge/prompt.py`
   - Ensure it doesn't instruct the agent to stay silent

3. **Tool Discovery Failed**
   - Look for log: `Discovered N tools` on startup
   - If N=0, check MCP server connectivity (see MCP section below)

4. **Context Trimming**
   - Very long conversations may trim important context
   - Check `max_context_tokens` in AgentConfig

---

## MCP Connection Failed

**Symptoms:** Agent starts but has no tools, or logs show MCP errors.

**Possible Causes & Solutions:**

1. **MCP Server Not Running**
   ```bash
   # Check if MCP server is reachable
   curl -X POST $MCP_SERVER_URL/tools/list
   ```

2. **Environment Variables Missing**
   - Verify `AGENTS_MCP__<AGENT_SLUG>__SERVERS` is set correctly
   - Format: JSON array of server configurations

3. **Network Issues**
   - Check firewall rules between service and MCP server
   - Verify DNS resolution for MCP server hostname

4. **Timeout Configuration**
   - Increase `timeout` in MCPConfig if MCP server is slow
   - Default is 60 seconds

**Testing MCP Manually:**
```python
from my_agentic_serviceservice_order_specialist.platform.agent.mcp import MCPClient

async def test_mcp():
    client = MCPClient(server_url="http://your-mcp-server")
    tools = await client.list_tools()
    print(f"Found {len(tools)} tools")
```

---

## Database Errors

### Migration Failures

**Symptoms:** `alembic upgrade head` fails, or service won't start.

**Solutions:**

1. **Check Database Connectivity**
   ```bash
   psql -h $PRIMARY_DB__HOST -U $PRIMARY_DB__USER -d $PRIMARY_DB__DATABASE
   ```

2. **Reset Database (Development Only)**
   ```bash
   make db-reset
   ```

3. **Manual Migration**
   ```bash
   alembic current  # Check current state
   alembic history  # View migration history
   alembic upgrade head  # Apply pending migrations
   ```

### Connection Pool Exhaustion

**Symptoms:** `asyncpg.exceptions.TooManyConnectionsError`

**Solutions:**

1. **Increase Pool Size**
   - Adjust `PRIMARY_DB__POOL_SIZE` in env (default: 10)
   - Ensure database max_connections supports the pool size

2. **Check for Connection Leaks**
   - Ensure all database sessions are properly closed
   - Use `async with` for session management

### Checkpointer Errors

**Symptoms:** LangGraph state persistence fails.

**Solutions:**

1. **Verify checkpointer table exists:**
   ```sql
   SELECT * FROM pg_tables WHERE tablename LIKE 'checkpoint%';
   ```

2. **Recreate checkpointer table:**
   - The checkpointer table is created automatically on startup
   - If corrupted, drop and restart the service

---

## Tool Not Found

**Symptoms:** Agent can't find a specific tool or tool call fails.

**Possible Causes & Solutions:**

1. **Tool Not Registered**
   - Check MCP server exposes the tool via `/tools/list`
   - Verify tool name matches (case-sensitive)

2. **Tool Naming Convention**
   - MCP tools are prefixed: `mcp_<tool_name>` or `mcp_<prefix>_<tool_name>`
   - Built-in tools (like `inspect_artifact`) have no prefix

3. **Schema Validation Failed**
   - Look for warning: `Invalid tool schema for '<name>'`
   - Ensure tool's inputSchema has a `properties` key

4. **Tool Collision**
   - Multiple MCP servers may expose tools with same name
   - Configure `tool_prefix` in MCPConfig to disambiguate

---

## Performance Issues

### Slow Response Times

**Symptoms:** Agent takes too long to respond.

**Diagnosis:**

1. **Check reasoning steps:**
   - Response includes `reasoning_steps` count
   - High count (>10) suggests complex reasoning or loops

2. **Review tool latency:**
   - Check `/metrics` endpoint for tool duration histograms
   - Slow tools may need timeout configuration

**Solutions:**

1. **Reduce max_reasoning_steps** (currently 15)
2. **Increase tool timeouts** for slow external services
3. **Enable tool caching** if tools return stable data

### Token Limit Exceeded

**Symptoms:** Agent response is cut off or returns error.

**Solutions:**

1. **Check max_context_tokens**
   - Default: ~100k tokens
   - Reduce conversation history or increase limit

2. **Enable message trimming**
   - Configured via `trim_messages` in reasoner node
   - Uses "last" strategy by default

---

## Streaming Issues

### Stream Disconnects

**Symptoms:** SSE stream closes prematurely.

**Solutions:**

1. **Check proxy buffering:**
   - Response includes `X-Accel-Buffering: no` header
   - Verify nginx/proxy respects this header

2. **Client timeout:**
   - Increase client-side timeout for long operations
   - Consider heartbeat events for keep-alive

---

## Logging and Diagnostics

### Enable Debug Logging

```bash
# In your env file
APP_HTTP__LOG_LEVEL=DEBUG
```

### Key Log Messages to Watch

| Log Message | Meaning |
|-------------|---------|
| `Discovered N tools` | Tools loaded from MCP servers |
| `task_failed` | Agent execution failed (check error field) |
| `Invalid tool schema` | MCP tool has malformed schema |
| `no_user_input` | A2A request had empty message |

### Correlation IDs

Every request includes a correlation ID in logs:
```
correlation_id=abc-123 | Processing request...
```

Use this to trace a single request across all log entries.

---

## Getting Help

If you can't resolve an issue:

1. Check existing issues in the repository
2. Gather logs with correlation ID
3. Note environment (local/docker/k8s)
4. Create an issue with reproduction steps
