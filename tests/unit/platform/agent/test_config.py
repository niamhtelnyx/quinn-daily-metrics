"""Unit tests for agent configuration dataclasses.

This module tests all configuration dataclasses in platform/agent/config.py.
"""

from dataclasses import FrozenInstanceError

import pytest

from my_agentic_serviceservice_order_specialist.platform.agent.config import (
    AgentConfig,
    AgentIdentity,
    Audience,
    LlmConfig,
    MCPConfig,
)


class TestAudience:
    """Tests for Audience enum."""

    def test_all_values_exist(self):
        """All expected audience values should exist."""
        assert Audience.CUSTOMER == "customer"
        assert Audience.INTERNAL == "internal"
        assert Audience.PUBLIC == "public"

    def test_is_string_enum(self):
        """Audience values should be usable as strings."""
        assert str(Audience.CUSTOMER) == "customer"
        assert f"audience: {Audience.INTERNAL}" == "audience: internal"

    def test_from_string(self):
        """Audience can be created from string value."""
        assert Audience("customer") == Audience.CUSTOMER
        assert Audience("internal") == Audience.INTERNAL
        assert Audience("public") == Audience.PUBLIC

    def test_invalid_value_raises(self):
        """Invalid audience string should raise ValueError."""
        with pytest.raises(ValueError):
            Audience("invalid")


class TestLlmConfig:
    """Tests for LlmConfig dataclass."""

    def test_required_model_field(self):
        """Model is the only required field."""
        config = LlmConfig(model="gpt-4")
        assert config.model == "gpt-4"

    def test_default_values(self):
        """Optional fields should have correct defaults."""
        config = LlmConfig(model="claude-3")
        assert config.api_key is None
        assert config.base_url is None
        assert config.temperature == 0.7

    def test_all_fields(self):
        """All fields can be set explicitly."""
        config = LlmConfig(
            model="litellm_proxy/anthropic/claude-sonnet-4-5",
            api_key="sk-test-key",
            base_url="http://litellm:4000",
            temperature=0.5,
        )
        assert config.model == "litellm_proxy/anthropic/claude-sonnet-4-5"
        assert config.api_key == "sk-test-key"
        assert config.base_url == "http://litellm:4000"
        assert config.temperature == 0.5

    def test_frozen_immutability(self):
        """LlmConfig should be immutable (frozen)."""
        config = LlmConfig(model="gpt-4")
        with pytest.raises(FrozenInstanceError):
            config.model = "gpt-3.5"  # type: ignore

    def test_temperature_boundaries(self):
        """Temperature can be set to boundary values."""
        config_zero = LlmConfig(model="test", temperature=0.0)
        config_one = LlmConfig(model="test", temperature=1.0)
        assert config_zero.temperature == 0.0
        assert config_one.temperature == 1.0


class TestMCPConfig:
    """Tests for MCPConfig dataclass."""

    def test_required_server_url(self):
        """server_url is the only required field."""
        config = MCPConfig(server_url="http://mcp:8080")
        assert config.server_url == "http://mcp:8080"

    def test_default_values(self):
        """Optional fields should have correct defaults."""
        config = MCPConfig(server_url="http://mcp:8080")
        assert config.tool_prefix is None
        assert config.headers is None
        assert config.timeout == 60.0
        assert config.sse_read_timeout == 300.0
        assert config.read_timeout == 120.0

    def test_all_fields(self):
        """All fields can be set explicitly."""
        config = MCPConfig(
            server_url="http://mcp-server:9000",
            tool_prefix="github",
            headers={"Authorization": "Bearer token"},
            timeout=30.0,
            sse_read_timeout=600.0,
            read_timeout=60.0,
        )
        assert config.server_url == "http://mcp-server:9000"
        assert config.tool_prefix == "github"
        assert config.headers == {"Authorization": "Bearer token"}
        assert config.timeout == 30.0
        assert config.sse_read_timeout == 600.0
        assert config.read_timeout == 60.0

    def test_frozen_immutability(self):
        """MCPConfig should be immutable (frozen)."""
        config = MCPConfig(server_url="http://mcp:8080")
        with pytest.raises(FrozenInstanceError):
            config.server_url = "http://other:8080"  # type: ignore

    def test_empty_headers_dict(self):
        """Headers can be an empty dict."""
        config = MCPConfig(server_url="http://mcp:8080", headers={})
        assert config.headers == {}


