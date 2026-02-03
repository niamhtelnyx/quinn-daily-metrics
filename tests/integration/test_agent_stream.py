"""Integration tests for agent streaming flow.

Tests the complete streaming flow from LangGraphAgent through to StreamEvent,
with mocked LLM responses to simulate real streaming behavior.
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage

from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentIdentity
from my_agentic_serviceservice_order_specialist.platform.agent.langgraph import LangGraphAgent
from my_agentic_serviceservice_order_specialist.platform.agent.messages import StreamEvent


class TestAgentStreamFlow:
    """E2E tests for complete agent streaming flow."""

    @pytest.fixture
    def agent(
        self,
        stub_streaming_graph: Mock,
        stub_identity: AgentIdentity,
        initial_state_builder,
    ) -> LangGraphAgent:
        """Create a LangGraphAgent with mocked streaming graph."""
        return LangGraphAgent(
            graph=stub_streaming_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

    async def test_stream_yields_events(self, agent: LangGraphAgent):
        """run_stream yields StreamEvent objects."""
        events = []
        async for event in agent.run_stream(
            message="What is Python?",
            thread_id="test-thread-123",
        ):
            events.append(event)

        assert len(events) == 3
        assert all(isinstance(e, StreamEvent) for e in events)

    async def test_stream_events_contain_data(self, agent: LangGraphAgent):
        """StreamEvent objects contain event data."""
        events = []
        async for event in agent.run_stream(
            message="What is Python?",
            thread_id="test-thread-123",
        ):
            events.append(event)

        for event in events:
            assert event.data is not None

    async def test_stream_events_have_event_type(self, agent: LangGraphAgent):
        """StreamEvent objects have event_type."""
        events = []
        async for event in agent.run_stream(
            message="What is Python?",
            thread_id="test-thread-123",
        ):
            events.append(event)

        for event in events:
            assert event.event_type is not None

    async def test_stream_preserves_message_order(self, agent: LangGraphAgent):
        """Stream events are yielded in order."""
        contents = []
        async for event in agent.run_stream(
            message="What is Python?",
            thread_id="test-thread-123",
        ):
            # Extract content from parsed message events
            if event.event_type == "message" and event.data.get("content"):
                contents.append(event.data["content"])

        assert contents == ["Thinking...", "Processing...", "Final answer."]


class TestAgentStreamWithTools:
    """E2E tests for agent streaming with tool calls."""

    @pytest.fixture
    def stub_stream_with_tools(self) -> list[dict]:
        """Create stub stream events including tool calls."""
        # Create a message with tool calls
        msg_with_tools = AIMessage(content="Let me search for that.")
        msg_with_tools.tool_calls = [
            {"name": "search", "args": {"query": "Python"}, "id": "call_123"}
        ]

        return [
            {"reasoner": {"messages": [msg_with_tools]}},
            {"tools": {"messages": [AIMessage(content="Search results...")]}},
            {"reasoner": {"messages": [AIMessage(content="Based on my search...")]}},
        ]

    @pytest.fixture
    def stub_graph_with_tools(self, stub_stream_with_tools: list[dict]) -> Mock:
        """Create a stub graph that yields canned tool events."""
        graph = Mock()

        async def stream_generator(*args, **kwargs):
            for event in stub_stream_with_tools:
                yield event

        graph.astream = stream_generator
        return graph

    async def test_stream_includes_tool_events(
        self,
        stub_graph_with_tools: Mock,
        stub_identity: AgentIdentity,
        initial_state_builder,
    ):
        """Stream includes events from tool execution."""
        agent = LangGraphAgent(
            graph=stub_graph_with_tools,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        events = []
        async for event in agent.run_stream(
            message="Search for Python",
            thread_id="test-thread",
        ):
            events.append(event)

        assert len(events) == 3

    async def test_stream_tool_calls_in_data(
        self,
        stub_graph_with_tools: Mock,
        stub_identity: AgentIdentity,
        initial_state_builder,
    ):
        """Stream events contain tool call information."""
        agent = LangGraphAgent(
            graph=stub_graph_with_tools,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        events = []
        async for event in agent.run_stream(
            message="Search for Python",
            thread_id="test-thread",
        ):
            events.append(event)

        # First event should have tool calls (parsed by to_stream_event)
        first_event = events[0]
        assert first_event.event_type == "tool_call"
        assert "tool_calls" in first_event.data
        assert len(first_event.data["tool_calls"]) > 0


class TestAgentStreamEdgeCases:
    """E2E tests for agent streaming edge cases."""

    async def test_stream_empty_response(self, stub_identity: AgentIdentity, initial_state_builder):
        """Stream handles empty graph response."""
        mock_graph = Mock()

        async def mock_astream(*args, **kwargs):
            # Empty async generator
            if False:  # type: ignore[unreachable]
                yield

        mock_graph.astream = mock_astream

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        events = []
        async for event in agent.run_stream(
            message="Hello",
            thread_id="test-thread",
        ):
            events.append(event)

        assert events == []

    async def test_stream_single_event(self, stub_identity: AgentIdentity, initial_state_builder):
        """Stream works with single event."""
        mock_graph = Mock()

        async def mock_astream(*args, **kwargs):
            yield {"reasoner": {"messages": [AIMessage(content="Quick response")]}}

        mock_graph.astream = mock_astream

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        events = []
        async for event in agent.run_stream(
            message="Hello",
            thread_id="test-thread",
        ):
            events.append(event)

        assert len(events) == 1

    async def test_stream_with_utc_now(self, stub_identity: AgentIdentity):
        """Stream passes utc_now to state builder."""
        state_builder = Mock(
            return_value={
                "messages": [],
                "reasoning_steps": 0,
                "thread_id": "test",
                "input_tokens_by_model": {},
                "output_tokens_by_model": {},
            }
        )

        mock_graph = Mock()

        async def mock_astream(*args, **kwargs):
            yield {"reasoner": {"messages": [AIMessage(content="Response")]}}

        mock_graph.astream = mock_astream

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=state_builder,
        )

        utc_now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
        async for _ in agent.run_stream(
            message="Hello",
            thread_id="test-thread",
            utc_now=utc_now,
        ):
            pass

        call_kwargs = state_builder.call_args[1]
        assert call_kwargs["utc_now"] == utc_now
