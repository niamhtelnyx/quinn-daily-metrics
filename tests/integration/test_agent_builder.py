"""Integration tests for KnowledgeAgentBuilder.

Tests the agent builder class including initialization, build process,
graph structure verification, and tool binding.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import MemorySaver

from my_agentic_serviceservice_order_specialist.agents.knowledge.agent import KnowledgeAgentBuilder
from my_agentic_serviceservice_order_specialist.platform.agent.config import (
    AgentConfig,
    AgentIdentity,
    Audience,
    LlmConfig,
    MCPConfig,
)
from my_agentic_serviceservice_order_specialist.platform.agent.langgraph import LangGraphAgent


class TestKnowledgeAgentBuilderInit:
    """Tests for KnowledgeAgentBuilder initialization."""

    @pytest.fixture
    def agent_config(self) -> AgentConfig:
        """Create a test agent config."""
        return AgentConfig(
            max_reasoning_steps=10,
            artifact_threshold=1000,
            always_visible_tools=frozenset({"inspect_artifact"}),
            recursion_limit=25,
        )

    @pytest.fixture
    def llm_config(self) -> LlmConfig:
        """Create a test LLM config."""
        return LlmConfig(
            model="test-model",
            base_url="http://localhost:8080",
            api_key="test-key",
            temperature=0.5,
        )

    @pytest.fixture
    def mcp_configs(self) -> list[MCPConfig]:
        """Create test MCP configs."""
        return [
            MCPConfig(server_url="http://mcp1/mcp", tool_prefix="mcp1"),
            MCPConfig(server_url="http://mcp2/mcp", tool_prefix="mcp2"),
        ]

    @pytest.fixture
    def checkpointer(self) -> MemorySaver:
        """Create a test checkpointer."""
        return MemorySaver()

    @pytest.fixture
    def identity(self) -> AgentIdentity:
        """Create a test agent identity."""
        return AgentIdentity(
            name="Test Agent",
            slug="test-agent",
            description="A test agent",
            squad="test-squad",
            origin="test-origin",
            audience=Audience.INTERNAL,
        )

    def test_init_stores_agent_config(
        self,
        agent_config: AgentConfig,
        llm_config: LlmConfig,
        mcp_configs: list[MCPConfig],
        checkpointer: MemorySaver,
        identity: AgentIdentity,
    ):
        """Builder stores agent config."""
        builder = KnowledgeAgentBuilder(
            agent_config=agent_config,
            llm_config=llm_config,
            mcp_configs=mcp_configs,
            checkpointer=checkpointer,
            identity=identity,
        )
        assert builder.agent_config is agent_config

    def test_init_stores_llm_config(
        self,
        agent_config: AgentConfig,
        llm_config: LlmConfig,
        mcp_configs: list[MCPConfig],
        checkpointer: MemorySaver,
        identity: AgentIdentity,
    ):
        """Builder stores LLM config."""
        builder = KnowledgeAgentBuilder(
            agent_config=agent_config,
            llm_config=llm_config,
            mcp_configs=mcp_configs,
            checkpointer=checkpointer,
            identity=identity,
        )
        assert builder.llm_config is llm_config

    def test_init_stores_mcp_configs(
        self,
        agent_config: AgentConfig,
        llm_config: LlmConfig,
        mcp_configs: list[MCPConfig],
        checkpointer: MemorySaver,
        identity: AgentIdentity,
    ):
        """Builder stores MCP configs."""
        builder = KnowledgeAgentBuilder(
            agent_config=agent_config,
            llm_config=llm_config,
            mcp_configs=mcp_configs,
            checkpointer=checkpointer,
            identity=identity,
        )
        assert builder.mcp_configs is mcp_configs

    def test_init_stores_checkpointer(
        self,
        agent_config: AgentConfig,
        llm_config: LlmConfig,
        mcp_configs: list[MCPConfig],
        checkpointer: MemorySaver,
        identity: AgentIdentity,
    ):
        """Builder stores checkpointer."""
        builder = KnowledgeAgentBuilder(
            agent_config=agent_config,
            llm_config=llm_config,
            mcp_configs=mcp_configs,
            checkpointer=checkpointer,
            identity=identity,
        )
        assert builder.checkpointer is checkpointer

    def test_init_stores_identity(
        self,
        agent_config: AgentConfig,
        llm_config: LlmConfig,
        mcp_configs: list[MCPConfig],
        checkpointer: MemorySaver,
        identity: AgentIdentity,
    ):
        """Builder stores identity."""
        builder = KnowledgeAgentBuilder(
            agent_config=agent_config,
            llm_config=llm_config,
            mcp_configs=mcp_configs,
            checkpointer=checkpointer,
            identity=identity,
        )
        assert builder.identity is identity

    def test_init_uses_custom_tool_fetcher(
        self,
        agent_config: AgentConfig,
        llm_config: LlmConfig,
        mcp_configs: list[MCPConfig],
        checkpointer: MemorySaver,
        identity: AgentIdentity,
    ):
        """Builder uses custom tool fetcher when provided."""
        custom_fetcher = AsyncMock(return_value=[])
        builder = KnowledgeAgentBuilder(
            agent_config=agent_config,
            llm_config=llm_config,
            mcp_configs=mcp_configs,
            checkpointer=checkpointer,
            identity=identity,
            tool_fetcher=custom_fetcher,
        )
        assert builder._fetch_tools is custom_fetcher


class TestKnowledgeAgentBuilderDefaultBuilder:
    """Tests for KnowledgeAgentBuilder.default_builder() class method."""

    @pytest.fixture
    def checkpointer(self) -> MemorySaver:
        """Create a test checkpointer."""
        return MemorySaver()

    @pytest.fixture
    def mcp_configs(self) -> list[MCPConfig]:
        """Create test MCP configs."""
        return [MCPConfig(server_url="http://mcp/mcp")]

    def test_default_builder_creates_builder(
        self, checkpointer: MemorySaver, mcp_configs: list[MCPConfig]
    ):
        """default_builder creates a KnowledgeAgentBuilder instance."""
        builder = KnowledgeAgentBuilder.default_builder(
            llm_base_url="http://localhost:8080",
            llm_api_key="test-key",
            checkpointer=checkpointer,
            mcp_configs=mcp_configs,
        )
        assert isinstance(builder, KnowledgeAgentBuilder)

    def test_default_builder_sets_llm_config(
        self, checkpointer: MemorySaver, mcp_configs: list[MCPConfig]
    ):
        """default_builder sets LLM config with provided values."""
        builder = KnowledgeAgentBuilder.default_builder(
            llm_base_url="http://localhost:8080",
            llm_api_key="my-api-key",
            checkpointer=checkpointer,
            mcp_configs=mcp_configs,
        )
        assert builder.llm_config.base_url == "http://localhost:8080"
        assert builder.llm_config.api_key == "my-api-key"

    def test_default_builder_uses_default_identity(
        self, checkpointer: MemorySaver, mcp_configs: list[MCPConfig]
    ):
        """default_builder uses default identity when not provided."""
        builder = KnowledgeAgentBuilder.default_builder(
            llm_base_url="http://localhost:8080",
            llm_api_key="test-key",
            checkpointer=checkpointer,
            mcp_configs=mcp_configs,
        )
        assert builder.identity.name == "Knowledge"
        assert builder.identity.slug == "knowledge"

    def test_default_builder_uses_custom_identity(
        self, checkpointer: MemorySaver, mcp_configs: list[MCPConfig]
    ):
        """default_builder uses custom identity when provided."""
        custom_identity = AgentIdentity(
            name="Custom Agent",
            slug="custom",
            description="Custom description",
            squad="custom-squad",
            origin="custom-origin",
        )
        builder = KnowledgeAgentBuilder.default_builder(
            llm_base_url="http://localhost:8080",
            llm_api_key="test-key",
            checkpointer=checkpointer,
            mcp_configs=mcp_configs,
            identity=custom_identity,
        )
        assert builder.identity is custom_identity

    def test_default_builder_sets_agent_config(
        self, checkpointer: MemorySaver, mcp_configs: list[MCPConfig]
    ):
        """default_builder sets default agent config values."""
        builder = KnowledgeAgentBuilder.default_builder(
            llm_base_url="http://localhost:8080",
            llm_api_key="test-key",
            checkpointer=checkpointer,
            mcp_configs=mcp_configs,
        )
        assert builder.agent_config.max_reasoning_steps == 15
        assert builder.agent_config.artifact_threshold == 5000
        assert builder.agent_config.recursion_limit == 50


class TestKnowledgeAgentBuilderBuild:
    """Tests for KnowledgeAgentBuilder.build() method."""

    @pytest.fixture
    def stub_tools(self) -> list[StructuredTool]:
        """Create stub tools with canned implementations."""

        def search_fn(query: str) -> str:
            return f"Results for: {query}"

        def fetch_fn(url: str) -> str:
            return f"Content from: {url}"

        return [
            StructuredTool.from_function(
                func=search_fn,
                name="mcp_search",
                description="Search for information",
            ),
            StructuredTool.from_function(
                func=fetch_fn,
                name="mcp_fetch",
                description="Fetch a URL",
            ),
        ]

    @pytest.fixture
    def builder_with_stub_tools(self, stub_tools: list[StructuredTool]):
        """Create a builder with stubbed tool fetcher."""
        checkpointer = MemorySaver()
        identity = AgentIdentity(
            name="Test Agent",
            slug="test-agent",
            description="A test agent",
            squad="test-squad",
            origin="test-origin",
        )
        return KnowledgeAgentBuilder(
            agent_config=AgentConfig(
                max_reasoning_steps=10,
                artifact_threshold=1000,
                always_visible_tools=frozenset({"inspect_artifact"}),
                recursion_limit=25,
            ),
            llm_config=LlmConfig(
                model="test-model",
                base_url="http://localhost:8080",
                api_key="test-key",
                temperature=0.5,
            ),
            mcp_configs=[MCPConfig(server_url="http://mcp/mcp")],
            checkpointer=checkpointer,
            identity=identity,
            tool_fetcher=AsyncMock(return_value=stub_tools),
        )

    async def test_build_returns_langgraph_agent(
        self, builder_with_stub_tools: KnowledgeAgentBuilder
    ):
        """build() returns a LangGraphAgent instance."""
        agent = await builder_with_stub_tools.build()
        assert isinstance(agent, LangGraphAgent)

    async def test_build_agent_has_identity(self, builder_with_stub_tools: KnowledgeAgentBuilder):
        """Built agent has the configured identity."""
        agent = await builder_with_stub_tools.build()
        assert agent.identity.name == "Test Agent"
        assert agent.identity.slug == "test-agent"

    async def test_build_agent_has_tools(self, builder_with_stub_tools: KnowledgeAgentBuilder):
        """Built agent has tools including inspect_artifact."""
        agent = await builder_with_stub_tools.build()
        tool_names = [t.name for t in agent.tools]
        # Should have MCP tools plus inspect_artifact
        assert "mcp_search" in tool_names
        assert "mcp_fetch" in tool_names
        assert "inspect_artifact" in tool_names

    async def test_build_calls_tool_fetcher(self, builder_with_stub_tools: KnowledgeAgentBuilder):
        """build() calls the tool fetcher with MCP configs."""
        await builder_with_stub_tools.build()
        builder_with_stub_tools._fetch_tools.assert_called_once_with(  # type: ignore[union-attr]
            builder_with_stub_tools.mcp_configs
        )

    async def test_build_agent_graph_has_nodes(
        self, builder_with_stub_tools: KnowledgeAgentBuilder
    ):
        """Built agent graph has reasoner and tools nodes."""
        agent = await builder_with_stub_tools.build()
        # Access the underlying graph nodes
        graph_nodes = agent._graph.nodes
        assert "reasoner" in graph_nodes
        assert "tools" in graph_nodes


class TestKnowledgeAgentBuilderBuildInitialState:
    """Tests for KnowledgeAgentBuilder.build_initial_state() static method."""

    def test_build_initial_state_returns_agent_state(self):
        """build_initial_state returns an AgentState dict."""
        state = KnowledgeAgentBuilder.build_initial_state("Hello")
        assert "messages" in state
        assert "reasoning_steps" in state
        assert "thread_id" in state

    def test_build_initial_state_includes_user_message(self):
        """State includes the user message."""
        state = KnowledgeAgentBuilder.build_initial_state("What is Python?")
        messages = state["messages"]
        # Should have system message and human message
        assert len(messages) == 2
        assert isinstance(messages[1], HumanMessage)
        assert "What is Python?" in messages[1].content

    def test_build_initial_state_includes_system_message(self):
        """State includes a system message."""
        state = KnowledgeAgentBuilder.build_initial_state("Hello")
        messages = state["messages"]
        assert isinstance(messages[0], SystemMessage)

    def test_build_initial_state_uses_provided_thread_id(self):
        """State uses the provided thread_id."""
        state = KnowledgeAgentBuilder.build_initial_state("Hello", thread_id="custom-thread-123")
        assert state["thread_id"] == "custom-thread-123"

    def test_build_initial_state_generates_thread_id(self):
        """State generates a thread_id when not provided."""
        state = KnowledgeAgentBuilder.build_initial_state("Hello")
        assert state["thread_id"] is not None
        assert len(state["thread_id"]) > 0

    def test_build_initial_state_reasoning_steps_zero(self):
        """State starts with zero reasoning steps."""
        state = KnowledgeAgentBuilder.build_initial_state("Hello")
        assert state["reasoning_steps"] == 0

    def test_build_initial_state_empty_token_dicts(self):
        """State starts with empty token tracking dicts."""
        state = KnowledgeAgentBuilder.build_initial_state("Hello")
        assert state["input_tokens_by_model"] == {}
        assert state["output_tokens_by_model"] == {}

    def test_build_initial_state_uses_provided_utc_now(self):
        """State uses the provided UTC time."""
        utc_now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
        state = KnowledgeAgentBuilder.build_initial_state("Hello", utc_now=utc_now)
        messages = state["messages"]
        assert "2025-06-15" in messages[1].content

    def test_build_initial_state_uses_current_time_when_not_provided(self):
        """State uses current time when utc_now not provided."""
        state = KnowledgeAgentBuilder.build_initial_state("Hello")
        messages = state["messages"]
        # Should contain a date string
        assert "UTC Now:" in messages[1].content


class TestKnowledgeAgentBuilderSlug:
    """Tests for KnowledgeAgentBuilder class constant."""

    def test_slug_constant(self):
        """Builder has correct SLUG constant."""
        assert KnowledgeAgentBuilder.SLUG == "knowledge"
