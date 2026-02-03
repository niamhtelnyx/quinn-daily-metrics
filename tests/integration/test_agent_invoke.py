"""Integration tests for agent invoke flow.

Tests the complete invoke flow from LangGraphAgent through to ExecutionResult,
with mocked LLM responses to simulate real agent behavior.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentIdentity
from my_agentic_serviceservice_order_specialist.platform.agent.langgraph import LangGraphAgent
from my_agentic_serviceservice_order_specialist.platform.agent.messages import ExecutionResult


class TestAgentInvokeFlow:
    """E2E tests for complete agent invoke flow."""

    @pytest.fixture
    def stub_graph_result(self) -> dict:
        """Create a stub graph execution result with canned data."""
        return {
            "messages": [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="What is Python?"),
                AIMessage(content="Python is a programming language."),
            ],
            "reasoning_steps": 1,
            "thread_id": "test-thread-123",
            "input_tokens_by_model": {"test-model": 50},
            "output_tokens_by_model": {"test-model": 25},
        }

    @pytest.fixture
    def stub_graph(self, stub_graph_result: dict) -> Mock:
        """Create a stub compiled graph that returns canned responses."""
        graph = Mock()
        graph.ainvoke = AsyncMock(return_value=stub_graph_result)
        return graph

    @pytest.fixture
    def initial_state_builder_with_system(self):
        """Create a state builder that includes SystemMessage."""

        def builder(message: str, thread_id: str, utc_now: datetime | None = None):
            return {
                "messages": [
                    SystemMessage(content="System prompt"),
                    HumanMessage(content=message),
                ],
                "reasoning_steps": 0,
                "thread_id": thread_id,
                "input_tokens_by_model": {},
                "output_tokens_by_model": {},
            }

        return builder

    @pytest.fixture
    def agent(
        self,
        stub_graph: Mock,
        stub_identity: AgentIdentity,
        initial_state_builder_with_system,
    ) -> LangGraphAgent:
        """Create a LangGraphAgent with stub graph."""
        return LangGraphAgent(
            graph=stub_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder_with_system,
        )

    async def test_invoke_returns_execution_result(self, agent: LangGraphAgent):
        """invoke returns an ExecutionResult."""
        result = await agent.run(
            message="What is Python?",
            thread_id="test-thread-123",
        )

        assert isinstance(result, ExecutionResult)

    async def test_invoke_result_contains_response(self, agent: LangGraphAgent):
        """ExecutionResult contains the agent's response."""
        result = await agent.run(
            message="What is Python?",
            thread_id="test-thread-123",
        )

        assert result.response == "Python is a programming language."

    async def test_invoke_result_contains_messages(self, agent: LangGraphAgent):
        """ExecutionResult contains message history."""
        result = await agent.run(
            message="What is Python?",
            thread_id="test-thread-123",
        )

        assert len(result.messages) >= 1

    async def test_invoke_result_contains_thread_id(self, agent: LangGraphAgent):
        """ExecutionResult contains the thread_id."""
        result = await agent.run(
            message="What is Python?",
            thread_id="test-thread-123",
        )

        assert result.thread_id == "test-thread-123"

    async def test_invoke_calls_graph_with_correct_config(
        self, agent: LangGraphAgent, stub_graph: Mock
    ):
        """invoke calls graph.ainvoke with correct thread config."""
        await agent.run(
            message="What is Python?",
            thread_id="my-thread-456",
        )

        stub_graph.ainvoke.assert_called_once()
        call_kwargs = stub_graph.ainvoke.call_args[1]
        assert call_kwargs["config"]["configurable"]["thread_id"] == "my-thread-456"

    async def test_invoke_passes_message_to_state_builder(
        self, stub_graph: Mock, stub_identity: AgentIdentity
    ):
        """invoke passes the message to the initial state builder."""
        state_builder = Mock(
            return_value={
                "messages": [],
                "reasoning_steps": 0,
                "thread_id": "test",
                "input_tokens_by_model": {},
                "output_tokens_by_model": {},
            }
        )
        stub_graph.ainvoke = AsyncMock(
            return_value={
                "messages": [AIMessage(content="Response")],
                "reasoning_steps": 1,
                "thread_id": "test",
                "input_tokens_by_model": {},
                "output_tokens_by_model": {},
            }
        )

        agent = LangGraphAgent(
            graph=stub_graph,
            identity=stub_identity,
            initial_state_builder=state_builder,
        )

        await agent.run(message="Hello world", thread_id="test-thread")

        state_builder.assert_called_once()
        call_kwargs = state_builder.call_args[1]
        assert call_kwargs["message"] == "Hello world"
        assert call_kwargs["thread_id"] == "test-thread"

    async def test_invoke_with_utc_now(self, stub_graph: Mock, stub_identity: AgentIdentity):
        """invoke passes utc_now to state builder when provided."""
        state_builder = Mock(
            return_value={
                "messages": [],
                "reasoning_steps": 0,
                "thread_id": "test",
                "input_tokens_by_model": {},
                "output_tokens_by_model": {},
            }
        )
        stub_graph.ainvoke = AsyncMock(
            return_value={
                "messages": [AIMessage(content="Response")],
                "reasoning_steps": 1,
                "thread_id": "test",
                "input_tokens_by_model": {},
                "output_tokens_by_model": {},
            }
        )

        agent = LangGraphAgent(
            graph=stub_graph,
            identity=stub_identity,
            initial_state_builder=state_builder,
        )

        utc_now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
        await agent.run(message="Hello", thread_id="test-thread", utc_now=utc_now)

        call_kwargs = state_builder.call_args[1]
        assert call_kwargs["utc_now"] == utc_now


