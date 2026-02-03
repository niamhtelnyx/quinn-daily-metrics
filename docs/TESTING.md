# Testing Guide

This document defines the testing strategy for the codebase. It provides clear criteria for choosing test types, best practices, and heuristics for both humans and code agents.

## Testing Pyramid

We follow the testing pyramid principle: **favor unit tests, then integration, then E2E**.

```
         /\
        /  \    E2E (few)
       /    \   Real systems, slow, expensive
      /------\
     /        \   Integration (moderate)
    /          \  Mocks/fakes, test interfaces
   /------------\
  /              \   Unit (many)
 /                \  Pure functions, fast, isolated
/__________________\
```

## Test Types at a Glance

| Type | Location | External Systems | Speed | Purpose |
|------|----------|------------------|-------|---------|
| Unit | `tests/unit/` | None | ~1ms/test | Test pure functions in isolation |
| Integration | `tests/integration/` | Mocked/faked | ~10-50ms/test | Test component interfaces |
| E2E | `tests/e2e/` | Real (containers) | ~1-10s/test | Test real workflows end-to-end |

---

## Unit Tests

### Definition
Unit tests verify **pure functions** and **stateless logic** in complete isolation. No external dependencies, no mocks of external systems, no I/O.

### Location
```
tests/unit/
├── agents/
│   └── knowledge/
│       ├── test_card.py              # Agent card generation
│       ├── test_inspect_artifact.py  # Artifact inspection
│       ├── test_prompt.py            # Prompt template logic
│       └── test_reasoner_helpers.py  # Token extraction, accumulation
└── platform/
    └── agent/
        ├── test_config.py         # Configuration parsing
        ├── test_identity.py       # Identity validation
        ├── test_messages.py       # Message formatting
        ├── test_metrics.py        # Metrics calculations
        ├── test_mcp_config.py     # MCP timeout defaults
        └── test_mcp_parsing.py    # JSON parsing logic
```

### When to Write Unit Tests

**DO write unit tests when:**
- Function takes inputs and returns outputs (pure function)
- Logic involves calculations, transformations, or parsing
- Function has no side effects (no I/O, no state mutation)
- Testing edge cases and boundary conditions
- Function is a static method or standalone utility

**DO NOT write unit tests when:**
- Function requires mocking external systems to test
- Function's primary purpose is I/O or coordination
- Testing would require complex setup of dependencies

### Decision Flowchart

```
Is the function pure (no I/O, no side effects)?
├─ YES → Unit test
└─ NO → Does it interact with external systems?
         ├─ YES (real systems) → E2E test
         └─ NO (can mock) → Integration test
```

### Unit Test Examples

```python
# GOOD: Pure function, no dependencies
class TestExtractTokens:
    def test_extracts_from_usage_metadata(self):
        """Token extraction from message metadata."""
        msg = Mock()
        msg.usage_metadata = {"input_tokens": 100, "output_tokens": 50}

        input_tokens, output_tokens = ReasonerNode._extract_tokens(msg)

        assert input_tokens == 100
        assert output_tokens == 50

# GOOD: Configuration parsing
class TestAgentConfig:
    def test_default_values(self):
        """Default configuration values are set."""
        config = AgentConfig()

        assert config.max_reasoning_steps == 10
        assert config.recursion_limit == 50

# GOOD: JSON parsing (pure transformation)
class TestMCPClientParseResult:
    def test_parse_content_valid_json(self):
        """Valid JSON is parsed correctly."""
        client = MCPClient(server_url="http://localhost:8000/mcp")
        content = Mock(text='{"key": "value"}')

        assert client._parse_content(content) == {"key": "value"}
```

### Best Practices

1. **No mocks of external systems** - If you need `AsyncMock` for a database or HTTP client, it's an integration test
2. **Test one behavior per test** - Each test should verify a single logical assertion
3. **Use descriptive names** - `test_extracts_tokens_from_usage_metadata` not `test_extract`
4. **Cover edge cases** - Empty inputs, None values, boundary conditions
5. **Keep tests fast** - Unit tests should run in milliseconds
6. **Use `pytest.mark.parametrize` to reduce boilerplate** - When testing the same logic with multiple inputs, use parametrization instead of separate test methods

