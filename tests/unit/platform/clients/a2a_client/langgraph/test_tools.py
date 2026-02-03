"""Unit tests for A2A LangGraph tool wrappers."""

from unittest.mock import AsyncMock, patch

import pytest
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from pydantic import BaseModel

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import A2AClientConfig, AuthConfig
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.tools import (
    A2AToolConfig,
    _build_agent_description,
    _json_schema_to_pydantic_model,
    _json_schema_type_to_python,
    create_a2a_tool,
    create_tool_from_agent_card,
)


class TestA2AToolConfig:
    """Tests for A2AToolConfig dataclass."""

    def test_required_base_url(self):
        """A2AToolConfig requires base_url."""
        config = A2AToolConfig(base_url="http://agent.example.com")
        assert config.base_url == "http://agent.example.com"

    def test_default_values(self):
        """A2AToolConfig has correct defaults."""
        config = A2AToolConfig(base_url="http://example.com")
        assert config.skill_id is None
        assert config.name_override is None
        assert config.description_override is None
        assert config.client_config is None
        assert config.auth is None

    def test_full_config(self):
        """A2AToolConfig accepts all values."""
        client_config = A2AClientConfig(timeout_seconds=30.0)
        auth = AuthConfig(api_key="test-key")

        config = A2AToolConfig(
            base_url="http://agent.example.com",
            skill_id="skill-1",
            name_override="my_tool",
            description_override="My custom tool",
            client_config=client_config,
            auth=auth,
        )

        assert config.skill_id == "skill-1"
        assert config.name_override == "my_tool"
        assert config.description_override == "My custom tool"
        assert config.client_config is client_config
        assert config.auth is auth


class TestJsonSchemaTypeConversion:
    """Tests for _json_schema_type_to_python()."""

    def test_string_type(self):
        """Converts string type."""
        result = _json_schema_type_to_python({"type": "string"})
        assert result is str

    def test_integer_type(self):
        """Converts integer type."""
        result = _json_schema_type_to_python({"type": "integer"})
        assert result is int

    def test_number_type(self):
        """Converts number type."""
        result = _json_schema_type_to_python({"type": "number"})
        assert result is float

    def test_boolean_type(self):
        """Converts boolean type."""
        result = _json_schema_type_to_python({"type": "boolean"})
        assert result is bool

    def test_array_type(self):
        """Converts array type."""
        result = _json_schema_type_to_python({"type": "array"})
        assert result is list

    def test_object_type(self):
        """Converts object type."""
        result = _json_schema_type_to_python({"type": "object"})
        assert result is dict

    def test_unknown_type_defaults_to_string(self):
        """Unknown types default to string."""
        result = _json_schema_type_to_python({"type": "unknown"})
        assert result is str

    def test_missing_type_defaults_to_string(self):
        """Missing type defaults to string."""
        result = _json_schema_type_to_python({})
        assert result is str


