"""Integration tests for A2A protocol routes.

Tests the agent registration and A2A route setup functions.
"""

from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentIdentity, Audience
from my_agentic_serviceservice_order_specialist.platform.agent.registration import ToolInfo
from my_agentic_serviceservice_order_specialist.platform.server.routes.a2a import register_agent_card


class TestRegisterAgentCard:
    """Tests for register_agent_card function."""

    @pytest.fixture
    def mock_http_client(self) -> AsyncMock:
        """Create a mock HTTP client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        response = Mock()
        response.raise_for_status = Mock()
        client.post = AsyncMock(return_value=response)
        return client

    @pytest.fixture
    def sample_agent_card(self) -> AgentCard:
        """Create a sample agent card."""
        return AgentCard(
            name="Test Agent",
            description="A test agent",
            url="http://localhost:8000/a2a/test-agent/rpc",
            version="0.3.0",
            capabilities=AgentCapabilities(
                streaming=True,
                push_notifications=True,
                state_transition_history=True,
            ),
            skills=[
                AgentSkill(
                    id="general-query",
                    name="General Query",
                    description="Answer general questions",
                    tags=["query", "knowledge"],
                )
            ],
            default_input_modes=["text"],
            default_output_modes=["text"],
        )

    @pytest.fixture
    def sample_identity(self) -> AgentIdentity:
        """Create a sample agent identity."""
        return AgentIdentity(
            name="Test Agent",
            slug="test-agent",
            description="A test agent",
            squad="test-squad",
            origin="test-origin",
            audience=Audience.INTERNAL,
        )

    async def test_register_calls_http_post(
        self,
        mock_http_client: AsyncMock,
        sample_agent_card: AgentCard,
        sample_identity: AgentIdentity,
    ):
        """Registration makes HTTP POST to registry URL."""
        await register_agent_card(
            http_client=mock_http_client,
            registry_url="http://registry.example.com/agents",
            agent_card=sample_agent_card,
            identity=sample_identity,
        )

        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert call_args[0][0] == "http://registry.example.com/agents"

    async def test_register_sends_json_payload(
        self,
        mock_http_client: AsyncMock,
        sample_agent_card: AgentCard,
        sample_identity: AgentIdentity,
    ):
        """Registration sends JSON payload with agent data."""
        await register_agent_card(
            http_client=mock_http_client,
            registry_url="http://registry.example.com/agents",
            agent_card=sample_agent_card,
            identity=sample_identity,
        )

        call_args = mock_http_client.post.call_args
        json_payload = call_args[1]["json"]

        assert "metadata" in json_payload
        assert "agent_card" in json_payload

    async def test_register_includes_metadata(
        self,
        mock_http_client: AsyncMock,
        sample_agent_card: AgentCard,
        sample_identity: AgentIdentity,
    ):
        """Registration includes identity metadata."""
        await register_agent_card(
            http_client=mock_http_client,
            registry_url="http://registry.example.com/agents",
            agent_card=sample_agent_card,
            identity=sample_identity,
        )

        call_args = mock_http_client.post.call_args
        metadata = call_args[1]["json"]["metadata"]

        assert metadata["agent_id"] == sample_identity.unique_id
        assert metadata["squad"] == "test-squad"
        assert metadata["origin"] == "test-origin"
        assert metadata["audience"] == "internal"

    async def test_register_includes_tools(
        self,
        mock_http_client: AsyncMock,
        sample_agent_card: AgentCard,
        sample_identity: AgentIdentity,
    ):
        """Registration includes tool information when provided."""
        tools = [
            ToolInfo(name="search", description="Search for information"),
            ToolInfo(name="fetch", description="Fetch a URL"),
        ]

        await register_agent_card(
            http_client=mock_http_client,
            registry_url="http://registry.example.com/agents",
            agent_card=sample_agent_card,
            identity=sample_identity,
            tools=tools,
        )

        call_args = mock_http_client.post.call_args
        json_payload = call_args[1]["json"]

        assert "tools" in json_payload
        assert len(json_payload["tools"]) == 2

    async def test_register_empty_tools_when_none(
        self,
        mock_http_client: AsyncMock,
        sample_agent_card: AgentCard,
        sample_identity: AgentIdentity,
    ):
        """Registration sends empty tools list when none provided."""
        await register_agent_card(
            http_client=mock_http_client,
            registry_url="http://registry.example.com/agents",
            agent_card=sample_agent_card,
            identity=sample_identity,
            tools=None,
        )

        call_args = mock_http_client.post.call_args
        json_payload = call_args[1]["json"]

        assert json_payload["tools"] == []

    async def test_register_handles_http_error(
        self,
        mock_http_client: AsyncMock,
        sample_agent_card: AgentCard,
        sample_identity: AgentIdentity,
    ):
        """Registration handles HTTP errors gracefully."""
        mock_http_client.post.side_effect = httpx.HTTPError("Connection failed")

        # Should not raise, just log error
        await register_agent_card(
            http_client=mock_http_client,
            registry_url="http://registry.example.com/agents",
            agent_card=sample_agent_card,
            identity=sample_identity,
        )

    async def test_register_handles_status_error(
        self,
        mock_http_client: AsyncMock,
        sample_agent_card: AgentCard,
        sample_identity: AgentIdentity,
    ):
        """Registration handles HTTP status errors gracefully."""
        response = Mock()
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=Mock(),
            response=Mock(),
        )
        mock_http_client.post = AsyncMock(return_value=response)

        # Should not raise, just log error
        await register_agent_card(
            http_client=mock_http_client,
            registry_url="http://registry.example.com/agents",
            agent_card=sample_agent_card,
            identity=sample_identity,
        )


class TestAgentCardStructure:
    """Tests for agent card structure validation."""

    @pytest.fixture
    def sample_agent_card(self) -> AgentCard:
        """Create a sample agent card."""
        return AgentCard(
            name="Knowledge",
            description="Answers questions about Telnyx",
            url="http://localhost:8000/a2a/knowledge/rpc",
            version="0.3.0",
            capabilities=AgentCapabilities(
                streaming=True,
                push_notifications=True,
                state_transition_history=True,
            ),
            skills=[
                AgentSkill(
                    id="general-query",
                    name="General Query",
                    description="Answer general questions",
                    tags=["query", "knowledge"],
                )
            ],
            default_input_modes=["text"],
            default_output_modes=["text"],
        )

    def test_agent_card_has_required_fields(self, sample_agent_card: AgentCard):
        """Agent card has all required fields."""
        assert sample_agent_card.name is not None
        assert sample_agent_card.description is not None
        assert sample_agent_card.url is not None
        assert sample_agent_card.version is not None

    def test_agent_card_capabilities(self, sample_agent_card: AgentCard):
        """Agent card has capabilities configured."""
        assert sample_agent_card.capabilities is not None
        assert sample_agent_card.capabilities.streaming is True
        assert sample_agent_card.capabilities.push_notifications is True

    def test_agent_card_has_skills(self, sample_agent_card: AgentCard):
        """Agent card has at least one skill."""
        assert sample_agent_card.skills is not None
        assert len(sample_agent_card.skills) >= 1

    def test_agent_card_skill_structure(self, sample_agent_card: AgentCard):
        """Agent card skills have required fields."""
        skill = sample_agent_card.skills[0]
        assert skill.id is not None
        assert skill.name is not None
        assert skill.tags is not None

    def test_agent_card_default_modes(self, sample_agent_card: AgentCard):
        """Agent card has default input/output modes."""
        assert "text" in sample_agent_card.default_input_modes
        assert "text" in sample_agent_card.default_output_modes
