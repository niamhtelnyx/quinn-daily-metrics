"""A2A Agent Card builder for Knowledge agents.

This module provides a builder for creating A2A protocol AgentCard metadata
that describes agent capabilities for service discovery.
"""

from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from my_agentic_serviceservice_order_specialist.platform.agent.protocol import Agent


class KnowledgeAgentCardBuilder:
    """Builder for A2A protocol AgentCard metadata.

    Creates an AgentCard that describes the agent's capabilities, skills,
    and endpoints for A2A service discovery.

    Example:
        card = KnowledgeAgentCardBuilder(agent, "http://localhost:8000", "0.3.0").build()
    """

    def __init__(self, agent: Agent, a2a_base_url: str, a2a_protocol_version: str) -> None:
        """Initialize the card builder.

        Args:
            agent: The agent to create a card for (provides name, description, slug)
            a2a_base_url: Base URL where the A2A endpoints are hosted
            a2a_protocol_version: A2A protocol version to advertise
        """
        self.agent = agent
        self.a2a_base_url = a2a_base_url
        self.a2a_protocol_version = a2a_protocol_version

    def build(self) -> AgentCard:
        """Build the AgentCard with skills and capabilities.

        Returns:
            AgentCard with Knowledge-specific skills and streaming capabilities.
        """
        skills = [
            AgentSkill(
                id="general-query",
                name="General Query",
                description="Answer questions and perform operations",
                tags=["query", "knowledge"],
                examples=["How can I help you today?"],
            ),
        ]

        capabilities = AgentCapabilities(
            streaming=True,
            push_notifications=True,
            state_transition_history=True,
        )

        return AgentCard(
            name=self.agent.name,
            description=self.agent.description,
            url=f"{self.a2a_base_url}/{self.agent.slug}/rpc",
            version=self.a2a_protocol_version,
            capabilities=capabilities,
            skills=skills,
            default_input_modes=["text"],
            default_output_modes=["text"],
        )
