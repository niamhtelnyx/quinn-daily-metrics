"""LangGraph state definition for the knowledge agent."""

from my_agentic_serviceservice_order_specialist.platform.agent.state import BaseAgentState


class AgentState(BaseAgentState):
    """LangGraph state for the knowledge agent.

    Inherits from BaseAgentState and adds:
        reasoning_steps: Counter for reasoning iterations
    """

    reasoning_steps: int
