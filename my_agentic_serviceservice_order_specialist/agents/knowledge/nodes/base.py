"""Base protocol for agent nodes."""

from typing import Protocol, runtime_checkable

from my_agentic_serviceservice_order_specialist.agents.knowledge.state import AgentState


@runtime_checkable
class Node(Protocol):
    """Protocol for agent graph nodes.

    Nodes are callable objects that transform AgentState.
    They are used as nodes in the LangGraph StateGraph.
    """

    async def __call__(self, state: AgentState) -> AgentState:
        """Process state and return updated state.

        Args:
            state: Current agent state

        Returns:
            Updated agent state with modifications
        """
        ...
