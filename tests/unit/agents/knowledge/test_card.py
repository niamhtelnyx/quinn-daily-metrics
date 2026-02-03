"""Unit tests for KnowledgeAgentCardBuilder.

This module tests the A2A AgentCard builder functionality.
"""

from unittest.mock import Mock

from a2a.types import AgentCard

from my_agentic_serviceservice_order_specialist.agents.knowledge.card import KnowledgeAgentCardBuilder


class TestKnowledgeAgentCardBuilderInit:
    """Tests for KnowledgeAgentCardBuilder initialization."""

    def test_stores_agent(self):
        """Builder stores the agent reference."""
        mock_agent = Mock()
        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000",
            a2a_protocol_version="0.3.0",
        )
        assert builder.agent is mock_agent

    def test_stores_base_url(self):
        """Builder stores the base URL."""
        mock_agent = Mock()
        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://api.example.com:8080",
            a2a_protocol_version="0.3.0",
        )
        assert builder.a2a_base_url == "http://api.example.com:8080"

    def test_stores_protocol_version(self):
        """Builder stores the protocol version."""
        mock_agent = Mock()
        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000",
            a2a_protocol_version="1.0.0",
        )
        assert builder.a2a_protocol_version == "1.0.0"


class TestKnowledgeAgentCardBuilderBuild:
    """Tests for KnowledgeAgentCardBuilder.build() method."""

    def test_returns_agent_card(self):
        """build() returns an AgentCard instance."""
        mock_agent = Mock()
        mock_agent.name = "Test Agent"
        mock_agent.description = "A test agent"
        mock_agent.slug = "test-agent"

        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000",
            a2a_protocol_version="0.3.0",
        )
        card = builder.build()

        assert isinstance(card, AgentCard)

    def test_uses_agent_name(self):
        """Card name comes from agent.name."""
        mock_agent = Mock()
        mock_agent.name = "Knowledge"
        mock_agent.description = "Desc"
        mock_agent.slug = "knowledge"

        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000",
            a2a_protocol_version="0.3.0",
        )
        card = builder.build()

        assert card.name == "Knowledge"

    def test_uses_agent_description(self):
        """Card description comes from agent.description."""
        mock_agent = Mock()
        mock_agent.name = "Agent"
        mock_agent.description = "Handles queries"
        mock_agent.slug = "knowledge"

        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000",
            a2a_protocol_version="0.3.0",
        )
        card = builder.build()

        assert card.description == "Handles queries"

    def test_constructs_url_from_base_and_slug(self):
        """Card URL is constructed from base_url and agent.slug."""
        mock_agent = Mock()
        mock_agent.name = "Agent"
        mock_agent.description = "Desc"
        mock_agent.slug = "my-agent"

        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000/a2a",
            a2a_protocol_version="0.3.0",
        )
        card = builder.build()

        assert card.url == "http://localhost:8000/a2a/my-agent/rpc"

    def test_uses_protocol_version(self):
        """Card version comes from a2a_protocol_version."""
        mock_agent = Mock()
        mock_agent.name = "Agent"
        mock_agent.description = "Desc"
        mock_agent.slug = "agent"

        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000",
            a2a_protocol_version="1.2.3",
        )
        card = builder.build()

        assert card.version == "1.2.3"

    def test_capabilities_streaming_enabled(self):
        """Card has streaming capability enabled."""
        mock_agent = Mock()
        mock_agent.name = "Agent"
        mock_agent.description = "Desc"
        mock_agent.slug = "agent"

        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000",
            a2a_protocol_version="0.3.0",
        )
        card = builder.build()

        assert card.capabilities is not None
        assert card.capabilities.streaming is True

    def test_capabilities_push_notifications_enabled(self):
        """Card has push_notifications capability enabled."""
        mock_agent = Mock()
        mock_agent.name = "Agent"
        mock_agent.description = "Desc"
        mock_agent.slug = "agent"

        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000",
            a2a_protocol_version="0.3.0",
        )
        card = builder.build()

        assert card.capabilities is not None
        assert card.capabilities.push_notifications is True

    def test_capabilities_state_transition_history_enabled(self):
        """Card has state_transition_history capability enabled."""
        mock_agent = Mock()
        mock_agent.name = "Agent"
        mock_agent.description = "Desc"
        mock_agent.slug = "agent"

        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000",
            a2a_protocol_version="0.3.0",
        )
        card = builder.build()

        assert card.capabilities is not None
        assert card.capabilities.state_transition_history is True

    def test_has_general_query_skill(self):
        """Card includes the general-query skill."""
        mock_agent = Mock()
        mock_agent.name = "Agent"
        mock_agent.description = "Desc"
        mock_agent.slug = "agent"

        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000",
            a2a_protocol_version="0.3.0",
        )
        card = builder.build()

        assert card.skills is not None
        assert len(card.skills) == 1
        skill = card.skills[0]
        assert skill.id == "general-query"
        assert skill.name == "General Query"
        assert "query" in skill.tags
        assert "knowledge" in skill.tags

    def test_default_input_modes(self):
        """Card has text as default input mode."""
        mock_agent = Mock()
        mock_agent.name = "Agent"
        mock_agent.description = "Desc"
        mock_agent.slug = "agent"

        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000",
            a2a_protocol_version="0.3.0",
        )
        card = builder.build()

        assert card.default_input_modes == ["text"]

    def test_default_output_modes(self):
        """Card has text as default output mode."""
        mock_agent = Mock()
        mock_agent.name = "Agent"
        mock_agent.description = "Desc"
        mock_agent.slug = "agent"

        builder = KnowledgeAgentCardBuilder(
            agent=mock_agent,
            a2a_base_url="http://localhost:8000",
            a2a_protocol_version="0.3.0",
        )
        card = builder.build()

        assert card.default_output_modes == ["text"]
