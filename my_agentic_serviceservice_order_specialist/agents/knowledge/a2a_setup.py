"""A2A registration for Knowledge agent.

This module provides a factory function that handles the complete lifecycle
of creating a Knowledge agent and mounting it to the FastAPI application.
"""

from a2a.server.tasks import TaskStore
from a2a.types import AgentCard
from fastapi import FastAPI

from my_agentic_serviceservice_order_specialist.agents.knowledge.agent import KnowledgeAgentBuilder
from my_agentic_serviceservice_order_specialist.agents.knowledge.card import KnowledgeAgentCardBuilder
from my_agentic_serviceservice_order_specialist.platform.agent.a2a import create_a2a_application
from my_agentic_serviceservice_order_specialist.platform.agent.config import A2AConfig, AgentIdentity, MCPConfig
from my_agentic_serviceservice_order_specialist.platform.agent.protocol import Agent
from my_agentic_serviceservice_order_specialist.platform.agent.registration import ToolInfo


async def build_and_mount_knowledge_agent(
    app: FastAPI,
    task_store: TaskStore,
) -> tuple[type, Agent, AgentCard, AgentIdentity, list[ToolInfo]]:
    """Build the Knowledge agent and mount its A2A routes.

    Args:
        app: FastAPI application with initialized db_engine, db_checkpointer, and settings
        task_store: Shared TaskStore for A2A task management

    Returns:
        Tuple of (builder_class, agent, AgentCard, AgentIdentity, tools) for use in
        service registration and agent caching
    """
    settings = app.state.settings

    mcp_configs = [
        MCPConfig(
            server_url=s.url,
            tool_prefix=s.prefix,
            timeout=s.timeout,
            sse_read_timeout=s.sse_read_timeout,
            read_timeout=s.read_timeout,
        )
        for s in settings.agents_mcp.knowledge
    ]

    a2a_configs = [
        A2AConfig(
            base_url=s.url,
            api_key=s.api_key,
            bearer_token=s.bearer_token,
            timeout_seconds=s.timeout_seconds,
            tool_prefix=s.tool_prefix,
            name_override=s.name_override,
            description_override=s.description_override,
        )
        for s in settings.agents_a2a.knowledge
    ]

    builder = KnowledgeAgentBuilder.default_builder(
        llm_base_url=settings.litellm.proxy_api_base,
        llm_api_key=settings.litellm.proxy_api_key,
        checkpointer=app.state.db_checkpointer,
        mcp_configs=mcp_configs,
        a2a_configs=a2a_configs,
    )
    agent = await builder.build()

    agent_card = KnowledgeAgentCardBuilder(
        agent=agent,
        a2a_base_url=settings.a2a_base_url,
        a2a_protocol_version=settings.a2a.protocol_version,
    ).build()

    a2a_app = await create_a2a_application(
        agent=agent,
        agent_card=agent_card,
        task_store=task_store,
    )

    a2a_app.add_routes_to_app(
        app,
        agent_card_url=f"{settings.a2a.path}/{agent.slug}/{settings.a2a.agent_card_path}",
        rpc_url=f"{settings.a2a.path}/{agent.slug}/rpc",
    )

    tools = [ToolInfo(name=tool.name, description=tool.description or "") for tool in agent.tools]
    return KnowledgeAgentBuilder, agent, agent_card, agent.identity, tools
