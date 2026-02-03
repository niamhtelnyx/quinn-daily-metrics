"""Unit tests for the inspect_artifact tool.

This module tests the artifact inspection logic including:
- Artifact lookup from state
- JSON data handling with JMESPath
- Text data handling with search/slice/match commands
- Error handling
"""

from typing import Any

import pytest
from langchain_core.messages import HumanMessage, ToolMessage

from my_agentic_serviceservice_order_specialist.agents.knowledge.tools.inspect_artifact import (
    create_inspect_artifact_tool,
)


@pytest.fixture
def inspect_tool():
    """Create the inspect_artifact tool for testing."""
    return create_inspect_artifact_tool()


def make_state_with_artifact(artifact_id: str, data: Any) -> dict:
    """Helper to create state with an artifact in message history."""
    return {
        "messages": [
            HumanMessage(content="test"),
            ToolMessage(
                content="Hidden content",
                tool_call_id="call_1",
                artifact={"id": artifact_id, "data": data},
            ),
        ]
    }


class TestArtifactLookup:
    """Tests for artifact lookup from state."""

    def test_artifact_not_found(self, inspect_tool):
        """Missing artifact returns error message."""
        state = {"messages": [HumanMessage(content="test")]}
        result = inspect_tool.invoke({"artifact_id": "missing", "query": "keys", "state": state})
        assert "Error: Artifact 'missing' not found" in result

    def test_artifact_found_by_id(self, inspect_tool):
        """Artifact is found by matching ID."""
        state = make_state_with_artifact("art_123", {"name": "test"})
        result = inspect_tool.invoke({"artifact_id": "art_123", "query": "keys", "state": state})
        assert "Keys:" in result
        assert "name" in result

    def test_searches_messages_in_reverse(self, inspect_tool):
        """Most recent artifact with matching ID is used."""
        state = {
            "messages": [
                ToolMessage(
                    content="old",
                    tool_call_id="call_1",
                    artifact={"id": "art_1", "data": {"version": "old"}},
                ),
                ToolMessage(
                    content="new",
                    tool_call_id="call_2",
                    artifact={"id": "art_1", "data": {"version": "new"}},
                ),
            ]
        }
        result = inspect_tool.invoke({"artifact_id": "art_1", "query": "version", "state": state})
        assert "new" in result


class TestJsonDataHandling:
    """Tests for JSON data with JMESPath queries."""

    def test_keys_query_on_dict(self, inspect_tool):
        """'keys' query returns dictionary keys."""
        state = make_state_with_artifact("art_1", {"name": "test", "count": 5, "active": True})
        result = inspect_tool.invoke({"artifact_id": "art_1", "query": "keys", "state": state})
        assert "Keys:" in result
        assert "name" in result
        assert "count" in result
        assert "active" in result

    def test_simple_field_access(self, inspect_tool):
        """Simple field access returns field value."""
        state = make_state_with_artifact("art_1", {"name": "Alice", "age": 30})
        result = inspect_tool.invoke({"artifact_id": "art_1", "query": "name", "state": state})
        assert "Alice" in result

    def test_nested_field_access(self, inspect_tool):
        """Nested field access works with dot notation."""
        state = make_state_with_artifact("art_1", {"user": {"profile": {"name": "Bob"}}})
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "user.profile.name", "state": state}
        )
        assert "Bob" in result

    def test_array_index_access(self, inspect_tool):
        """Array index access works."""
        state = make_state_with_artifact("art_1", {"items": ["a", "b", "c"]})
        result = inspect_tool.invoke({"artifact_id": "art_1", "query": "items[0]", "state": state})
        assert "a" in result

    def test_array_wildcard_projection(self, inspect_tool):
        """Array wildcard projection extracts fields."""
        state = make_state_with_artifact(
            "art_1",
            {"users": [{"name": "Alice"}, {"name": "Bob"}]},
        )
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "users[*].name", "state": state}
        )
        assert "Alice" in result
        assert "Bob" in result

    def test_invalid_jmespath_query(self, inspect_tool):
        """Invalid JMESPath query returns error."""
        state = make_state_with_artifact("art_1", {"name": "test"})
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "[[[invalid", "state": state}
        )
        assert "Error: Invalid JMESPath query" in result

    def test_no_result_for_query(self, inspect_tool):
        """Query with no match returns appropriate message."""
        state = make_state_with_artifact("art_1", {"name": "test"})
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "nonexistent", "state": state}
        )
        assert "No result found" in result

    def test_json_in_string_is_parsed(self, inspect_tool):
        """JSON string data is automatically parsed."""
        state = make_state_with_artifact("art_1", '{"name": "test", "value": 42}')
        result = inspect_tool.invoke({"artifact_id": "art_1", "query": "name", "state": state})
        assert "test" in result

    def test_search_command_rejected_for_json(self, inspect_tool):
        """Text search commands are rejected for JSON data."""
        state = make_state_with_artifact("art_1", {"name": "test"})
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "search:test", "state": state}
        )
        assert "Error: This artifact is JSON" in result
        assert "JMESPath" in result

    def test_large_result_is_truncated(self, inspect_tool):
        """Results larger than 2000 chars are truncated."""
        large_data = {"items": [{"id": i, "data": "x" * 100} for i in range(50)]}
        state = make_state_with_artifact("art_1", large_data)
        result = inspect_tool.invoke({"artifact_id": "art_1", "query": "items", "state": state})
        assert "Result too long" in result
        assert "Preview:" in result


