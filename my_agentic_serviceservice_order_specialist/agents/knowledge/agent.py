"""LangGraph ReAct agent builder module.

This module provides the builder class for constructing LangGraph-based ReAct agents
with MCP tool integration, artifact handling, and conversation persistence.
"""

import uuid
from datetime import UTC, datetime
from typing import Self

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition

from my_agentic_serviceservice_order_specialist.agents.knowledge.nodes import (
    ReasonerNode,
    ToolNodeFactory,
)
from my_agentic_serviceservice_order_specialist.agents.knowledge.prompt import build_system_prompt
from my_agentic_serviceservice_order_specialist.agents.knowledge.state import AgentState
from my_agentic_serviceservice_order_specialist.agents.knowledge.tools.inspect_artifact import (
    create_inspect_artifact_tool,
)
from my_agentic_serviceservice_order_specialist.platform.agent.config import (
    A2AConfig,
    AgentConfig,
    AgentIdentity,
    LlmConfig,
    MCPConfig,
)
from my_agentic_serviceservice_order_specialist.platform.agent.langgraph import (
    A2AToolFetcher,
    LangGraphA2ATools,
    LangGraphAgent,
    LangGraphMCPTools,
    ToolFetcher,
)
from my_agentic_serviceservice_order_specialist.platform.agent.llm_client import LlmClient
from my_agentic_serviceservice_order_specialist.platform.constants import SERVICE_NAME, SQUAD_NAME


