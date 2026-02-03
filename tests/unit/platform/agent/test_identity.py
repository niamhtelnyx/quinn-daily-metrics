"""Unit tests for agent identity and constants.

This module tests identity-related functionality including:
- AgentIdentity integration with project constants
- LangGraphAgent identity delegation
- Service constants
"""

from unittest.mock import MagicMock, Mock

import pytest

from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentIdentity, Audience
from my_agentic_serviceservice_order_specialist.platform.agent.langgraph import LangGraphAgent
from my_agentic_serviceservice_order_specialist.platform.constants import (
    SERVICE_NAME,
    SERVICE_VERSION,
    SQUAD_NAME,
    USER_AGENT,
)


class TestConstants:
    """Tests for service constants."""

    def test_service_name_format(self):
        """SERVICE_NAME should be a valid identifier."""
        assert SERVICE_NAME == "my-agentic-serviceservice-order-specialist"
        assert "-" in SERVICE_NAME  # Kebab case

    def test_service_version_format(self):
        """SERVICE_VERSION should follow semver format."""
        assert SERVICE_VERSION == "0.1.0"
        parts = SERVICE_VERSION.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_squad_name_format(self):
        """SQUAD_NAME should be a dotted identifier."""
        assert SQUAD_NAME == "ai.platform.squad"
        assert "." in SQUAD_NAME

    def test_user_agent_composition(self):
        """USER_AGENT should combine service name and version."""
        assert USER_AGENT == f"{SERVICE_NAME}/client.{SERVICE_VERSION}"
        assert SERVICE_NAME in USER_AGENT
        assert SERVICE_VERSION in USER_AGENT


class TestAgentIdentityWithConstants:
    """Tests for AgentIdentity using project constants."""

    def test_identity_with_project_constants(self):
        """Identity should work with project constants."""
        identity = AgentIdentity(
            name="Test Agent",
            description="Description",
            slug="test-agent",
            squad=SQUAD_NAME,
            origin=SERVICE_NAME,
        )
        assert identity.audience == Audience.INTERNAL
        assert identity.unique_id == f"{SQUAD_NAME}:{SERVICE_NAME}:test-agent"

    def test_identity_unique_id_uses_constants(self):
        """unique_id should incorporate project constants correctly."""
        identity = AgentIdentity(
            name="Knowledge",
            description="Handles knowledge queries",
            slug="knowledge",
            squad=SQUAD_NAME,
            origin=SERVICE_NAME,
        )
        assert SQUAD_NAME in identity.unique_id
        assert SERVICE_NAME in identity.unique_id
        assert identity.unique_id == f"{SQUAD_NAME}:{SERVICE_NAME}:knowledge"

    def test_identity_explicit_audience(self):
        """Explicit audience should override default."""
        identity = AgentIdentity(
            name="Public Agent",
            description="Public Description",
            slug="public-agent",
            squad=SQUAD_NAME,
            origin=SERVICE_NAME,
            audience=Audience.PUBLIC,
        )
        assert identity.audience == Audience.PUBLIC


class TestLangGraphAgentIdentity:
    """Tests for LangGraphAgent identity delegation."""

    @pytest.fixture
    def stub_graph(self):
        """Create a stub LangGraph graph."""
        return MagicMock()

    @pytest.fixture
    def stub_state_builder(self):
        """Create a stub initial state builder."""
        return Mock()

    def test_agent_delegates_name(self, stub_graph, stub_state_builder):
        """Agent name should delegate to identity."""
        identity = AgentIdentity(
            name="Delegation Test",
            description="Tests delegation",
            slug="delegation-test",
            squad="test-squad",
            origin="test-service",
        )
        agent = LangGraphAgent(
            graph=stub_graph,
            identity=identity,
            initial_state_builder=stub_state_builder,
        )
        assert agent.name == identity.name

    def test_agent_delegates_description(self, stub_graph, stub_state_builder):
        """Agent description should delegate to identity."""
        identity = AgentIdentity(
            name="Test",
            description="A detailed description of the agent",
            slug="test",
            squad="squad",
            origin="origin",
        )
        agent = LangGraphAgent(
            graph=stub_graph,
            identity=identity,
            initial_state_builder=stub_state_builder,
        )
        assert agent.description == identity.description

    def test_agent_delegates_slug(self, stub_graph, stub_state_builder):
        """Agent slug should delegate to identity."""
        identity = AgentIdentity(
            name="Test",
            description="Desc",
            slug="my-custom-slug",
            squad="squad",
            origin="origin",
        )
        agent = LangGraphAgent(
            graph=stub_graph,
            identity=identity,
            initial_state_builder=stub_state_builder,
        )
        assert agent.slug == identity.slug

    def test_agent_exposes_full_identity(self, stub_graph, stub_state_builder):
        """Agent should expose the full identity object."""
        identity = AgentIdentity(
            name="Full Identity Test",
            description="Tests full identity access",
            slug="full-identity",
            squad="test-squad",
            origin="test-service",
            audience=Audience.CUSTOMER,
        )
        agent = LangGraphAgent(
            graph=stub_graph,
            identity=identity,
            initial_state_builder=stub_state_builder,
        )
        assert agent.identity is identity
        assert agent.identity.audience == Audience.CUSTOMER
        assert agent.identity.unique_id == "test-squad:test-service:full-identity"

    def test_agent_with_all_audience_types(self, stub_graph, stub_state_builder):
        """Agent should work with all audience types."""
        for audience in Audience:
            identity = AgentIdentity(
                name="Test",
                description="Desc",
                slug="test",
                squad="squad",
                origin="origin",
                audience=audience,
            )
            agent = LangGraphAgent(
                graph=stub_graph,
                identity=identity,
                initial_state_builder=stub_state_builder,
            )
            assert agent.identity.audience == audience