class TestTextDataHandling:
    """Tests for text data with search/slice/match commands."""

    def test_search_finds_matching_lines(self, inspect_tool):
        """search: command finds lines containing term."""
        text_data = "line 1: hello\nline 2: world\nline 3: hello world"
        state = make_state_with_artifact("art_1", text_data)
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "search:hello", "state": state}
        )
        assert "Found 2 matches" in result
        assert "Line 0" in result
        assert "Line 2" in result

    def test_search_case_insensitive(self, inspect_tool):
        """search: is case insensitive."""
        text_data = "ERROR occurred\nerror again\nERROR!"
        state = make_state_with_artifact("art_1", text_data)
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "search:error", "state": state}
        )
        assert "Found 3 matches" in result

    def test_search_no_matches(self, inspect_tool):
        """search: with no matches returns appropriate message."""
        text_data = "line 1\nline 2\nline 3"
        state = make_state_with_artifact("art_1", text_data)
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "search:notfound", "state": state}
        )
        assert "No matches found" in result

    def test_slice_extracts_line_range(self, inspect_tool):
        """slice: command extracts line range."""
        text_data = "line 0\nline 1\nline 2\nline 3\nline 4"
        state = make_state_with_artifact("art_1", text_data)
        result = inspect_tool.invoke({"artifact_id": "art_1", "query": "slice:1:3", "state": state})
        assert "line 1" in result
        assert "line 2" in result
        assert "line 0" not in result
        assert "line 3" not in result

    def test_slice_invalid_format(self, inspect_tool):
        """slice: with invalid format returns error."""
        text_data = "line 1\nline 2"
        state = make_state_with_artifact("art_1", text_data)
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "slice:invalid", "state": state}
        )
        assert "Error: Invalid slice" in result

    def test_match_regex_pattern(self, inspect_tool):
        """match: command uses regex pattern."""
        text_data = "2023-01-15 INFO start\n2023-01-15 ERROR fail\n2023-01-16 INFO ok"
        state = make_state_with_artifact("art_1", text_data)
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "match:^2023-01-15", "state": state}
        )
        assert "Found 2 regex matches" in result

    def test_match_invalid_regex(self, inspect_tool):
        """match: with invalid regex returns error."""
        text_data = "test data"
        state = make_state_with_artifact("art_1", text_data)
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "match:[invalid", "state": state}
        )
        assert "Error: Invalid Regex pattern" in result

    def test_unknown_text_command_returns_error(self, inspect_tool):
        """Unknown command on text data returns helpful error."""
        text_data = "plain text data"
        state = make_state_with_artifact("art_1", text_data)
        result = inspect_tool.invoke({"artifact_id": "art_1", "query": "unknown", "state": state})
        assert "Error: Artifact is text" in result
        assert "search:" in result
        assert "slice:" in result
        assert "match:" in result


class TestJsonStringDetection:
    """Tests for JSON-in-string detection."""

    def test_json_object_string_parsed(self, inspect_tool):
        """String starting with { is parsed as JSON."""
        state = make_state_with_artifact("art_1", '{"key": "value"}')
        result = inspect_tool.invoke({"artifact_id": "art_1", "query": "key", "state": state})
        assert "value" in result

    def test_json_array_string_parsed(self, inspect_tool):
        """String starting with [ is parsed as JSON."""
        state = make_state_with_artifact("art_1", '["a", "b", "c"]')
        result = inspect_tool.invoke({"artifact_id": "art_1", "query": "[0]", "state": state})
        assert "a" in result

    def test_invalid_json_string_treated_as_text(self, inspect_tool):
        """Invalid JSON string is treated as plain text."""
        state = make_state_with_artifact("art_1", "{invalid json}")
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "search:invalid", "state": state}
        )
        assert "Found 1 matches" in result

    def test_text_command_on_json_string_skips_parsing(self, inspect_tool):
        """Text commands on JSON-like strings skip JSON parsing."""
        # When using search:, the JSON parsing is skipped
        state = make_state_with_artifact("art_1", '{"error": "test"}')
        result = inspect_tool.invoke(
            {"artifact_id": "art_1", "query": "search:error", "state": state}
        )
        assert "Found 1 matches" in result