class TestAgentInvokeMetadata:
    """E2E tests for agent invoke metadata handling."""

    async def test_invoke_tracks_reasoning_steps(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """ExecutionResult includes reasoning steps count."""
        mock_graph = Mock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "messages": [AIMessage(content="After 3 steps of reasoning...")],
                "reasoning_steps": 3,
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

        result = await agent.run(message="Complex question", thread_id="test")

        assert result.reasoning_steps == 3

    async def test_invoke_result_metadata_contains_token_counts(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """ExecutionResult metadata includes token usage."""
        mock_graph = Mock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "messages": [AIMessage(content="Response")],
                "reasoning_steps": 1,
                "thread_id": "test",
                "input_tokens_by_model": {"gpt-4": 100},
                "output_tokens_by_model": {"gpt-4": 50},
            }
        )

        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        result = await agent.run(message="Hello", thread_id="test")

        # Metadata should contain token information in raw_state
        assert "raw_state" in result.metadata
        raw_state = result.metadata["raw_state"]
        assert "input_tokens_by_model" in raw_state
        assert "output_tokens_by_model" in raw_state


class TestAgentInvokeEdgeCases:
    """E2E tests for agent invoke edge cases."""

    async def test_invoke_with_empty_message(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """invoke handles empty message input."""
        mock_graph = Mock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "messages": [AIMessage(content="I need more information.")],
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

        result = await agent.run(message="", thread_id="test")

        assert result.response is not None

    async def test_invoke_with_long_message(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """invoke handles very long message input."""
        mock_graph = Mock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "messages": [AIMessage(content="Processed your long message.")],
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

        long_message = "x" * 10000
        result = await agent.run(message=long_message, thread_id="test")

        assert result.response is not None

    async def test_invoke_preserves_special_characters(
        self, stub_identity: AgentIdentity, initial_state_builder
    ):
        """invoke preserves special characters in messages."""
        mock_graph = Mock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "messages": [AIMessage(content="Response with émojis 🎉")],
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

        result = await agent.run(message="Question with émojis 🤔", thread_id="test")

        assert "🎉" in result.response
