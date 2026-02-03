# Integration Tests

Tests for **component interfaces** using mocks and test doubles.

## Criteria

A test belongs here if:
- Tests interaction between components
- Uses mocks/fakes for external systems (database, HTTP, LLM)
- Verifies interface contracts between modules
- Tests error handling across boundaries
- Does NOT require real external systems

## What Belongs Here

- Repository methods with mocked database sessions
- HTTP clients with `respx` mocked responses
- Agent nodes with mocked LLM chains
- API routes with test client (`TestClient`)
- MCP client with mocked server responses
- Error handling with simulated failures

## What Does NOT Belong Here

- Pure function tests (move to `unit/`)
- Tests requiring real PostgreSQL (move to `e2e/`)
- Tests requiring real external APIs (move to `e2e/`)

## Test Doubles

| Real System | Test Double | Library |
|-------------|-------------|---------|
| PostgreSQL | `AsyncMock` session | `unittest.mock` |
| HTTP APIs | `respx` mock | `respx` |
| LLM | `Mock` with returns | `unittest.mock` |
| MCP Server | `AsyncMock` client | `unittest.mock` |

## Examples

```python
# GOOD: Mocked database session
async def test_list_conversations(mock_db_session):
    mock_db_session.execute.return_value = Mock(fetchall=lambda: [row])
    repo = ConversationRepository(db_engine=mock_db)
    result = await repo.list_conversations(...)
    assert len(result.items) == 1

# GOOD: Mocked HTTP with respx
async def test_mcp_client_timeout():
    with respx.mock:
        respx.post("http://localhost/mcp").respond(json={"ok": True})
        client = MCPClient(server_url="http://localhost/mcp")
        result = await client.call("method", {})
        assert result == {"ok": True}

# GOOD: Mocked LLM chain
async def test_reasoner_returns_response(mock_chain):
    mock_chain.ainvoke.return_value = AIMessage(content="Response")
    node = ReasonerNode(llm_with_tools=mock_llm, ...)
    result = await node(state)
    assert result["messages"][0].content == "Response"

# BAD: Real database (move to e2e/)
async def test_persists_data(real_postgres_container):
    ...
```

## Shared Fixtures

Common fixtures are defined in `conftest.py`:
- `mock_agent` - Agent with mocked LLM
- `test_client` - FastAPI TestClient
- `mock_db_engine` - Mocked database engine

## Running

```bash
pytest tests/integration/ -v
pytest tests/integration/ -v -k "repository"  # Filter by name
```