### Using `pytest.mark.parametrize`

Parametrize tests when you have:
- Multiple input/output pairs for the same function
- Edge cases that follow the same test pattern
- Boundary condition testing

**When to use parametrize:**

| Scenario | Use Parametrize? |
|----------|------------------|
| Same assertion logic, different inputs | Yes |
| Testing boundary values (0, 1, max) | Yes |
| Different setup or assertions needed | No |
| Complex object construction per case | No |

**Example - Before (boilerplate):**
```python
def test_offset_page_one(self):
    pagination = Pagination(page=1, page_size=20)
    assert pagination.offset == 0

def test_offset_page_two(self):
    pagination = Pagination(page=2, page_size=20)
    assert pagination.offset == 20

def test_offset_page_three(self):
    pagination = Pagination(page=3, page_size=10)
    assert pagination.offset == 20
```

**Example - After (parametrized):**
```python
@pytest.mark.parametrize(
    ("page", "page_size", "expected_offset"),
    [
        (1, 20, 0),   # Page 1 has offset 0
        (2, 20, 20),  # Page 2 offset = page_size
        (3, 10, 20),  # Page 3 offset = 2 * page_size
        (5, 25, 100), # Page 5 offset = 4 * 25
    ],
)
def test_offset_calculation(self, page: int, page_size: int, expected_offset: int):
    """Offset is calculated as (page - 1) * page_size."""
    pagination = Pagination(page=page, page_size=page_size)
    assert pagination.offset == expected_offset
```

**Benefits:**
- Each case runs as a separate test (clear failure reporting)
- Easy to add new cases (just add a tuple)
- Reduces code duplication
- Test output shows which parameters failed: `test_offset_calculation[3-10-20]`

**Heuristics:**
- 3+ similar tests → consider parametrize
- Tests differ only in input values → parametrize
- Tests need different setup/teardown → keep separate
- Edge case needs special assertion → keep separate

---

## Integration Tests

### Definition
Integration tests verify **component interfaces** and **interactions** using mocks, fakes, or test doubles. They test that components work together correctly without requiring real external systems.

### Location
```
tests/integration/
├── conftest.py                    # Shared fixtures (mock clients, test app)
├── test_agent_builder.py          # Agent construction with mocked LLM
├── test_agent_invoke.py           # Agent invocation with mocked responses
├── test_agent_stream.py           # Streaming with mocked LLM
├── test_agent_tools.py            # Tool execution with mocked tools
├── test_conversations_repository.py  # Repository with mocked DB session
├── test_database.py               # Database engine with mocked pool
├── test_error_handling.py         # Error scenarios with mocked failures
├── test_health_routes.py          # Health endpoints with test client
├── test_knowledge_routes.py       # API routes with mocked agent
├── test_mcp_http.py               # MCP client with respx mock
├── test_mcp_tools.py              # MCP tools with mocked client
├── test_reasoner_node.py          # Reasoner with mocked chain
└── test_tools_node.py             # Tools node with mocked execution
```

### When to Write Integration Tests

**DO write integration tests when:**
- Testing component interactions (A calls B correctly)
- Verifying interface contracts between modules
- Testing error handling across component boundaries
- Validating request/response flows with mocked backends
- Testing database repository methods with mocked sessions

**DO NOT write integration tests when:**
- Testing pure logic (use unit tests instead)
- Need to verify real system behavior (use E2E tests)
- Test would just be testing the mock itself

### Key Principle: Test Doubles

Integration tests use **test doubles** instead of real systems:

| Real System | Test Double | Library |
|-------------|-------------|---------|
| PostgreSQL | `AsyncMock` session | `unittest.mock` |
| HTTP APIs | `respx` mock | `respx` |
| LLM (ChatLiteLLM) | `Mock` with configured returns | `unittest.mock` |
| MCP Server | `AsyncMock` client | `unittest.mock` |

