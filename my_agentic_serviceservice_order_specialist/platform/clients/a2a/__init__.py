"""A2A Client module for communicating with A2A protocol agents.

This module provides a client-side implementation for the A2A (Agent-to-Agent) protocol,
enabling this service to communicate with external A2A agents as a client.

The module includes:
- Agent Card discovery and caching
- Synchronous, streaming, and polling execution strategies
- Multi-turn conversation management
- LangGraph integration (tools and nodes)
"""

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.client import A2AClientWrapper
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import A2AClientConfig
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.discovery import AgentCardCache, CachedAgentCardResolver
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import (
    A2AClientError,
    A2AConnectionError,
    A2AProtocolError,
    A2ATaskCanceledError,
    A2ATaskError,
    A2ATaskFailedError,
    A2ATaskNotFoundError,
    A2ATimeoutError,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.messages import MessageBuilder
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.session import ConversationSession

__all__ = [
    # Client
    "A2AClientWrapper",
    "A2AClientConfig",
    # Discovery
    "AgentCardCache",
    "CachedAgentCardResolver",
    # Messages
    "MessageBuilder",
    # Session
    "ConversationSession",
    # Exceptions
    "A2AClientError",
    "A2AConnectionError",
    "A2ATimeoutError",
    "A2AProtocolError",
    "A2ATaskError",
    "A2ATaskNotFoundError",
    "A2ATaskFailedError",
    "A2ATaskCanceledError",
]
