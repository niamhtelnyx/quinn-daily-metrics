"""A2A Protocol HTTP routes using a2a-sdk.

This module sets up the A2A protocol endpoints using the official a2a-sdk,
providing JSON-RPC handling, streaming, and agent card discovery.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import cast

import httpx
from a2a.server.tasks import DatabaseTaskStore, TaskStore
from a2a.types import AgentCard
from fastapi import FastAPI

from my_agentic_serviceservice_order_specialist.agents.service_order.a2a_setup import (
    build_and_mount_service_order_agent,
)
from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentIdentity
from my_agentic_serviceservice_order_specialist.platform.agent.protocol import Agent
from my_agentic_serviceservice_order_specialist.platform.agent.registration import (
    AgentRegistration,
    RegistrationMetadata,
    ToolInfo,
)
from my_agentic_serviceservice_order_specialist.platform.database.engine import DbEngine

# Type alias for agent mount functions
# Returns: (builder_class, agent, agent_card, identity, tools)
type AgentMountResult = tuple[type, Agent, AgentCard, AgentIdentity, list[ToolInfo]]
type AgentMountFn = Callable[[FastAPI, TaskStore], Awaitable[AgentMountResult]]

logger = logging.getLogger(__name__)


async def register_agent_card(
    http_client: httpx.AsyncClient,
    registry_url: str,
    agent_card: AgentCard,
    identity: AgentIdentity,
    tools: list[ToolInfo] | None = None,
) -> None:
    """Register an agent card with an external registry.

    Args:
        http_client: HTTP client for making the request
        registry_url: URL of the agent registry
        agent_card: The agent card to register
        identity: Agent identity containing metadata for registration
        tools: Optional list of tools available to the agent
    """
    metadata = RegistrationMetadata(
        agent_id=identity.unique_id,
        audience=identity.audience.value,
        squad=identity.squad,
        origin=identity.origin,
    )
    registration = AgentRegistration(
        metadata=metadata,
        agent_card=agent_card,
        tools=tools or [],
    )
    try:
        response = await http_client.post(
            registry_url,
            json=registration.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()
        logger.info(f"Agent '{metadata.agent_id}' registered at {registry_url}")
    except Exception as e:
        logger.error(f"Failed to register agent '{metadata.agent_id}': {e}")


async def add_a2a_routes_to_app(
    app: FastAPI,
) -> list[tuple[AgentCard, AgentIdentity, list[ToolInfo]]]:
    """Add A2A routes to the FastAPI application and cache agents.

    This should be called after the database is initialized (in lifespan).
    Builds agents using configuration from app.state.settings.
    Agents are cached in app.state.agents using their builder class as key.

    Args:
        app: The FastAPI application instance with initialized db_engine and settings

    Returns:
        List of (AgentCard, AgentIdentity, tools) tuples for use in service registration
    """

    try:
        # Get database from app.state
        db: DbEngine = app.state.db_engine
        engine = db.get_engine()

        # Create shared task store
        # This prevents "Table already defined" error when creating multiple apps
        task_store = cast(
            TaskStore,
            DatabaseTaskStore(
                engine=engine,
                create_table=True,
                table_name="a2a_tasks",
            ),
        )

        # Initialize agent registry (builder class -> agent instance)
        app.state.agents = {}  # type: dict[type, Agent]

        # List of agent mount functions - add new agents here
        agent_mount_functions: list[AgentMountFn] = [
            build_and_mount_service_order_agent,
            # build_and_mount_support_agent, 
            # build_and_mount_sales_agent,
        ]

        # Mount all agents and cache them
        agent_registrations: list[tuple[AgentCard, AgentIdentity, list[ToolInfo]]] = []

        for mount_fn in agent_mount_functions:
            builder_cls, agent, agent_card, identity, tools = await mount_fn(app, task_store)
            app.state.agents[builder_cls] = agent
            agent_registrations.append((agent_card, identity, tools))
            logger.info(f"Agent '{identity.slug}' mounted and cached")

        logger.info(f"A2A routes: {len(app.state.agents)} agent(s) ready")
        return agent_registrations
    except Exception as e:
        logger.exception(f"Failed to mount A2A routes: {e}")
        raise
