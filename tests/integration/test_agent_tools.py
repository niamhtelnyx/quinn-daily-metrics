"""Integration tests for agent tool execution flow.

Tests the complete tool execution flow including tool binding,
tool calls, and result handling in the agent.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool

from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentIdentity
from my_agentic_serviceservice_order_specialist.platform.agent.langgraph import LangGraphAgent


class TestAgentToolBinding:
    """E2E tests for agent tool binding."""

    @pytest.fixture
    def sample_tools(self) -> list[BaseTool]:
        """Create sample tools for testing."""

        def search_fn(query: str) -> str:
            return f"Results for: {query}"

        def calculate_fn(expression: str) -> str:
            return f"Calculated: {expression}"

        return [
            StructuredTool.from_function(
                func=search_fn,
                name="search",
                description="Search for information",
            ),
            StructuredTool.from_function(
                func=calculate_fn,
                name="calculate",
                description="Calculate an expression",
            ),
        ]

    def test_agent_stores_tools(
        self,
        stub_identity: AgentIdentity,
        sample_tools: list[BaseTool],
        initial_state_builder,
    ):
        """Agent stores provided tools."""
        mock_graph = Mock()
        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
            tools=sample_tools,
        )

        assert len(agent.tools) == 2
        assert agent.tools[0].name == "search"
        assert agent.tools[1].name == "calculate"

    def test_agent_tools_default_empty(
        self,
        stub_identity: AgentIdentity,
        initial_state_builder,
    ):
        """Agent defaults to empty tools list."""
        mock_graph = Mock()
        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        assert agent.tools == []

    def test_agent_tools_accessible_by_name(
        self,
        stub_identity: AgentIdentity,
        sample_tools: list[BaseTool],
        initial_state_builder,
    ):
        """Agent tools can be accessed by name."""
        mock_graph = Mock()
        agent = LangGraphAgent(
            graph=mock_graph,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
            tools=sample_tools,
        )

        tool_names = [t.name for t in agent.tools]
        assert "search" in tool_names
        assert "calculate" in tool_names


class TestAgentToolExecution:
    """E2E tests for agent tool execution in graph."""

    @pytest.fixture
    def stub_graph_with_tool_call(self) -> Mock:
        """Create a stub graph that simulates tool execution with canned data."""
        # Simulate a graph response that includes tool call and result
        ai_msg_with_tool = AIMessage(content="Let me search for that.")
        ai_msg_with_tool.tool_calls = [
            {"name": "search", "args": {"query": "Python"}, "id": "call_123"}
        ]

        graph_result = {
            "messages": [
                HumanMessage(content="What is Python?"),
                ai_msg_with_tool,
                ToolMessage(content="Python is a programming language.", tool_call_id="call_123"),
                AIMessage(content="Python is a programming language used for..."),
            ],
            "reasoning_steps": 2,
            "thread_id": "test-thread",
            "input_tokens_by_model": {"test-model": 100},
            "output_tokens_by_model": {"test-model": 50},
        }

        graph = Mock()
        graph.ainvoke = AsyncMock(return_value=graph_result)
        return graph

    async def test_invoke_with_tool_execution(
        self,
        stub_graph_with_tool_call: Mock,
        stub_identity: AgentIdentity,
        initial_state_builder,
    ):
        """invoke handles tool execution in graph."""
        agent = LangGraphAgent(
            graph=stub_graph_with_tool_call,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        result = await agent.run(
            message="What is Python?",
            thread_id="test-thread",
        )

        # Should get final response after tool execution
        assert "Python" in result.response

    async def test_invoke_tracks_tool_steps(
        self,
        stub_graph_with_tool_call: Mock,
        stub_identity: AgentIdentity,
        initial_state_builder,
    ):
        """invoke tracks reasoning steps including tool calls."""
        agent = LangGraphAgent(
            graph=stub_graph_with_tool_call,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        result = await agent.run(
            message="What is Python?",
            thread_id="test-thread",
        )

        assert result.reasoning_steps == 2

    async def test_invoke_messages_include_tool_messages(
        self,
        stub_graph_with_tool_call: Mock,
        stub_identity: AgentIdentity,
        initial_state_builder,
    ):
        """invoke result messages include tool interactions."""
        agent = LangGraphAgent(
            graph=stub_graph_with_tool_call,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        result = await agent.run(
            message="What is Python?",
            thread_id="test-thread",
        )

        # Messages should include the full conversation
        assert len(result.messages) >= 2


class TestAgentMultipleToolCalls:
    """E2E tests for agent with multiple tool calls."""

    @pytest.fixture
    def stub_graph_with_multiple_tools(self) -> Mock:
        """Create a stub graph that simulates multiple tool calls with canned data."""
        # First AI message with first tool call
        ai_msg_1 = AIMessage(content="Let me search first.")
        ai_msg_1.tool_calls = [
            {"name": "search", "args": {"query": "Python basics"}, "id": "call_1"}
        ]

        # Second AI message with second tool call
        ai_msg_2 = AIMessage(content="Now let me calculate.")
        ai_msg_2.tool_calls = [{"name": "calculate", "args": {"expression": "2+2"}, "id": "call_2"}]

        graph_result = {
            "messages": [
                HumanMessage(content="Search Python and calculate 2+2"),
                ai_msg_1,
                ToolMessage(content="Python basics info...", tool_call_id="call_1"),
                ai_msg_2,
                ToolMessage(content="4", tool_call_id="call_2"),
                AIMessage(content="Here's what I found and calculated..."),
            ],
            "reasoning_steps": 4,
            "thread_id": "test-thread",
            "input_tokens_by_model": {"test-model": 200},
            "output_tokens_by_model": {"test-model": 100},
        }

        graph = Mock()
        graph.ainvoke = AsyncMock(return_value=graph_result)
        return graph

    async def test_invoke_handles_multiple_tool_calls(
        self,
        stub_graph_with_multiple_tools: Mock,
        stub_identity: AgentIdentity,
        initial_state_builder,
    ):
        """invoke handles multiple sequential tool calls."""
        agent = LangGraphAgent(
            graph=stub_graph_with_multiple_tools,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        result = await agent.run(
            message="Search Python and calculate 2+2",
            thread_id="test-thread",
        )

        assert result.response is not None
        assert result.reasoning_steps == 4


class TestAgentToolErrors:
    """E2E tests for agent tool error handling."""

    @pytest.fixture
    def stub_graph_with_tool_error(self) -> Mock:
        """Create a stub graph that simulates tool error with canned data."""
        ai_msg_with_tool = AIMessage(content="Let me try this tool.")
        ai_msg_with_tool.tool_calls = [{"name": "failing_tool", "args": {}, "id": "call_err"}]

        graph_result = {
            "messages": [
                HumanMessage(content="Use the failing tool"),
                ai_msg_with_tool,
                ToolMessage(content="Error: Tool execution failed", tool_call_id="call_err"),
                AIMessage(content="I encountered an error with that tool."),
            ],
            "reasoning_steps": 2,
            "thread_id": "test-thread",
            "input_tokens_by_model": {},
            "output_tokens_by_model": {},
        }

        graph = Mock()
        graph.ainvoke = AsyncMock(return_value=graph_result)
        return graph

    async def test_invoke_handles_tool_error(
        self,
        stub_graph_with_tool_error: Mock,
        stub_identity: AgentIdentity,
        initial_state_builder,
    ):
        """invoke handles tool execution errors gracefully."""
        agent = LangGraphAgent(
            graph=stub_graph_with_tool_error,
            identity=stub_identity,
            initial_state_builder=initial_state_builder,
        )

        result = await agent.run(
            message="Use the failing tool",
            thread_id="test-thread",
        )

        # Agent should still return a response despite tool error
        assert result.response is not None
        assert "error" in result.response.lower()
