"""Agent dependencies for FastAPI routes."""

from collections.abc import Callable

from fastapi import Request

from my_agentic_serviceservice_order_specialist.platform.agent.protocol import Agent


def get_agent(builder_cls: type) -> Callable[[Request], Agent]:
    """Create a dependency that retrieves a cached agent by its builder class.

    Args:
        builder_cls: The agent builder class (e.g., KnowledgeAgentBuilder)

    Returns:
        A FastAPI dependency function that returns the cached agent

    Raises:
        KeyError: If the agent is not found in the registry

    Example:
        from my_agentic_serviceservice_order_specialist.agents.knowledge.agent import KnowledgeAgentBuilder

        @router.post("/invoke")
        async def invoke(
            payload: Payload,
            agent: Agent = Depends(get_agent(KnowledgeAgentBuilder)),
        ):
            return await agent.run(payload.question, thread_id=str(payload.thread_id))
    """

    def _get_agent(request: Request) -> Agent:
        agents = request.app.state.agents
        if builder_cls not in agents:
            raise KeyError(
                f"Agent for {builder_cls.__name__} not found. "
                f"Available: {[cls.__name__ for cls in agents.keys()]}"
            )
        return agents[builder_cls]

    return _get_agent
