# Unit Tests

Tests for **pure functions** with no external dependencies.

## Criteria

A test belongs here if:
- Function has no I/O (no database, HTTP, file system)
- Function has no side effects (no state mutation)
- Function takes inputs and returns outputs deterministically
- No mocking of external systems is required

## What Belongs Here

- Configuration parsing and validation
- Data transformations and calculations
- Token extraction and accumulation
- JSON/text parsing utilities
- Message formatting logic
- Validation functions

## What Does NOT Belong Here

- Tests requiring `AsyncMock` for database sessions
- Tests requiring `respx` for HTTP mocking
- Tests requiring mocked LLM responses
- Any test that needs external system fakes

## Examples

```python
# GOOD: Pure calculation
def test_pagination_offset():
    pagination = Pagination(page=3, page_size=10)
    assert pagination.offset == 20

# GOOD: Pure parsing
def test_parse_content_valid_json():
    result = client._parse_content(Mock(text='{"key": "value"}'))
    assert result == {"key": "value"}

# BAD: Requires mocked external system (move to integration/)
async def test_repository_query(mock_session):
    ...
```

## Use `pytest.mark.parametrize`

When testing multiple inputs with the same logic, use parametrization:

```python
# Instead of 4 separate tests, use parametrize:
@pytest.mark.parametrize(
    ("page", "page_size", "expected_offset"),
    [
        (1, 20, 0),
        (2, 20, 20),
        (3, 10, 20),
        (5, 25, 100),
    ],
)
def test_offset_calculation(self, page, page_size, expected_offset):
    pagination = Pagination(page=page, page_size=page_size)
    assert pagination.offset == expected_offset
```

**Heuristics:**
- 3+ similar tests → parametrize
- Same assertion, different inputs → parametrize
- Different setup/assertions → keep separate

## Running

```bash
pytest tests/unit/ -v
pytest tests/unit/ -v --tb=short  # Compact output
```