class TestJsonSchemaToPydanticModel:
    """Tests for _json_schema_to_pydantic_model()."""

    def test_none_schema_creates_query_model(self):
        """None schema creates model with query field."""
        model = _json_schema_to_pydantic_model("TestModel", None)

        assert issubclass(model, BaseModel)
        assert "query" in model.model_fields
        assert model.model_fields["query"].annotation is str

    def test_empty_properties_creates_query_model(self):
        """Empty properties creates model with query field."""
        schema = {"type": "object", "properties": {}}
        model = _json_schema_to_pydantic_model("TestModel", schema)

        assert "query" in model.model_fields

    def test_creates_required_fields(self):
        """Creates required fields from schema."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "User name"},
            },
            "required": ["name"],
        }
        model = _json_schema_to_pydantic_model("TestModel", schema)

        assert "name" in model.model_fields
        field = model.model_fields["name"]
        assert field.is_required() is True

    def test_creates_optional_fields(self):
        """Creates optional fields from schema."""
        schema = {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Result limit"},
            },
            "required": [],
        }
        model = _json_schema_to_pydantic_model("TestModel", schema)

        assert "limit" in model.model_fields
        field = model.model_fields["limit"]
        assert field.is_required() is False

    def test_uses_default_values(self):
        """Uses default values from schema."""
        schema = {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Count",
                    "default": 10,
                },
            },
        }
        model = _json_schema_to_pydantic_model("TestModel", schema)

        assert model.model_fields["count"].default == 10


class TestCreateA2ATool:
    """Tests for create_a2a_tool()."""

    @pytest.fixture
    def sample_agent_card(self):
        """Create a sample AgentCard with skills."""
        return AgentCard(
            name="Test Agent",
            description="A test agent",
            url="http://agent.example.com/a2a",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=True),
            skills=[
                AgentSkill(
                    id="skill-1",
                    name="Search Skill",
                    description="Search for information",
                    tags=["search"],
                    input_modes=None,
                    output_modes=None,
                ),
                AgentSkill(
                    id="skill-2",
                    name="Calculate",
                    description="Perform calculations",
                    tags=["math"],
                    input_modes=None,
                    output_modes=None,
                ),
            ],
            default_input_modes=["text"],
            default_output_modes=["text"],
        )

    def test_creates_tool_without_agent_card(self):
        """create_a2a_tool creates tool with defaults when no card."""
        config = A2AToolConfig(base_url="http://example.com")

        tool = create_a2a_tool(config)

        # Without agent card, uses "remote" as prefix fallback
        assert tool.name == "a2a_remote_agent"
        assert tool.description == "Send a message to the A2A agent"

    def test_creates_tool_with_skill_from_card(self, sample_agent_card):
        """create_a2a_tool uses first skill from agent card."""
        config = A2AToolConfig(base_url="http://example.com")

        tool = create_a2a_tool(config, agent_card=sample_agent_card)

        # Prefix derived from agent card name "Test Agent" -> "test_agent"
        assert tool.name == "a2a_test_agent_search_skill"
        assert tool.description == "Search for information"

    def test_creates_tool_with_specific_skill(self, sample_agent_card):
        """create_a2a_tool can select specific skill by ID."""
        config = A2AToolConfig(
            base_url="http://example.com",
            skill_id="skill-2",
        )

        tool = create_a2a_tool(config, agent_card=sample_agent_card)

        # Prefix derived from agent card name "Test Agent" -> "test_agent"
        assert tool.name == "a2a_test_agent_calculate"
        assert tool.description == "Perform calculations"

    def test_uses_name_override(self, sample_agent_card):
        """create_a2a_tool uses name_override when provided."""
        config = A2AToolConfig(
            base_url="http://example.com",
            name_override="my_custom_tool",
        )

        tool = create_a2a_tool(config, agent_card=sample_agent_card)

        assert tool.name == "my_custom_tool"

    def test_uses_description_override(self, sample_agent_card):
        """create_a2a_tool uses description_override when provided."""
        config = A2AToolConfig(
            base_url="http://example.com",
            description_override="Custom description",
        )

        tool = create_a2a_tool(config, agent_card=sample_agent_card)

        assert tool.description == "Custom description"

    def test_tool_name_is_normalized(self, sample_agent_card):
        """create_a2a_tool normalizes tool name."""
        sample_agent_card.skills[0].name = "My Search-Tool"
        config = A2AToolConfig(base_url="http://example.com")

        tool = create_a2a_tool(config, agent_card=sample_agent_card)

        # Prefix derived from agent card name "Test Agent" -> "test_agent"
        assert tool.name == "a2a_test_agent_my_search_tool"

    def test_uses_explicit_tool_prefix(self, sample_agent_card):
        """create_a2a_tool uses explicit tool_prefix when provided."""
        config = A2AToolConfig(
            base_url="http://example.com",
            tool_prefix="custom_prefix",
        )

        tool = create_a2a_tool(config, agent_card=sample_agent_card)

        assert tool.name == "a2a_custom_prefix_search_skill"


class TestBuildAgentDescription:
    """Tests for _build_agent_description()."""

    def test_builds_description_with_skills(self):
        """_build_agent_description includes agent description and skills."""
        card = AgentCard(
            name="Test Agent",
            description="A test agent for searching",
            url="http://example.com",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=True),
            skills=[
                AgentSkill(
                    id="skill-1",
                    name="Search",
                    description="Search for information",
                    tags=["search"],
                    input_modes=None,
                    output_modes=None,
                ),
                AgentSkill(
                    id="skill-2",
                    name="Calculate",
                    description="Perform calculations",
                    tags=["math"],
                    input_modes=None,
                    output_modes=None,
                ),
            ],
            default_input_modes=["text"],
            default_output_modes=["text"],
        )

        description = _build_agent_description(card)

        assert "A test agent for searching" in description
        assert "Capabilities:" in description
        assert "- Search: Search for information" in description
        assert "- Calculate: Perform calculations" in description

    def test_builds_description_without_skills(self):
        """_build_agent_description handles no skills."""
        card = AgentCard(
            name="Simple Agent",
            description="A simple agent",
            url="http://example.com",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=False),
            skills=[],
            default_input_modes=["text"],
            default_output_modes=["text"],
        )

        description = _build_agent_description(card)

        assert description == "A simple agent"
        assert "Capabilities:" not in description


class TestCreateToolFromAgentCard:
    """Tests for create_tool_from_agent_card()."""

    @pytest.fixture
    def sample_agent_card(self):
        """Create a sample AgentCard with skills."""
        return AgentCard(
            name="Test Agent",
            description="A test agent",
            url="http://agent.example.com/a2a",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=True),
            skills=[
                AgentSkill(
                    id="skill-1",
                    name="Search",
                    description="Search for information",
                    tags=["search", "query"],
                    input_modes=None,
                    output_modes=None,
                ),
                AgentSkill(
                    id="skill-2",
                    name="Calculate",
                    description="Perform calculations",
                    tags=["math"],
                    input_modes=None,
                    output_modes=None,
                ),
            ],
            default_input_modes=["text"],
            default_output_modes=["text"],
        )

    async def test_creates_single_tool_for_agent(self, sample_agent_card):
        """create_tool_from_agent_card creates one tool per agent."""
        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.tools.A2AClientWrapper"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get_agent_card = AsyncMock(return_value=sample_agent_card)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            tool = await create_tool_from_agent_card("http://example.com")

            assert tool.name == "a2a_test_agent"
            assert "A test agent" in tool.description
            assert "Capabilities:" in tool.description
            assert "- Search: Search for information" in tool.description
            assert "- Calculate: Perform calculations" in tool.description

    async def test_tool_has_query_input(self, sample_agent_card):
        """create_tool_from_agent_card creates tool with query input."""
        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.tools.A2AClientWrapper"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get_agent_card = AsyncMock(return_value=sample_agent_card)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            tool = await create_tool_from_agent_card("http://example.com")

            assert tool.args_schema is not None
            schema = tool.args_schema
            assert isinstance(schema, type) and issubclass(schema, BaseModel)
            assert "query" in schema.model_fields

    async def test_uses_name_override(self, sample_agent_card):
        """create_tool_from_agent_card uses name_override when provided."""
        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.tools.A2AClientWrapper"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get_agent_card = AsyncMock(return_value=sample_agent_card)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            tool = await create_tool_from_agent_card(
                "http://example.com",
                name_override="custom_tool",
            )

            assert tool.name == "custom_tool"

    async def test_uses_description_override(self, sample_agent_card):
        """create_tool_from_agent_card uses description_override when provided."""
        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.tools.A2AClientWrapper"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get_agent_card = AsyncMock(return_value=sample_agent_card)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            tool = await create_tool_from_agent_card(
                "http://example.com",
                description_override="Custom description",
            )

            assert tool.description == "Custom description"

    async def test_creates_tool_when_no_skills(self):
        """create_tool_from_agent_card creates tool when agent has no skills."""
        card_without_skills = AgentCard(
            name="Simple Agent",
            description="A simple agent",
            url="http://example.com",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=False),
            skills=[],
            default_input_modes=["text"],
            default_output_modes=["text"],
        )

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.tools.A2AClientWrapper"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get_agent_card = AsyncMock(return_value=card_without_skills)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            tool = await create_tool_from_agent_card("http://example.com")

            assert tool.name == "a2a_simple_agent"
            assert tool.description == "A simple agent"