### Integration Test Examples

```python
# GOOD: Repository with mocked database session
class TestListConversations:
    async def test_list_conversations_with_results(self, mock_db_engine):
        """List returns conversation summaries."""
        mock_db, mock_session = mock_db_engine

        # Setup mock to return test data
        row = Mock()
        row.thread_id = "thread-123"
        row.created_at = "2025-01-01T00:00:00"
        mock_result = Mock()
        mock_result.fetchall.return_value = [row]
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = ConversationRepository(db_engine=mock_db)
        result = await repo.list_conversations(
            filters=ConversationFilters(),
            pagination=Pagination(),
        )

        assert result.total == 1
        assert result.items[0].thread_id == "thread-123"

# GOOD: HTTP client with respx mock
class TestMCPClientHTTP:
    async def test_timeout_is_applied(self):
        """HTTP client uses configured timeout."""
        with respx.mock:
            respx.post("http://localhost:8000/mcp").respond(json={"result": "ok"})

            client = MCPClient(server_url="http://localhost:8000/mcp", timeout=5.0)
            result = await client.call("test_method", {})

            assert result == {"result": "ok"}

# GOOD: Agent with mocked LLM chain
class TestReasonerNodeCall:
    async def test_call_normal_execution(self, mock_llm, agent_config, mock_chain):
        """Normal execution returns LLM response."""
        response = AIMessage(content="I can help with that.")
        mock_chain.ainvoke.return_value = response

        node = ReasonerNode(llm_with_tools=mock_llm, config=agent_config)
        state = {"messages": [HumanMessage(content="Hello")], ...}

        with patch.object(node, "_trimmer") as mock_trimmer:
            mock_trimmer.__or__ = Mock(return_value=mock_chain)
            result = await node(state)

        assert result["messages"][0].content == "I can help with that."
```

### Best Practices

1. **Mock at boundaries** - Mock the external interface, not internal implementation
2. **Use realistic test data** - Mocked responses should match real API contracts
3. **Test error paths** - Verify handling of failures, timeouts, invalid responses
4. **Avoid over-mocking** - If you're mocking 5+ things, reconsider the test scope
5. **Use fixtures** - Share common mock setups via `conftest.py`

---

## E2E Tests

### Definition
E2E (end-to-end) tests verify **complete workflows** with **real external systems**. They use testcontainers for databases and may use fake implementations for expensive services (like LLMs).

### Location
```
tests/e2e/
├── conftest.py                    # Real PostgreSQL via testcontainers
├── test_agent_workflow.py         # Agent with real DB, fake LLM
└── test_postgres_connection.py    # Database connectivity verification
```

### When to Write E2E Tests

**DO write E2E tests when:**
- Verifying data persists correctly in real database
- Testing complete user workflows end-to-end
- Validating system behavior that mocks cannot capture
- Testing critical paths that must work in production
- Verifying database migrations work correctly

**DO NOT write E2E tests when:**
- Testing can be done with mocks (use integration tests)
- Testing pure logic (use unit tests)
- Test would be flaky or slow without adding value

### E2E Test Strategy

```
┌─────────────────────────────────────────────────┐
│                   E2E Test                       │
│  ┌─────────────┐    ┌─────────────────────────┐ │
│  │ Fake LLM    │    │ Real PostgreSQL         │ │
│  │ (no API $)  │    │ (testcontainers)        │ │
│  └─────────────┘    └─────────────────────────┘ │
│         │                      │                 │
│         └──────────┬───────────┘                 │
│                    ▼                             │
│            ┌───────────────┐                     │
│            │  Real Agent   │                     │
│            │  Real Routes  │                     │
│            │  Real Repos   │                     │
│            └───────────────┘                     │
└─────────────────────────────────────────────────┘
```

### E2E Test Examples

