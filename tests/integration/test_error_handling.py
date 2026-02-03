"""Integration tests for agent error handling.

Tests error handling scenarios including timeouts, MCP server failures,
and LLM errors.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentIdentity
from my_agentic_serviceservice_order_specialist.platform.agent.langgraph import LangGraphAgent
from my_agentic_serviceservice_order_specialist.platform.agent.mcp import MCPClientError


class TestMCPServerUnavailable:
    """E2E tests for MCP server unavailability."""

    async def test_mcp_client_error_propagates(self):
        """MCPClientError propagates with meaningful message."""
        error = MCPClientError("Failed to connect to MCP server")

        assert "Failed to connect" in str(error)
        assert isinstance(error, Exception)

    async def test_agent_with_failed_tool_call(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """Agent handles failed tool calls gracefully."""
        mock_graph = Mock()

        # Simulate a response where tool call failed but agent recovered
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "messages": [
                    HumanMessage(content="Search for Python"),
                    AIMessage(content="I encountered an error accessing the tool."),
                ],
                "reasoning_steps": 1,
                "thread_id": "test",
                "input_tokens_by_model": {},
                "output_tokens_by_model": {},
            }
        )

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        result = await agent.run(message="Search for Python", thread_id="test")

        # Agent should still return a response
        assert result.response is not None

    async def test_agent_handles_connection_error_in_stream(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """Agent stream handles connection errors."""
        mock_graph = Mock()

        async def failing_stream(*args, **kwargs):
            yield {"reasoner": {"messages": [AIMessage(content="Starting...")]}}
            raise ConnectionError("Lost connection to MCP server")

        mock_graph.astream = failing_stream

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        events = []
        with pytest.raises(ConnectionError, match="Lost connection"):
            async for event in agent.run_stream(message="Hello", thread_id="test"):
                events.append(event)

        # Should have received first event before error
        assert len(events) == 1


class TestLLMErrors:
    """E2E tests for LLM error handling."""

    async def test_invoke_raises_on_graph_error(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """invoke raises when graph execution fails."""
        mock_graph = Mock()
        mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("LLM API error"))

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        with pytest.raises(RuntimeError, match="LLM API error"):
            await agent.run(message="Hello", thread_id="test")

    async def test_invoke_raises_on_rate_limit(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """invoke raises on rate limit errors."""
        mock_graph = Mock()
        mock_graph.ainvoke = AsyncMock(side_effect=Exception("Rate limit exceeded. Please retry."))

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        with pytest.raises(Exception, match="Rate limit"):
            await agent.run(message="Hello", thread_id="test")

    async def test_invoke_raises_on_invalid_response(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """invoke raises on invalid LLM response format."""
        mock_graph = Mock()
        mock_graph.ainvoke = AsyncMock(side_effect=ValueError("Invalid response format from LLM"))

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        with pytest.raises(ValueError, match="Invalid response"):
            await agent.run(message="Hello", thread_id="test")

    async def test_stream_raises_on_graph_error(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """stream raises when graph execution fails."""
        mock_graph = Mock()

        async def failing_stream(*args, **kwargs):
            raise RuntimeError("LLM streaming error")
            yield  # type: ignore[unreachable]

        mock_graph.astream = failing_stream

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        with pytest.raises(RuntimeError, match="LLM streaming error"):
            async for _ in agent.run_stream(message="Hello", thread_id="test"):
                pass

    async def test_stream_partial_failure(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """stream handles partial execution before failure."""
        mock_graph = Mock()

        async def partial_stream(*args, **kwargs):
            yield {"reasoner": {"messages": [AIMessage(content="First response")]}}
            yield {"reasoner": {"messages": [AIMessage(content="Second response")]}}
            raise RuntimeError("Connection lost mid-stream")

        mock_graph.astream = partial_stream

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        events = []
        with pytest.raises(RuntimeError, match="Connection lost"):
            async for event in agent.run_stream(message="Hello", thread_id="test"):
                events.append(event)

        # Should have received events before failure
        assert len(events) == 2


class TestErrorRecovery:
    """E2E tests for error recovery scenarios."""

    async def test_agent_recovers_after_error(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """Agent can be invoked again after an error."""
        mock_graph = Mock()
        call_count = 0

        async def intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Temporary failure")
            return {
                "messages": [AIMessage(content="Success!")],
                "reasoning_steps": 1,
                "thread_id": "test",
                "input_tokens_by_model": {},
                "output_tokens_by_model": {},
            }

        mock_graph.ainvoke = intermittent_failure

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        # First call fails
        with pytest.raises(RuntimeError):
            await agent.run(message="Hello", thread_id="test")

        # Second call succeeds
        result = await agent.run(message="Hello again", thread_id="test")
        assert result.response == "Success!"

    async def test_different_threads_isolated(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """Errors in one thread don't affect other threads."""
        mock_graph = Mock()

        async def thread_specific(*args, **kwargs):
            config = kwargs.get("config", {})
            thread_id = config.get("configurable", {}).get("thread_id")
            if thread_id == "failing-thread":
                raise RuntimeError("Thread-specific failure")
            return {
                "messages": [AIMessage(content=f"Success for {thread_id}")],
                "reasoning_steps": 1,
                "thread_id": thread_id,
                "input_tokens_by_model": {},
                "output_tokens_by_model": {},
            }

        mock_graph.ainvoke = thread_specific

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        # Failing thread
        with pytest.raises(RuntimeError):
            await agent.run(message="Hello", thread_id="failing-thread")

        # Different thread succeeds
        result = await agent.run(message="Hello", thread_id="working-thread")
        assert "working-thread" in result.response
