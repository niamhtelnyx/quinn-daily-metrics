"""Unit tests for ReasonerNode and related helper methods.

Tests for:
- LlmClient.extract_tokens: Token extraction from AIMessage
- add_tokens reducer: Token accumulation in state
- ReasonerNode._trim_messages: Message trimming

These tests do not require external systems - they test internal logic only.
"""

from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.reasoner import ReasonerNode
from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentConfig
from my_agentic_serviceservice_order_specialist.platform.agent.llm_client import LlmClient
from my_agentic_serviceservice_order_specialist.platform.agent.state import add_tokens


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
    llm.model = "test-model"
    return llm


@pytest.fixture
def reasoner_node(mock_llm, agent_config) -> ReasonerNode:
    """Create a ReasonerNode with mock LLM."""
    return ReasonerNode(llm_with_tools=mock_llm, config=agent_config)


class TestExtractTokens:
    """Tests for LlmClient.extract_tokens static method."""

    @pytest.mark.parametrize(
        ("usage_metadata", "expected_input", "expected_output"),
        [
            # Full metadata
            ({"input_tokens": 100, "output_tokens": 50}, 100, 50),
            # Only input tokens
            ({"input_tokens": 100}, 100, 0),
            # Only output tokens
            ({"output_tokens": 50}, 0, 50),
            # Empty dict
            ({}, 0, 0),
            # None value
            (None, 0, 0),
        ],
    )
    def test_extract_tokens_from_metadata(
        self,
        usage_metadata: dict | None,
        expected_input: int,
        expected_output: int,
    ):
        """Extracts tokens from usage_metadata, defaulting to 0 for missing values."""
        message = AIMessage(content="test")
        message.usage_metadata = usage_metadata  # type: ignore[assignment]

        input_tokens, output_tokens = LlmClient.extract_tokens(message)

        assert input_tokens == expected_input
        assert output_tokens == expected_output

    def test_extract_tokens_without_usage_metadata_attr(self):
        """Returns zeros when message has no usage_metadata attribute."""
        message = AIMessage(content="test")

        input_tokens, output_tokens = LlmClient.extract_tokens(message)

        assert input_tokens == 0
        assert output_tokens == 0


class TestAddTokensReducer:
    """Tests for add_tokens state reducer."""

    def test_add_tokens_new_model(self):
        """Adds tokens for a new model to empty dict."""
        existing = {}
        new = {"test-model": 100}

        result = add_tokens(existing, new)

        assert result == {"test-model": 100}

    def test_add_tokens_existing_model(self):
        """Accumulates tokens for an existing model."""
        existing = {"test-model": 100}
        new = {"test-model": 200}

        result = add_tokens(existing, new)

        assert result == {"test-model": 300}

    def test_add_tokens_multiple_models(self):
        """Preserves tokens from other models while adding new."""
        existing = {"other-model": 500}
        new = {"test-model": 100}

        result = add_tokens(existing, new)

        assert result == {"other-model": 500, "test-model": 100}

    def test_add_tokens_none_existing(self):
        """Handles None as existing value."""
        result = add_tokens(None, {"test-model": 100})  # type: ignore[arg-type]

        assert result == {"test-model": 100}

    def test_add_tokens_none_new(self):
        """Handles None as new value."""
        result = add_tokens({"test-model": 100}, None)  # type: ignore[arg-type]

        assert result == {"test-model": 100}

    def test_add_tokens_both_none(self):
        """Handles both values being None."""
        result = add_tokens(None, None)  # type: ignore[arg-type]

        assert result == {}


class TestTrimMessages:
    """Tests for _trim_messages method."""

    def test_trim_messages_under_limit(self, reasoner_node):
        """Does not trim when under limit."""
        messages = [
            SystemMessage(content="System"),
            HumanMessage(content="Hello"),
            AIMessage(content="Hi"),
        ]

        result = reasoner_node._trim_messages(messages)

        assert len(result) == 3

    def test_trim_messages_over_limit(self, mock_llm):
        """Trims messages when over token limit."""
        config = AgentConfig(
            max_reasoning_steps=3,
            always_visible_tools=frozenset(),
            recursion_limit=50,
            artifact_threshold=5000,
            max_context_tokens=50,  # Very low limit
        )
        node = ReasonerNode(llm_with_tools=mock_llm, config=config)

        # Create messages that exceed the token limit
        messages = [
            SystemMessage(content="System prompt here"),
            HumanMessage(content="First message " * 50),
            AIMessage(content="Response " * 50),
            HumanMessage(content="Second message"),
        ]

        result = node._trim_messages(messages)

        # Should trim to fit within limit
        assert len(result) < len(messages)
