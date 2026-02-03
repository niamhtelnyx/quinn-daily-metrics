"""HTTP clients for external services.

This module provides clients for communicating with external services,
including A2A (Agent-to-Agent) protocol agents.
"""

from my_agentic_serviceservice_order_specialist.platform.clients.a2a import (
    A2AClientConfig,
    A2AClientError,
    A2AClientWrapper,
    A2AConnectionError,
    A2AProtocolError,
    A2ATaskCanceledError,
    A2ATaskError,
    A2ATaskFailedError,
    A2ATaskNotFoundError,
    A2ATimeoutError,
    AgentCardCache,
    CachedAgentCardResolver,
    ConversationSession,
    MessageBuilder,
)

__all__ = [
    # A2A Client
    "A2AClientWrapper",
    "A2AClientConfig",
    # A2A Discovery
    "AgentCardCache",
    "CachedAgentCardResolver",
    # A2A Messages
    "MessageBuilder",
    # A2A Session
    "ConversationSession",
    # A2A Exceptions
    "A2AClientError",
    "A2AConnectionError",
    "A2ATimeoutError",
    "A2AProtocolError",
    "A2ATaskError",
    "A2ATaskNotFoundError",
    "A2ATaskFailedError",
    "A2ATaskCanceledError",
]