class KnowledgeAgentBuilder:
    """Builder for constructing LangGraph-based Knowledge agents.

    This builder assembles all components needed for a Knowledge agent:
    - LLM client with tool bindings
    - MCP clients for tool discovery and execution (supports multiple servers)
    - Reasoner node for the agent graph
    - Checkpointer for conversation persistence
    """

    SLUG = "knowledge"

    def __init__(
        self,
        agent_config: AgentConfig,
        llm_config: LlmConfig,
        mcp_configs: list[MCPConfig],
        checkpointer: BaseCheckpointSaver,
        identity: AgentIdentity,
        tool_fetcher: ToolFetcher | None = None,
        a2a_configs: list[A2AConfig] | None = None,
        a2a_tool_fetcher: A2AToolFetcher | None = None,
    ) -> None:
        """Initialize the builder with configuration.

        Args:
            agent_config: Configuration for agent behavior (steps, thresholds, etc.)
            llm_config: Configuration for the LLM client
            mcp_configs: List of MCP server configurations for tool discovery
            checkpointer: LangGraph checkpointer for conversation persistence
            identity: Agent identity (name, description, slug, squad)
            tool_fetcher: Optional callable for fetching tools from MCP configs.
                Defaults to LangGraphMCPTools.fetch_all. Inject for testing.
            a2a_configs: Optional list of A2A remote agent configurations.
            a2a_tool_fetcher: Optional callable for fetching tools from A2A configs.
                Defaults to LangGraphA2ATools.fetch_all. Inject for testing.
        """
        self.agent_config = agent_config
        self.llm_config = llm_config
        self.mcp_configs = mcp_configs
        self.checkpointer = checkpointer
        self.identity = identity
        self._fetch_tools = tool_fetcher or LangGraphMCPTools.fetch_all
        self.a2a_configs = a2a_configs or []
        self._fetch_a2a_tools = a2a_tool_fetcher or LangGraphA2ATools.fetch_all

    async def build(self) -> LangGraphAgent:
        """Build and return a configured LangGraphAgent.

        Assembles the agent graph with reasoner and tool nodes, binds tools to the LLM,
        and configures the checkpointer for conversation persistence.

        Returns:
            A fully configured LangGraphAgent ready for execution.
        """
        llm_client = LlmClient(
            agent_slug=self.identity.slug,
            model_name=self.llm_config.model,
            api_key=self.llm_config.api_key,
            api_base=self.llm_config.base_url,
            temperature=self.llm_config.temperature,
        )

        # Gather tools from all MCP servers concurrently
        all_tools = await self._fetch_tools(self.mcp_configs)

        # Gather tools from all A2A remote agents concurrently
        if self.a2a_configs:
            a2a_tools = await self._fetch_a2a_tools(self.a2a_configs)
            all_tools.extend(a2a_tools)

        all_tools.append(create_inspect_artifact_tool())
        llm_with_tools = llm_client.bind_tools(all_tools)

        reasoner_node = ReasonerNode(llm_with_tools, self.agent_config)  # type: ignore
        tool_node = ToolNodeFactory(self.agent_config, self.identity.slug).create(all_tools)

        workflow = StateGraph(AgentState)  # type: ignore[bad-specialization]

        workflow.add_node("reasoner", reasoner_node)  # type: ignore
        workflow.add_node("tools", tool_node)  # type: ignore

        workflow.add_edge(START, "reasoner")  # type: ignore
        workflow.add_conditional_edges("reasoner", tools_condition)
        workflow.add_edge("tools", "reasoner")  # type: ignore

        compiled = workflow.compile(checkpointer=self.checkpointer)
        return LangGraphAgent(
            graph=compiled.with_config({"recursion_limit": self.agent_config.recursion_limit}),
            identity=self.identity,
            initial_state_builder=self.build_initial_state,  # type: ignore
            tools=all_tools,
        )

    @classmethod
    def default_builder(
        cls,
        llm_base_url: str,
        llm_api_key: str,
        checkpointer: BaseCheckpointSaver,
        mcp_configs: list[MCPConfig],
        identity: AgentIdentity | None = None,
        a2a_configs: list[A2AConfig] | None = None,
    ) -> Self:
        """Create a builder with default configuration for a Knowledge agent.

        Args:
            llm_base_url: Base URL for the LiteLLM proxy
            llm_api_key: API key for the LiteLLM proxy
            checkpointer: LangGraph checkpointer for conversation persistence
            mcp_configs: List of MCP server configurations for tool discovery
            identity: Optional agent identity. Defaults to Knowledge agent.
            a2a_configs: Optional list of A2A remote agent configurations.

        Returns:
            A configured KnowledgeAgentBuilder instance.
        """
        default_identity = AgentIdentity(
            name="Knowledge",
            description="A knowledge-based agent that can answer questions and perform tasks",
            slug=cls.SLUG,
            squad=SQUAD_NAME,
            origin=SERVICE_NAME,
        )
        return cls(
            agent_config=AgentConfig(
                # Maximum LLM calls before forcing completion to prevent infinite loops
                # and control costs. 15 allows complex multi-step reasoning while
                # limiting runaway executions.
                max_reasoning_steps=15,
                # Tool outputs larger than this (in chars) are stored as artifacts
                # and replaced with a reference. 5000 chars balances context usage
                # with tool output visibility.
                artifact_threshold=5000,
                # Tools that should never be hidden by the artifact pattern,
                # ensuring the LLM can always inspect stored artifacts.
                always_visible_tools=frozenset({"inspect_artifact"}),
                # MCP tools with these suffixes are never hidden (handles prefixed names
                # like mcp_myprefix_fetch_relevant_tools)
                always_visible_tool_suffixes=frozenset({"_fetch_relevant_tools"}),
                # LangGraph recursion limit for graph traversal. 50 provides headroom
                # for complex tool chains while preventing stack overflow.
                recursion_limit=50,
            ),
            llm_config=LlmConfig(
                model="litellm_proxy/anthropic/claude-sonnet-4-5",
                base_url=llm_base_url,
                api_key=llm_api_key,
                temperature=0.7,
            ),
            mcp_configs=mcp_configs,
            checkpointer=checkpointer,
            identity=identity or default_identity,
            a2a_configs=a2a_configs,
        )

    @classmethod
    def build_initial_state(
        cls,
        message: str,
        thread_id: str | None = None,
        utc_now: datetime | None = None,
    ) -> AgentState:
        """Get the initial state for the agent.

        Args:
            message: User's input message
            thread_id: Thread ID for conversation persistence, if None, a new thread will be created
            utc_now: Optional UTC now time, if None, the current time will be used

        Returns:
            Initial agent state dictionary containing messages and metadata
        """
        thread_id = thread_id or str(uuid.uuid4())
        utc_now = utc_now or datetime.now(UTC)
        system_msg = SystemMessage(content=build_system_prompt())
        user_msg = HumanMessage(
            content=f"UTC Now: {utc_now.isoformat()}\n\nUser Inquiry: {message}"
        )

        return AgentState(
            messages=[system_msg, user_msg],
            reasoning_steps=0,
            thread_id=thread_id,
            agent_slug=cls.SLUG,
            input_tokens_by_model={},
            output_tokens_by_model={},
        )
