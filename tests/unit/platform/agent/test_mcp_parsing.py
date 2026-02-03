"""Unit tests for MCPClient result parsing methods.

Tests for pure JSON parsing logic: _parse_result, _parse_content.
These tests do not require network or external systems.
"""

from typing import Any
from unittest.mock import Mock

import pytest

from my_agentic_serviceservice_order_specialist.platform.agent.mcp import MCPClient


class TestMCPClientParseResult:
    """Tests for MCPClient result parsing methods."""

    def test_parse_result_empty_content(self):
        """Empty content returns None."""
        client = MCPClient(server_url="http://localhost:8000/mcp")
        result = Mock()
        result.content = []
        assert client._parse_result(result) is None

    def test_parse_result_single_item(self):
        """Single content item is returned directly."""
        client = MCPClient(server_url="http://localhost:8000/mcp")
        result = Mock()
        result.content = [Mock(text='{"key": "value"}')]
        parsed = client._parse_result(result)
        assert parsed == {"key": "value"}

    def test_parse_result_multiple_items(self):
        """Multiple content items are returned as list."""
        client = MCPClient(server_url="http://localhost:8000/mcp")
        result = Mock()
        result.content = [Mock(text='"item1"'), Mock(text='"item2"')]
        parsed = client._parse_result(result)
        assert parsed == ["item1", "item2"]


class TestMCPClientParseContent:
    """Tests for _parse_content method."""

    @pytest.mark.parametrize(
        ("input_text", "expected"),
        [
            ('{"key": "value"}', {"key": "value"}),  # Valid JSON object
            ("[1, 2, 3]", [1, 2, 3]),  # Valid JSON array
            ('"string"', "string"),  # Valid JSON string
            ("123", 123),  # Valid JSON number
            ("true", True),  # Valid JSON boolean
            ("null", None),  # Valid JSON null
            ("Not valid JSON", "Not valid JSON"),  # Invalid JSON returns raw
            ("{malformed", "{malformed"),  # Malformed JSON returns raw
        ],
    )
    def test_parse_content_json_handling(self, input_text: str, expected: Any):
        """Parses valid JSON or returns raw text for invalid JSON."""
        client = MCPClient(server_url="http://localhost:8000/mcp")
        content = Mock(text=input_text)
        assert client._parse_content(content) == expected

    def test_parse_content_without_text_attr(self):
        """Content without text attribute uses str()."""
        client = MCPClient(server_url="http://localhost:8000/mcp")

        class ContentWithoutText:
            def __str__(self) -> str:
                return "string representation"

        content = ContentWithoutText()
        result = client._parse_content(content)
        assert result == "string representation"
