"""LangGraph node factory for A2A client.

This module provides functions to create LangGraph nodes that
communicate with A2A agents as part of a graph workflow.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.client import A2AClientWrapper
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import A2AClientConfig, AuthConfig
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.base import ExecutionResult


@dataclass
class A2ANodeConfig:
    """Configuration for creating an A2A node.

    Attributes:
        base_url: Base URL of the A2A agent.
        input_key: State key to read input from.
        output_key: State key to write output to.
        task_id_key: Optional state key for task ID (for multi-turn).
        context_id_key: Optional state key for context ID.
        client_config: Optional client configuration.
        auth: Optional authentication configuration.
        transform_input: Optional function to transform state to input text.
        transform_output: Optional function to transform result to state update.
    """

    base_url: str
    input_key: str = "messages"
    output_key: str = "a2a_response"
    task_id_key: str | None = "a2a_task_id"
    context_id_key: str | None = "a2a_context_id"
    client_config: A2AClientConfig | None = None
    auth: AuthConfig | None = None
    transform_input: Callable[[dict[str, Any]], str] | None = None
    transform_output: Callable[[ExecutionResult, dict[str, Any]], dict[str, Any]] | None = None


def _default_input_transform(state: dict[str, Any]) -> str:
    """Default input transformation.

    Extracts the last user message from the state.

    Args:
        state: The graph state.

    Returns:
        Input text for the A2A agent.
    """
    messages = state.get("messages", [])
    if not messages:
        raise ValueError("No messages in state")

    last_message = messages[-1]

    if hasattr(last_message, "content"):
        return last_message.content
    if isinstance(last_message, dict):
        return last_message.get("content", str(last_message))
    return str(last_message)


def _default_output_transform(
    result: ExecutionResult,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Default output transformation.

    Creates a state update with the A2A response.

    Args:
        result: The execution result.
        state: The current graph state.

    Returns:
        State update dictionary.
    """
    return {
        "a2a_response": result.response_text,
        "a2a_task_id": result.task_id,
        "a2a_context_id": result.context_id,
    }


def create_a2a_node(
    config: A2ANodeConfig,
) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
    """Create a LangGraph node that calls an A2A agent.

    The node reads input from the configured state key, sends it
    to the A2A agent, and writes the response to the output key.

    Args:
        config: Node configuration.

    Returns:
        An async function suitable for use as a LangGraph node.
    """
    input_transform = config.transform_input or _default_input_transform
    output_transform = config.transform_output or _default_output_transform

    async def node(state: dict[str, Any]) -> dict[str, Any]:
        """Execute the A2A agent node.

        Args:
            state: The current graph state.

        Returns:
            State update dictionary.
        """
        input_text = input_transform(state)

        task_id = state.get(config.task_id_key) if config.task_id_key else None
        context_id = state.get(config.context_id_key) if config.context_id_key else None

        client = A2AClientWrapper(
            base_url=config.base_url,
            config=config.client_config,
            auth=config.auth,
        )

        async with client:
            result = await client.send_text(
                input_text,
                task_id=task_id,
                context_id=context_id,
            )

        return output_transform(result, state)

    return node


def create_multi_agent_router(
    agents: dict[str, A2ANodeConfig],
    router_fn: Callable[[dict[str, Any]], str],
) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
    """Create a node that routes to different A2A agents.

    Args:
        agents: Dictionary mapping agent names to their configs.
        router_fn: Function that takes state and returns agent name to use.

    Returns:
        An async function that routes to the appropriate agent.
    """

    async def router_node(state: dict[str, Any]) -> dict[str, Any]:
        """Route to the appropriate A2A agent.

        Args:
            state: The current graph state.

        Returns:
            State update dictionary.
        """
        agent_name = router_fn(state)

        if agent_name not in agents:
            raise ValueError(f"Unknown agent: {agent_name}")

        config = agents[agent_name]
        node = create_a2a_node(config)
        return await node(state)

    return router_node
