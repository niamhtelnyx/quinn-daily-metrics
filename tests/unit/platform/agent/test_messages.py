"""Unit tests for framework-agnostic message types.

This module tests the Message, ExecutionResult, and StreamEvent dataclasses.
"""

import pytest

from my_agentic_serviceservice_order_specialist.platform.agent.messages import (
    ExecutionResult,
    Message,
    StreamEvent,
)


class TestMessage:
    """Tests for Message dataclass."""

    def test_create_with_required_fields(self):
        """Can create message with role and content."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_tool_calls_defaults_to_none(self):
        """tool_calls defaults to None."""
        msg = Message(role="assistant", content="Response")
        assert msg.tool_calls is None

    def test_tool_call_id_defaults_to_none(self):
        """tool_call_id defaults to None."""
        msg = Message(role="tool", content="Result")
        assert msg.tool_call_id is None

    def test_name_defaults_to_none(self):
        """name defaults to None."""
        msg = Message(role="tool", content="Result")
        assert msg.name is None

    def test_can_set_tool_calls(self):
        """tool_calls can be explicitly set."""
        tool_calls = [{"id": "call_1", "name": "search", "args": {"q": "test"}}]
        msg = Message(role="assistant", content="", tool_calls=tool_calls)
        assert msg.tool_calls == tool_calls

    def test_can_set_tool_call_id(self):
        """tool_call_id can be explicitly set."""
        msg = Message(role="tool", content="Result", tool_call_id="call_123")
        assert msg.tool_call_id == "call_123"

    def test_can_set_name(self):
        """name can be explicitly set."""
        msg = Message(role="tool", content="Result", name="search")
        assert msg.name == "search"

    def test_is_frozen(self):
        """Message is immutable (frozen)."""
        msg = Message(role="user", content="Hello")
        with pytest.raises(AttributeError):
            msg.role = "assistant"  # type: ignore[misc]

    def test_is_frozen_content(self):
        """content attribute is also immutable."""
        msg = Message(role="user", content="Hello")
        with pytest.raises(AttributeError):
            msg.content = "Changed"  # type: ignore[misc]

    def test_system_role(self):
        """Can create system message."""
        msg = Message(role="system", content="Be helpful")
        assert msg.role == "system"

    def test_assistant_role(self):
        """Can create assistant message."""
        msg = Message(role="assistant", content="Hi there!")
        assert msg.role == "assistant"

    def test_tool_role(self):
        """Can create tool message."""
        msg = Message(role="tool", content="Result", tool_call_id="123", name="search")
        assert msg.role == "tool"
        assert msg.tool_call_id == "123"
        assert msg.name == "search"

    def test_empty_content(self):
        """Can create message with empty content."""
        msg = Message(role="assistant", content="")
        assert msg.content == ""

    def test_multiple_tool_calls(self):
        """Can have multiple tool calls."""
        tool_calls = [
            {"id": "call_1", "name": "search", "args": {}},
            {"id": "call_2", "name": "fetch", "args": {}},
        ]
        msg = Message(role="assistant", content="", tool_calls=tool_calls)
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 2


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_create_with_required_fields(self):
        """Can create result with required fields."""
        result = ExecutionResult(
            response="Hello",
            messages=[Message(role="assistant", content="Hello")],
            reasoning_steps=1,
            thread_id="thread-123",
        )
        assert result.response == "Hello"
        assert result.reasoning_steps == 1
        assert result.thread_id == "thread-123"

    def test_messages_stored(self):
        """messages list is stored correctly."""
        msgs = [
            Message(role="user", content="Hi"),
            Message(role="assistant", content="Hello"),
        ]
        result = ExecutionResult(
            response="Hello",
            messages=msgs,
            reasoning_steps=1,
            thread_id="thread-123",
        )
        assert len(result.messages) == 2
        assert result.messages[0].role == "user"
        assert result.messages[1].role == "assistant"

    def test_metadata_defaults_to_empty_dict(self):
        """metadata defaults to empty dict."""
        result = ExecutionResult(
            response="Response",
            messages=[],
            reasoning_steps=0,
            thread_id="thread-1",
        )
        assert result.metadata == {}

    def test_can_set_metadata(self):
        """metadata can be explicitly set."""
        result = ExecutionResult(
            response="Response",
            messages=[],
            reasoning_steps=0,
            thread_id="thread-1",
            metadata={"model": "gpt-4", "tokens": 100},
        )
        assert result.metadata["model"] == "gpt-4"
        assert result.metadata["tokens"] == 100

    def test_is_frozen(self):
        """ExecutionResult is immutable (frozen)."""
        result = ExecutionResult(
            response="Response",
            messages=[],
            reasoning_steps=0,
            thread_id="thread-1",
        )
        with pytest.raises(AttributeError):
            result.response = "Changed"  # type: ignore[misc]

    def test_is_frozen_reasoning_steps(self):
        """reasoning_steps is immutable."""
        result = ExecutionResult(
            response="Response",
            messages=[],
            reasoning_steps=5,
            thread_id="thread-1",
        )
        with pytest.raises(AttributeError):
            result.reasoning_steps = 10  # type: ignore[misc]

    def test_is_frozen_thread_id(self):
        """thread_id is immutable."""
        result = ExecutionResult(
            response="Response",
            messages=[],
            reasoning_steps=0,
            thread_id="thread-1",
        )
        with pytest.raises(AttributeError):
            result.thread_id = "thread-2"  # type: ignore[misc]

    def test_zero_reasoning_steps(self):
        """Can have zero reasoning steps."""
        result = ExecutionResult(
            response="Response",
            messages=[],
            reasoning_steps=0,
            thread_id="thread-1",
        )
        assert result.reasoning_steps == 0

    def test_empty_messages_list(self):
        """Can have empty messages list."""
        result = ExecutionResult(
            response="Response",
            messages=[],
            reasoning_steps=0,
            thread_id="thread-1",
        )
        assert result.messages == []

    def test_empty_response(self):
        """Can have empty response string."""
        result = ExecutionResult(
            response="",
            messages=[],
            reasoning_steps=0,
            thread_id="thread-1",
        )
        assert result.response == ""


class TestStreamEvent:
    """Tests for StreamEvent dataclass."""

    def test_create_with_required_fields(self):
        """Can create event with type and data."""
        event = StreamEvent(event_type="message", data={"content": "Hello"})
        assert event.event_type == "message"
        assert event.data == {"content": "Hello"}

    def test_message_event_type(self):
        """Can create message event."""
        event = StreamEvent(event_type="message", data={"content": "Hello"})
        assert event.event_type == "message"

    def test_tool_call_event_type(self):
        """Can create tool_call event."""
        event = StreamEvent(
            event_type="tool_call",
            data={"tool_calls": [{"id": "1", "name": "search"}]},
        )
        assert event.event_type == "tool_call"

    def test_tool_result_event_type(self):
        """Can create tool_result event."""
        event = StreamEvent(
            event_type="tool_result",
            data={"tool_call_id": "123", "result": "data"},
        )
        assert event.event_type == "tool_result"

    def test_done_event_type(self):
        """Can create done event."""
        event = StreamEvent(event_type="done", data={"final": True})
        assert event.event_type == "done"

    def test_error_event_type(self):
        """Can create error event."""
        event = StreamEvent(event_type="error", data={"error": "Something failed"})
        assert event.event_type == "error"

    def test_is_frozen(self):
        """StreamEvent is immutable (frozen)."""
        event = StreamEvent(event_type="message", data={})
        with pytest.raises(AttributeError):
            event.event_type = "error"  # type: ignore[misc]

    def test_is_frozen_data(self):
        """data attribute is immutable."""
        event = StreamEvent(event_type="message", data={})
        with pytest.raises(AttributeError):
            event.data = {"new": "data"}  # type: ignore[misc]

    def test_empty_data(self):
        """Can have empty data dict."""
        event = StreamEvent(event_type="state_update", data={})
        assert event.data == {}

    def test_nested_data(self):
        """Can have nested data structures."""
        event = StreamEvent(
            event_type="tool_call",
            data={
                "tool_calls": [
                    {"id": "1", "name": "search", "args": {"query": "test"}},
                    {"id": "2", "name": "fetch", "args": {"url": "http://example.com"}},
                ]
            },
        )
        assert len(event.data["tool_calls"]) == 2
        assert event.data["tool_calls"][0]["args"]["query"] == "test"

    def test_custom_event_type(self):
        """Can create custom event types."""
        event = StreamEvent(event_type="custom_event", data={"custom": True})
        assert event.event_type == "custom_event"
