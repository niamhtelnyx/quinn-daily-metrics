# E2E Tests

Tests for **complete workflows** with real external systems.

## Criteria

A test belongs here if:
- Tests critical user workflows end-to-end
- Requires real database to verify persistence
- Validates behavior that mocks cannot capture
- Tests real system integration (not just interfaces)

## What Belongs Here

- Agent workflows with real database persistence
- Conversation thread isolation verification
- Database connection and migration tests
- Multi-step workflows that must work in production

## What Does NOT Belong Here

- Tests that can be done with mocks (use `integration/`)
- Pure function tests (use `unit/`)
- Tests that would be flaky without real value

## Test Strategy

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

**Real systems:** PostgreSQL via testcontainers
**Fake systems:** LLM (to avoid API costs and ensure determinism)

## The Fake LLM Pattern

```python
class FakeChatModelForTests(BaseChatModel):
    """Returns predictable responses without API calls."""

    response_content: str = "This is a test response."

    def _generate(self, messages, **kwargs) -> ChatResult:
        ai_message = AIMessage(content=self.response_content)
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    def bind_tools(self, tools, **kwargs):
        return self
```

## Examples

```python
@pytest.mark.e2e
class TestAgentWorkflowWithRealDB:
    async def test_invoke_stores_conversation(
        self,
        db_checkpointer: AsyncPostgresSaver,  # Real PostgreSQL
        fake_llm: FakeChatModelForTests,
    ):
        """Verify conversation persists to real database."""
        builder = KnowledgeAgentBuilder(
            checkpointer=db_checkpointer,
            ...
        )

        # Patch LLM to use fake
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("...ChatLiteLLM", lambda **kw: fake_llm)
            agent = await builder.build()
            result = await agent.run(message="Hello", thread_id="test-001")

        # Verify persisted to real database
        checkpoint = await db_checkpointer.aget_tuple(config)
        assert checkpoint is not None

    async def test_threads_are_isolated(self, ...):
        """Different thread_ids have separate conversations."""
        # Thread A and Thread B should not share data
        ...
```

## Fixtures

Defined in `conftest.py`:
- `postgres_db` - Real PostgreSQL via testcontainers
- `db_checkpointer` - AsyncPostgresSaver connected to real DB
- `fake_llm` - Predictable LLM responses

## Marker

All E2E tests must be marked:

```python
@pytest.mark.e2e
class TestWorkflow:
    ...
```

This allows skipping E2E tests in fast runs:
```bash
pytest -m "not e2e"  # Skip E2E tests
```

## Running

```bash
# Requires Docker for testcontainers
pytest tests/e2e/ -v -m e2e

# Or via make
make test-e2e
```

## Best Practices

1. **Use unique identifiers** - Each test should use unique thread_ids
2. **Keep tests focused** - Test one critical path per test
3. **Clean test data** - Database is fresh per test run (container)
4. **Mark all tests** - Always use `@pytest.mark.e2e`
5. **Be selective** - Only test what requires real systems
