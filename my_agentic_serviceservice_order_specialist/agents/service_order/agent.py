"""Service Order Operations Agent.

This module provides a specialized agent for handling Telnyx Service Order operations,
including PDF parsing, Salesforce integration, and Commitment Manager workflows.
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
from my_agentic_serviceservice_order_specialist.agents.service_order.prompt import build_system_prompt
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


# A2A Skills that other agents can request from this Service Order agent
A2A_SKILLS = [
    {
        "id": "process-service-order",
        "name": "Process Service Order", 
        "description": "Complete end-to-end Service Order processing: parse PDF → validate Salesforce → get approval → send to Commitment Manager",
        "inputModes": ["file", "text"],
        "outputModes": ["text", "structured"]
    },
    {
        "id": "analyze-billing-discrepancy", 
        "name": "Analyze Billing Discrepancy",
        "description": "Investigate billing questions by cross-referencing Service Orders, Salesforce data, and Commitment Manager records",
        "inputModes": ["text"],
        "outputModes": ["text"]
    },
    {
        "id": "validate-salesforce-entry",
        "name": "Validate Salesforce Entry",
        "description": "Verify Service Order is correctly logged in Salesforce against source document",
        "inputModes": ["text"],
        "outputModes": ["text", "structured"]
    },
    {
        "id": "explain-commitment-changes",
        "name": "Explain Commitment Changes",
        "description": "Analyze why a customer's commitment or billing changed based on Service Order history",
        "inputModes": ["text"],
        "outputModes": ["text"]
    }
]


class ServiceOrderAgentBuilder:
    """Builder for constructing Service Order Operations agents.

    This builder creates specialized agents for handling Telnyx Service Orders with
    integrated PDF parsing, Salesforce validation, and Commitment Manager workflows.
    """

    SLUG = "service-order"

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
        """Initialize the Service Order agent builder with configuration.

        Args:
            agent_config: Configuration for agent behavior (steps, thresholds, etc.)
            llm_config: Configuration for the LLM client
            mcp_configs: List of MCP server configurations for tool discovery
            checkpointer: LangGraph checkpointer for conversation persistence
            identity: Agent identity (name, description, slug, squad)
            tool_fetcher: Optional callable for fetching tools from MCP configs
            a2a_configs: Optional list of A2A remote agent configurations
            a2a_tool_fetcher: Optional callable for fetching tools from A2A configs
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
        """Build and return a configured Service Order Agent.

        Returns:
            A fully configured Service Order LangGraphAgent ready for execution.
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
        """Create a builder with default configuration for a Service Order agent.

        Args:
            llm_base_url: Base URL for the LiteLLM proxy
            llm_api_key: API key for the LiteLLM proxy
            checkpointer: LangGraph checkpointer for conversation persistence
            mcp_configs: List of MCP server configurations for tool discovery
            identity: Optional agent identity. Defaults to Service Order agent.
            a2a_configs: Optional list of A2A remote agent configurations.

        Returns:
            A configured ServiceOrderAgentBuilder instance.
        """
        default_identity = AgentIdentity(
            name="Service Order Operations",
            description="Specialized agent for Telnyx Service Order operations: PDF parsing, Salesforce validation, Commitment Manager workflows, and billing analysis",
            slug=cls.SLUG,
            squad=SQUAD_NAME,
            origin=SERVICE_NAME,
        )
        return cls(
            agent_config=AgentConfig(
                # Service Orders can involve complex multi-step workflows
                max_reasoning_steps=20,
                # Large PDF content and Salesforce data may need artifact storage
                artifact_threshold=3000,
                # Essential tools for Service Order operations
                always_visible_tools=frozenset({"inspect_artifact", "parse_service_order", "validate_salesforce_entry"}),
                always_visible_tool_suffixes=frozenset({"_fetch_relevant_tools", "_commitment_manager"}),
                recursion_limit=60,  # Higher limit for complex Service Order workflows
            ),
            llm_config=LlmConfig(
                model="litellm_proxy/anthropic/claude-sonnet-4-5",
                base_url=llm_base_url,
                api_key=llm_api_key,
                temperature=0.3,  # Lower temperature for more consistent business operations
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
        """Get the initial state for the Service Order agent.

        Args:
            message: User's input message
            thread_id: Thread ID for conversation persistence
            utc_now: Optional UTC now time

        Returns:
            Initial agent state for Service Order operations
        """
        thread_id = thread_id or str(uuid.uuid4())
        utc_now = utc_now or datetime.now(UTC)
        system_msg = SystemMessage(content=build_system_prompt())
        user_msg = HumanMessage(
            content=f"UTC Now: {utc_now.isoformat()}\n\nService Order Request: {message}"
        )

        return AgentState(
            messages=[system_msg, user_msg],
            reasoning_steps=0,
            thread_id=thread_id,
            agent_slug=cls.SLUG,
            input_tokens_by_model={},
            output_tokens_by_model={},
        )