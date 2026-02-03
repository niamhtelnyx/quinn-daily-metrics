# Tests

This folder contains all tests for agentic-service-1A, organized by the testing pyramid.

> For comprehensive documentation, see [docs/TESTING.md](../docs/TESTING.md)

## Structure

```
tests/
├── unit/           # Pure functions, no external dependencies
├── integration/    # Component interfaces with mocks/fakes
└── e2e/            # Real workflows with real systems (containers)
```

## Quick Reference

| Folder | What to Test | External Systems | Speed |
|--------|--------------|------------------|-------|
| `unit/` | Pure functions, parsing, calculations | None | Fast |
| `integration/` | Component interfaces, error handling | Mocked | Medium |
| `e2e/` | Critical workflows, data persistence | Real (containers) | Slow |

## When to Use Each Type

### Unit (`tests/unit/`)
```python
# Pure function - no I/O, no side effects
def test_parse_config():
    config = AgentConfig(max_steps=5)
    assert config.max_steps == 5
```

### Integration (`tests/integration/`)
```python
# Mocked external system
async def test_repository_lists_items(mock_db_session):
    mock_db_session.execute.return_value = [...]
    repo = Repository(db=mock_db_session)
    result = await repo.list_items()
    assert len(result) == 1
```

### E2E (`tests/e2e/`)
```python
# Real database via testcontainers
@pytest.mark.e2e
async def test_data_persists(postgres_db):
    repo = Repository(db=postgres_db)
    await repo.create(item)
    retrieved = await repo.get(item.id)
    assert retrieved is not None
```

## Running Tests

```bash
# All checks locally (style, lint, types, tests)
make check

# By type (recommended)
make test-unit         # Unit tests only (fast)
make test-integration  # Integration tests only
make test-e2e          # E2E tests only (requires Docker)

# All tests in Docker (CI-like)
make docker-integrate  # Run all tests in Docker container
make test              # Alias for docker-integrate
```

## Decision Flowchart

```
Is the function pure (no I/O)?
├─ YES → tests/unit/
└─ NO → Need real external system?
         ├─ YES → tests/e2e/
         └─ NO (can mock) → tests/integration/
```
