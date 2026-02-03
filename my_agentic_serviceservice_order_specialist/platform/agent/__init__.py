"""Agent infrastructure module.

This module provides the core abstractions and integrations for building agents:
- Agent protocol definition
- Configuration dataclasses
- LangGraph integration
- MCP client for tool discovery
- A2A protocol adapter
- Agent-specific metrics
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

__all__ = [
    "Agent",
    "AgentConfig",
    "AgentIdentity",
    "LlmConfig",
    "MCPConfig",
    "ExecutionResult",
    "Message",
    "StreamEvent",
    "LangGraphAgent",
    "LangGraphMCPTools",
    "MCPClient",
]
