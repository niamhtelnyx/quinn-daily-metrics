"""Unit tests for LangGraph utility functions.

This module tests pure utility functions in langgraph.py:
- LangGraphMCPTools: Type conversion, name prefixing, schema building
- LangGraphMessageParser: Role extraction, content extraction, message conversion
"""

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from my_agentic_serviceservice_order_specialist.platform.agent.langgraph import (
    LangGraphMCPTools,
    LangGraphMessageParser,
)


class TestLangGraphMCPToolsJsonTypeConversion:
    """Tests for _json_type_to_python static method."""

    def test_string_type(self):
        """JSON 'string' maps to Python str."""
        assert LangGraphMCPTools._json_type_to_python("string") is str

    def test_integer_type(self):
        """JSON 'integer' maps to Python int."""
        assert LangGraphMCPTools._json_type_to_python("integer") is int

    def test_number_type(self):
        """JSON 'number' maps to Python float."""
        assert LangGraphMCPTools._json_type_to_python("number") is float

    def test_boolean_type(self):
        """JSON 'boolean' maps to Python bool."""
        assert LangGraphMCPTools._json_type_to_python("boolean") is bool

    def test_object_type(self):
        """JSON 'object' maps to Python dict."""
        assert LangGraphMCPTools._json_type_to_python("object") is dict

    def test_array_type(self):
        """JSON 'array' maps to Python list."""
        assert LangGraphMCPTools._json_type_to_python("array") is list

    def test_unknown_type_defaults_to_str(self):
        """Unknown types default to str."""
        assert LangGraphMCPTools._json_type_to_python("unknown") is str
        assert LangGraphMCPTools._json_type_to_python("custom") is str
        assert LangGraphMCPTools._json_type_to_python("") is str


