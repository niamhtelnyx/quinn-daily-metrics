"""Agent registration models for discovery service.

This module provides the envelope model for registering agents with
an external discovery service, including metadata alongside the A2A AgentCard.
"""

from datetime import UTC, datetime

from a2a.types import AgentCard
from pydantic import BaseModel, Field

REGISTRATION_SCHEMA_VERSION = "1.0"


class ToolInfo(BaseModel):
    """Tool information for registration.

    Attributes:
        name: Tool name
        description: Tool description
    """

    name: str
    description: str


class RegistrationMetadata(BaseModel):
    """Metadata for agent registration.

    Attributes:
        schema_version: Version of the registration schema
        agent_id: Unique identifier in format {squad}:{origin}:{slug}
        audience: Target audience (customer, internal, public)
        squad: Group identifier for the agent
        origin: Name of the service hosting the agent
        timestamp: Timestamp when registration was initiated
    """

    schema_version: str = Field(default=REGISTRATION_SCHEMA_VERSION)
    agent_id: str
    audience: str
    squad: str
    origin: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentRegistration(BaseModel):
    """Envelope for agent registration with discovery service.

    Attributes:
        metadata: Registration metadata
        agent_card: The A2A protocol AgentCard
        tools: List of tools available to the agent
    """

    metadata: RegistrationMetadata
    agent_card: AgentCard
    tools: list[ToolInfo] = Field(default_factory=list)
