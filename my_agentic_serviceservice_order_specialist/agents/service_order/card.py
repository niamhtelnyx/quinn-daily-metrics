"""Agent card for Service Order Operations agent.

This module builds the agent card (A2A discovery document) that describes
the Service Order agent's capabilities, skills, and integration points.
"""

from a2a.types import AgentCard, AgentCapabilities, AgentSkill

from my_agentic_serviceservice_order_specialist.agents.service_order.agent import A2A_SKILLS
from my_agentic_serviceservice_order_specialist.platform.agent.protocol import Agent


class ServiceOrderAgentCardBuilder:
    """Builder for Service Order Operations agent card.
    
    Creates the A2A agent card that describes the Service Order agent's
    capabilities for discovery by other agents and systems.
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
        """Build the complete agent card for Service Order operations.
        
        Returns:
            A2A agent card with Service Order capabilities and skills
        """
        # Convert A2A_SKILLS to AgentSkill objects
        skills = []
        for skill_dict in A2A_SKILLS:
            skills.append(AgentSkill(
                id=skill_dict["id"],
                name=skill_dict["name"],
                description=skill_dict["description"],
                tags=["service-order", "billing", "salesforce", "commitment-manager"],
                examples=self._get_skill_examples(skill_dict["id"]),
            ))

        capabilities = AgentCapabilities(
            streaming=True,
            push_notifications=True,
            state_transition_history=True,
            file_upload=True,
        )

        return AgentCard(
            name=self.agent.identity.name,
            description=self.agent.identity.description,
            url=f"{self.a2a_base_url}/{self.agent.identity.slug}/rpc",
            version=self.a2a_protocol_version,
            capabilities=capabilities,
            skills=skills,
            default_input_modes=["text", "file"],
            default_output_modes=["text", "structured"],
        )

    def _get_skill_examples(self, skill_id: str) -> list[str]:
        """Get example interactions for each skill.
        
        Args:
            skill_id: The skill identifier
            
        Returns:
            List of example prompts for the skill
        """
        examples = {
            "process-service-order": [
                "Please process this Service Order PDF for Customer ABC",
                "I have a new Service Order document that needs to be processed"
            ],
            "analyze-billing-discrepancy": [
                "Why did Customer XYZ get charged an extra $10K last month?",
                "Explain the billing discrepancy for Customer ABC"
            ],
            "validate-salesforce-entry": [
                "Verify Service Order SO-12345 in Salesforce matches the source document",
                "Check if this Service Order is correctly logged in Salesforce"
            ],
            "explain-commitment-changes": [
                "Why did Customer XYZ's commitment increase from $25K to $35K?",
                "Explain the commitment changes for Customer ABC over the past quarter"
            ]
        }
        return examples.get(skill_id, [f"Use {skill_id} for Service Order operations"])