class TestLangGraphMCPToolsPrefixedName:
    """Tests for _prefixed_name method."""

    def test_no_prefix(self):
        """Without tool_prefix, only mcp_ prefix is added."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        tools = LangGraphMCPTools(mcp_client=mock_client, tool_prefix=None)
        assert tools._prefixed_name("search") == "mcp_search"
        assert tools._prefixed_name("read_file") == "mcp_read_file"

    def test_with_prefix(self):
        """With tool_prefix, both prefixes are applied."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        tools = LangGraphMCPTools(mcp_client=mock_client, tool_prefix="github")
        assert tools._prefixed_name("search") == "mcp_github_search"
        assert tools._prefixed_name("create_issue") == "mcp_github_create_issue"

    def test_empty_prefix_treated_as_none(self):
        """Empty string prefix is falsy, so only mcp_ is added."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        tools = LangGraphMCPTools(mcp_client=mock_client, tool_prefix="")
        assert tools._prefixed_name("tool") == "mcp_tool"


class TestLangGraphMCPToolsBuildArgsSchema:
    """Tests for _build_args_schema class method."""

    def test_no_input_schema(self):
        """Tool without inputSchema returns None."""
        from unittest.mock import MagicMock

        mock_tool = MagicMock()
        del mock_tool.inputSchema  # Remove the attribute
        assert LangGraphMCPTools._build_args_schema(mock_tool) is None

    def test_empty_input_schema(self):
        """Tool with empty inputSchema returns None."""
        from unittest.mock import MagicMock

        mock_tool = MagicMock()
        mock_tool.inputSchema = {}
        assert LangGraphMCPTools._build_args_schema(mock_tool) is None

    def test_schema_without_properties(self):
        """Schema without properties returns None."""
        from unittest.mock import MagicMock

        mock_tool = MagicMock()
        mock_tool.inputSchema = {"type": "object"}
        assert LangGraphMCPTools._build_args_schema(mock_tool) is None

    def test_schema_with_empty_properties(self):
        """Schema with empty properties dict returns None."""
        from unittest.mock import MagicMock

        mock_tool = MagicMock()
        mock_tool.inputSchema = {"type": "object", "properties": {}}
        assert LangGraphMCPTools._build_args_schema(mock_tool) is None

    def test_simple_required_field(self):
        """Schema with required field creates proper model."""
        from unittest.mock import MagicMock

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        }

        schema = LangGraphMCPTools._build_args_schema(mock_tool)
        assert schema is not None
        assert "query" in schema.model_fields  # type: ignore[union-attr]

    def test_optional_field_with_default(self):
        """Optional fields get None as default."""
        from unittest.mock import MagicMock

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results"},
            },
            "required": [],
        }

        schema = LangGraphMCPTools._build_args_schema(mock_tool)
        assert schema is not None
        # Optional field should allow None
        instance = schema(limit=None)
        assert instance.limit is None

    def test_multiple_field_types(self):
        """Schema with multiple field types creates correct model."""
        from unittest.mock import MagicMock

        mock_tool = MagicMock()
        mock_tool.name = "complex_tool"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
                "score": {"type": "number"},
                "active": {"type": "boolean"},
            },
            "required": ["name"],
        }

        schema = LangGraphMCPTools._build_args_schema(mock_tool)
        assert schema is not None
        instance = schema(name="test", count=5, score=3.14, active=True)
        assert instance.name == "test"
        assert instance.count == 5
        assert instance.score == 3.14
        assert instance.active is True


class TestLangGraphMessageParserGetRole:
    """Tests for _get_role static method."""

    def test_system_message(self):
        """SystemMessage returns 'system' role."""
        msg = SystemMessage(content="You are a helpful assistant")
        assert LangGraphMessageParser._get_role(msg) == "system"

    def test_human_message(self):
        """HumanMessage returns 'user' role."""
        msg = HumanMessage(content="Hello")
        assert LangGraphMessageParser._get_role(msg) == "user"

    def test_ai_message(self):
        """AIMessage returns 'assistant' role."""
        msg = AIMessage(content="Hi there!")
        assert LangGraphMessageParser._get_role(msg) == "assistant"

    def test_tool_message(self):
        """ToolMessage returns 'tool' role."""
        msg = ToolMessage(content="Result", tool_call_id="123")
        assert LangGraphMessageParser._get_role(msg) == "tool"


class TestLangGraphMessageParserExtractContent:
    """Tests for _extract_content static method."""

    def test_string_content(self):
        """String content is returned as-is."""
        msg = AIMessage(content="Hello world")
        assert LangGraphMessageParser._extract_content(msg) == "Hello world"

    def test_empty_string_content(self):
        """Empty string content is returned as empty."""
        msg = AIMessage(content="")
        assert LangGraphMessageParser._extract_content(msg) == ""

    def test_list_content_with_text_dicts(self):
        """List content with text dicts is joined."""
        msg = AIMessage(content=[{"text": "Hello"}, {"text": "world"}])
        assert LangGraphMessageParser._extract_content(msg) == "Hello world"

    def test_list_content_with_mixed_items(self):
        """List content with mixed items converts non-dicts to strings."""
        msg = AIMessage(content=[{"text": "Hello"}, "raw string"])
        assert LangGraphMessageParser._extract_content(msg) == "Hello raw string"

    def test_list_content_without_text_key(self):
        """List content dicts without 'text' key use empty string."""
        msg = AIMessage(content=[{"type": "image"}, {"text": "caption"}])
        assert LangGraphMessageParser._extract_content(msg) == " caption"


class TestLangGraphMessageParserExtractResponse:
    """Tests for _extract_response method."""

    def test_single_ai_message(self):
        """Single AI message returns its content."""
        parser = LangGraphMessageParser()
        messages: list[BaseMessage] = [AIMessage(content="Final response")]
        assert parser._extract_response(messages) == "Final response"

    def test_multiple_messages_returns_last_ai(self):
        """Multiple messages returns last AI message without tool calls."""
        parser = LangGraphMessageParser()
        messages: list[BaseMessage] = [
            HumanMessage(content="Hello"),
            AIMessage(content="First response"),
            HumanMessage(content="Follow up"),
            AIMessage(content="Final response"),
        ]
        assert parser._extract_response(messages) == "Final response"

    def test_skips_ai_messages_with_tool_calls(self):
        """AI messages with tool calls are skipped."""
        parser = LangGraphMessageParser()
        messages: list[BaseMessage] = [
            AIMessage(
                content="",
                tool_calls=[{"id": "1", "name": "search", "args": {}}],
            ),
            ToolMessage(content="results", tool_call_id="1"),
            AIMessage(content="Here are the results"),
        ]
        assert parser._extract_response(messages) == "Here are the results"

    def test_empty_messages_returns_empty_string(self):
        """Empty message list returns empty string."""
        parser = LangGraphMessageParser()
        assert parser._extract_response([]) == ""

    def test_no_ai_messages_returns_empty_string(self):
        """No AI messages returns empty string."""
        parser = LangGraphMessageParser()
        messages: list[BaseMessage] = [HumanMessage(content="Hello")]
        assert parser._extract_response(messages) == ""

    def test_list_content_in_ai_message(self):
        """AI message with list content is handled."""
        parser = LangGraphMessageParser()
        messages: list[BaseMessage] = [AIMessage(content=[{"text": "Part 1"}, {"text": "Part 2"}])]
        assert parser._extract_response(messages) == "Part 1 Part 2"


class TestLangGraphMessageParserConvertMessages:
    """Tests for _convert_messages method."""

    def test_converts_single_message(self):
        """Single message is converted correctly."""
        parser = LangGraphMessageParser()
        messages: list[BaseMessage] = [HumanMessage(content="Hello")]
        converted = parser._convert_messages(messages)

        assert len(converted) == 1
        assert converted[0].role == "user"
        assert converted[0].content == "Hello"

    def test_converts_multiple_messages(self):
        """Multiple messages are converted in order."""
        parser = LangGraphMessageParser()
        messages: list[BaseMessage] = [
            SystemMessage(content="Be helpful"),
            HumanMessage(content="Hi"),
            AIMessage(content="Hello!"),
        ]
        converted = parser._convert_messages(messages)

        assert len(converted) == 3
        assert converted[0].role == "system"
        assert converted[1].role == "user"
        assert converted[2].role == "assistant"

    def test_extracts_tool_calls_from_ai_message(self):
        """Tool calls are extracted from AI messages."""
        parser = LangGraphMessageParser()
        messages: list[BaseMessage] = [
            AIMessage(
                content="Let me search",
                tool_calls=[
                    {"id": "call_1", "name": "search", "args": {"q": "test"}},
                ],
            ),
        ]
        converted = parser._convert_messages(messages)

        assert len(converted) == 1
        assert converted[0].tool_calls is not None
        assert len(converted[0].tool_calls) == 1
        assert converted[0].tool_calls[0]["name"] == "search"

    def test_extracts_tool_call_id_from_tool_message(self):
        """Tool call ID is extracted from tool messages."""
        parser = LangGraphMessageParser()
        messages: list[BaseMessage] = [ToolMessage(content="Result", tool_call_id="call_123")]
        converted = parser._convert_messages(messages)

        assert len(converted) == 1
        assert converted[0].tool_call_id == "call_123"


class TestLangGraphMessageParserToStreamEvent:
    """Tests for to_stream_event method."""

    def test_ai_message_without_tool_calls(self):
        """AI message without tool calls creates 'message' event."""
        parser = LangGraphMessageParser()
        # LangGraph astream returns events keyed by node name
        event = {"agent": {"messages": [AIMessage(content="Hello")]}}
        result = parser.to_stream_event(event)

        assert result.event_type == "message"
        assert result.data["content"] == "Hello"
        assert result.data["node"] == "agent"

    def test_ai_message_with_tool_calls(self):
        """AI message with tool calls creates 'tool_call' event."""
        parser = LangGraphMessageParser()
        event = {
            "agent": {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[{"id": "1", "name": "search", "args": {}}],
                    )
                ]
            }
        }
        result = parser.to_stream_event(event)

        assert result.event_type == "tool_call"
        assert "tool_calls" in result.data
        assert result.data["node"] == "agent"

    def test_tool_message_creates_tool_result_event(self):
        """Tool message creates 'tool_result' event."""
        parser = LangGraphMessageParser()
        event = {
            "tools": {
                "messages": [ToolMessage(content="Result", tool_call_id="123", name="search")]
            }
        }
        result = parser.to_stream_event(event)

        assert result.event_type == "tool_result"
        assert result.data["tool_call_id"] == "123"
        assert result.data["name"] == "search"
        assert result.data["node"] == "tools"

    def test_empty_event_creates_state_update(self):
        """Event without messages creates 'state_update' event."""
        parser = LangGraphMessageParser()
        event = {"reasoning_steps": 5}
        result = parser.to_stream_event(event)

        assert result.event_type == "state_update"
        assert result.data == event

    def test_empty_messages_list_creates_state_update(self):
        """Event with empty messages list creates 'state_update' event."""
        parser = LangGraphMessageParser()
        event = {"agent": {"messages": []}}
        result = parser.to_stream_event(event)

        assert result.event_type == "state_update"
