"""AI Platform infrastructure module.

This module provides the core infrastructure for building agentic services:
- Agent protocol and base classes
- LangGraph integration
- MCP (Model Context Protocol) client
- A2A (Agent-to-Agent) protocol adapter
- FastAPI server configuration
- Database and observability utilities

Squads should NOT modify this module. Updates come via `make update-template`.
"""

from my_agentic_serviceservice_order_specialist.platform.agent.config import (
    AgentConfig,
    AgentIdentity,
    LlmConfig,
    MCPConfig,
)
from my_agentic_serviceservice_order_specialist.platform.agent.langgraph import (
    LangGraphAgent,
    LangGraphMCPTools,
)
from my_agentic_serviceservice_order_specialist.platform.agent.mcp import MCPClient
from my_agentic_serviceservice_order_specialist.platform.agent.messages import (
    ExecutionResult,
    Message,
    StreamEvent,
)
from my_agentic_serviceservice_order_specialist.platform.agent.protocol import Agent
from my_agentic_serviceservice_order_specialist.platform.settings import Settings

__all__ = [
    # Core protocols
    "Agent",
    # Configuration
    "AgentConfig",
    "AgentIdentity",
    "LlmConfig",
    "MCPConfig",
    "Settings",
    # LangGraph integration
    "LangGraphAgent",
    "LangGraphMCPTools",
    # MCP
    "MCPClient",
    # Message types
    "ExecutionResult",
    "Message",
    "StreamEvent",
]