```python
# GOOD: Real database, fake LLM
@pytest.mark.e2e
class TestAgentWorkflowWithRealDB:
    async def test_invoke_stores_conversation(
        self,
        db_checkpointer: AsyncPostgresSaver,  # Real PostgreSQL
        fake_llm: FakeChatModelForTests,      # Predictable responses
    ):
        """Agent invoke stores conversation in real database."""
        builder = KnowledgeAgentBuilder(
            checkpointer=db_checkpointer,
            ...
        )

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("...ChatLiteLLM", lambda **kwargs: fake_llm)
            agent = await builder.build()

            result = await agent.run(
                message="What is Python?",
                thread_id="test-thread-e2e-001",
            )

        # Verify response
        assert result.response is not None

        # Verify data persisted to real database
        config = {"configurable": {"thread_id": "test-thread-e2e-001"}}
        checkpoint = await db_checkpointer.aget_tuple(config)
        assert checkpoint is not None

    async def test_different_threads_are_isolated(self, ...):
        """Different thread_ids have isolated conversations."""
        # Test thread isolation with real database
        ...
```

### The Fake LLM Pattern

For E2E tests, we use a fake LLM to avoid API costs while still testing real workflows:

```python
class FakeChatModelForTests(BaseChatModel):
    """Fake chat model that returns predictable responses."""

    response_content: str = "This is a test response."

    def _generate(self, messages, **kwargs) -> ChatResult:
        ai_message = AIMessage(content=self.response_content)
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    def bind_tools(self, tools, **kwargs):
        return self  # No-op for testing
```

### Best Practices

1. **Use testcontainers** - Spin up real PostgreSQL for each test run
2. **Fake expensive services** - Use fake LLMs to avoid API costs
3. **Test critical paths only** - E2E tests are slow; be selective
4. **Clean up test data** - Use unique thread_ids, clean database between tests
5. **Mark with `@pytest.mark.e2e`** - Allow skipping in fast test runs

---

## Decision Heuristics

### Quick Decision Guide

| Question | Answer → Test Type |
|----------|-------------------|
| Is it a pure function with no I/O? | Unit |
| Does it parse, transform, or calculate? | Unit |
| Does it need a mocked database/HTTP/LLM? | Integration |
| Does it test component interactions? | Integration |
| Must it verify real database persistence? | E2E |
| Is it a critical user workflow? | E2E |

### Code Smell: Wrong Test Type

**Unit test that should be integration:**
```python
# BAD: Mocking database in a "unit" test
def test_user_creation(self):
    mock_db = AsyncMock()  # This signals integration test
    repo = UserRepository(db=mock_db)
    ...
```

**Integration test that should be unit:**
```python
# BAD: No mocks needed, pure logic
async def test_parse_json(self):
    result = parse_json('{"key": "value"}')
    assert result == {"key": "value"}
```

**Integration test that should be E2E:**
```python
# BAD: Testing with real database in integration
async def test_user_persists(self, real_postgres):
    repo = UserRepository(db=real_postgres)  # Real DB = E2E
    ...
```

---

## Running Tests

### By Test Type (Recommended)

```bash
make test-unit         # Unit tests only (fast, no external deps)
make test-integration  # Integration tests only (uses mocks)
make test-e2e          # E2E tests only (requires Docker)
```

### All Tests

```bash
make test              # All tests in CI container (requires Docker)
make check        # All tests locally (unit + integration + e2e)
```

### Other Options

```bash
make test-slow                    # Show 10 slowest tests
pytest tests/unit/ -v -k "parse"  # Filter by name pattern
pytest --cov=my_agentic_serviceservice_order_specialist   # With coverage report
```

---

## Checklist for New Tests

Before submitting a test, verify:

- [ ] Test is in the correct folder (`unit/`, `integration/`, or `e2e/`)
- [ ] Docstring accurately describes what type of test it is
- [ ] Unit tests have no mocks of external systems
- [ ] Integration tests use mocks/fakes, not real systems
- [ ] E2E tests are marked with `@pytest.mark.e2e`
- [ ] Test name describes the behavior being tested
- [ ] Test covers one logical assertion
- [ ] Edge cases are covered where applicable