class TestAgentConfig:
    """Tests for AgentConfig dataclass."""

    def test_required_fields(self):
        """Required fields must be provided."""
        config = AgentConfig(
            max_reasoning_steps=10,
            always_visible_tools=frozenset({"tool1", "tool2"}),
            recursion_limit=50,
        )
        assert config.max_reasoning_steps == 10
        assert config.always_visible_tools == {"tool1", "tool2"}
        assert config.recursion_limit == 50

    def test_default_values(self):
        """Optional fields should have correct defaults."""
        config = AgentConfig(
            max_reasoning_steps=10,
            always_visible_tools=frozenset(),
            recursion_limit=50,
        )
        assert config.artifact_threshold == 5000
        assert config.max_context_tokens == 150000

    def test_all_fields(self):
        """All fields can be set explicitly."""
        config = AgentConfig(
            max_reasoning_steps=20,
            always_visible_tools=frozenset({"search", "read"}),
            recursion_limit=100,
            artifact_threshold=10000,
            max_context_tokens=200000,
        )
        assert config.max_reasoning_steps == 20
        assert config.always_visible_tools == {"search", "read"}
        assert config.recursion_limit == 100
        assert config.artifact_threshold == 10000
        assert config.max_context_tokens == 200000

    def test_frozen_immutability(self):
        """AgentConfig should be immutable (frozen)."""
        config = AgentConfig(
            max_reasoning_steps=10,
            always_visible_tools=frozenset(),
            recursion_limit=50,
        )
        with pytest.raises(FrozenInstanceError):
            config.max_reasoning_steps = 20  # type: ignore

    def test_empty_visible_tools_set(self):
        """always_visible_tools can be an empty set."""
        config = AgentConfig(
            max_reasoning_steps=10,
            always_visible_tools=frozenset(),
            recursion_limit=50,
        )
        assert config.always_visible_tools == set()


class TestAgentIdentity:
    """Tests for AgentIdentity dataclass."""

    def test_required_fields(self):
        """All non-defaulted fields are required."""
        identity = AgentIdentity(
            name="Test Agent",
            description="A test agent",
            slug="test-agent",
            squad="platform",
            origin="test-service",
        )
        assert identity.name == "Test Agent"
        assert identity.description == "A test agent"
        assert identity.slug == "test-agent"
        assert identity.squad == "platform"
        assert identity.origin == "test-service"

    def test_default_audience(self):
        """Default audience should be INTERNAL."""
        identity = AgentIdentity(
            name="Test",
            description="Desc",
            slug="test",
            squad="squad",
            origin="origin",
        )
        assert identity.audience == Audience.INTERNAL

    def test_explicit_audience(self):
        """Audience can be set explicitly."""
        for audience in [Audience.CUSTOMER, Audience.INTERNAL, Audience.PUBLIC]:
            identity = AgentIdentity(
                name="Test",
                description="Desc",
                slug="test",
                squad="squad",
                origin="origin",
                audience=audience,
            )
            assert identity.audience == audience

    def test_unique_id_format(self):
        """unique_id should be squad:origin:slug format."""
        identity = AgentIdentity(
            name="Knowledge Agent",
            description="Handles knowledge queries",
            slug="knowledge",
            squad="ai-platform",
            origin="agentic-service",
        )
        assert identity.unique_id == "ai-platform:agentic-service:knowledge"

    def test_unique_id_with_special_characters(self):
        """unique_id handles slugs with hyphens."""
        identity = AgentIdentity(
            name="Test",
            description="Desc",
            slug="my-complex-agent",
            squad="my-squad",
            origin="my-service",
        )
        assert identity.unique_id == "my-squad:my-service:my-complex-agent"

    def test_frozen_immutability(self):
        """AgentIdentity should be immutable (frozen)."""
        identity = AgentIdentity(
            name="Test",
            description="Desc",
            slug="test",
            squad="squad",
            origin="origin",
        )
        with pytest.raises(FrozenInstanceError):
            identity.name = "New Name"  # type: ignore

    def test_equality(self):
        """Two identities with same values should be equal."""
        identity1 = AgentIdentity(
            name="Test",
            description="Desc",
            slug="test",
            squad="squad",
            origin="origin",
        )
        identity2 = AgentIdentity(
            name="Test",
            description="Desc",
            slug="test",
            squad="squad",
            origin="origin",
        )
        assert identity1 == identity2

    def test_inequality_different_slug(self):
        """Identities with different slugs should not be equal."""
        identity1 = AgentIdentity(
            name="Test",
            description="Desc",
            slug="test-1",
            squad="squad",
            origin="origin",
        )
        identity2 = AgentIdentity(
            name="Test",
            description="Desc",
            slug="test-2",
            squad="squad",
            origin="origin",
        )
        assert identity1 != identity2
