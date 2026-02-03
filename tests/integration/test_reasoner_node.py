"""Integration tests for ReasonerNode.

Tests the LLM reasoning node __call__ method which requires
mocking the LLM chain and trimmer pipeline.

Note: Helper method tests (LlmClient.extract_tokens, add_tokens reducer, _trim_messages)
have been moved to tests/unit/agents/knowledge/test_reasoner_helpers.py
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.reasoner import ReasonerNode
from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentConfig
from my_agentic_serviceservice_order_specialist.platform.agent.llm_client import LlmClient


def create_response_with_tokens(content: str, input_tokens: int, output_tokens: int) -> AIMessage:
    """Create an AIMessage with usage_metadata for token counts."""
    response = AIMessage(content=content)
    response.usage_metadata = {"input_tokens": input_tokens, "output_tokens": output_tokens}  # type: ignore
    return response


@pytest.fixture
def agent_config() -> AgentConfig:
    """Create a test agent config."""
    return AgentConfig(
        max_reasoning_steps=3,
        always_visible_tools=frozenset(),
        recursion_limit=50,
        artifact_threshold=5000,
        max_context_tokens=1000,
    )


@pytest.fixture
def mock_llm():
    """Create a mock LLM."""
    llm = Mock()
    llm.model_name = "test-model"
    llm.extract_tokens = LlmClient.extract_tokens  # Use real static method
    return llm


class TestReasonerNodeCall:
    """Tests for ReasonerNode.__call__ method."""

    @pytest.fixture
    def mock_chain(self):
        """Create a mock chain for testing."""
        chain = Mock()
        chain.ainvoke = AsyncMock()
        return chain

    async def test_call_normal_execution(self, mock_llm, agent_config, mock_chain):
        """Normal execution returns LLM response."""
        response = create_response_with_tokens("I can help with that.", 50, 25)

        mock_chain.ainvoke.return_value = response
        node = ReasonerNode(llm_with_tools=mock_llm, config=agent_config)

        state = {
            "messages": [HumanMessage(content="Hello")],
            "reasoning_steps": 0,
            "thread_id": "test",
            "input_tokens_by_model": {},
            "output_tokens_by_model": {},
        }

        with patch.object(node, "_trimmer") as mock_trimmer:
            mock_trimmer.__or__ = Mock(return_value=mock_chain)
            result = await node(state)  # type: ignore[arg-type]

        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "I can help with that."
        assert result["reasoning_steps"] == 1
        assert result["input_tokens_by_model"]["test-model"] == 50
        assert result["output_tokens_by_model"]["test-model"] == 25

    async def test_call_max_steps_forces_final_answer(self, mock_llm, agent_config, mock_chain):
        """Forces final answer when max steps reached."""
        response = create_response_with_tokens("Final answer here.", 100, 50)

        mock_chain.ainvoke.return_value = response
        node = ReasonerNode(llm_with_tools=mock_llm, config=agent_config)

        state = {
            "messages": [HumanMessage(content="Hello")],
            "reasoning_steps": 3,  # At max
            "thread_id": "test",
            "input_tokens_by_model": {},
            "output_tokens_by_model": {},
        }

        with patch.object(node, "_trimmer") as mock_trimmer:
            mock_trimmer.__or__ = Mock(return_value=mock_chain)
            result = await node(state)  # type: ignore[arg-type]

        # Should include forcing message + response
        assert len(result["messages"]) == 3  # original + force msg + response
        assert "maximum number of reasoning steps" in result["messages"][1].content
        assert result["messages"][2].content == "Final answer here."
        assert result["reasoning_steps"] == 4

    async def test_call_increments_reasoning_steps(self, mock_llm, agent_config, mock_chain):
        """Each call increments reasoning steps."""
        response = create_response_with_tokens("Response", 0, 0)

        mock_chain.ainvoke.return_value = response
        node = ReasonerNode(llm_with_tools=mock_llm, config=agent_config)

        state = {
            "messages": [HumanMessage(content="Hello")],
            "reasoning_steps": 1,
            "thread_id": "test",
            "input_tokens_by_model": {},
            "output_tokens_by_model": {},
        }

        with patch.object(node, "_trimmer") as mock_trimmer:
            mock_trimmer.__or__ = Mock(return_value=mock_chain)
            result = await node(state)  # type: ignore[arg-type]

        assert result["reasoning_steps"] == 2

    async def test_call_returns_single_call_tokens(self, mock_llm, agent_config, mock_chain):
        """Node returns single-call tokens (reducer handles accumulation)."""
        response = create_response_with_tokens("Response", 100, 50)

        mock_chain.ainvoke.return_value = response
        node = ReasonerNode(llm_with_tools=mock_llm, config=agent_config)

        state = {
            "messages": [HumanMessage(content="Hello")],
            "reasoning_steps": 0,
            "thread_id": "test",
            "input_tokens_by_model": {"test-model": 200},  # Existing tokens
            "output_tokens_by_model": {"test-model": 100},
        }

        with patch.object(node, "_trimmer") as mock_trimmer:
            mock_trimmer.__or__ = Mock(return_value=mock_chain)
            result = await node(state)  # type: ignore[arg-type]

        # Node returns only this call's tokens; reducer handles accumulation
        assert result["input_tokens_by_model"]["test-model"] == 100
        assert result["output_tokens_by_model"]["test-model"] == 50
