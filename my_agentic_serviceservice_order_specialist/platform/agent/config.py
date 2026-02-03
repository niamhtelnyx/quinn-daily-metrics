"""Configuration dataclasses for agent components.

This module provides immutable configuration objects for LLM clients,
MCP servers, and agent behavior settings.
"""

from dataclasses import dataclass
from enum import StrEnum


class Audience(StrEnum):
    """Target audience for the agent."""

    CUSTOMER = "customer"
    INTERNAL = "internal"
    PUBLIC = "public"


@dataclass(frozen=True)
class LlmConfig:
    """Configuration for language model clients.

    This is a framework-agnostic configuration that both LangGraph and DSPy
    implementations can use to create their specific LLM clients.

    Attributes:
        model: Model identifier (e.g., "litellm_proxy/anthropic/claude-sonnet-4-5")
        api_key: API key for the LLM provider
        base_url: Base URL for the API (e.g., LiteLLM proxy URL)
        temperature: Sampling temperature (0.0 to 1.0)
    """

    model: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7


@dataclass(frozen=True)
class MCPConfig:
    """Configuration for MCP (Model Context Protocol) clients.

    Attributes:
        server_url: URL of the MCP server endpoint
        tool_prefix: Optional prefix for tool names to avoid collisions with multiple MCP servers.
                     All MCP tools get 'mcp_' prefix; this adds: mcp_<tool_prefix>_<name>
        headers: Optional HTTP headers to include in requests
        timeout: Connection timeout in seconds (default: 60.0)
        sse_read_timeout: SSE stream read timeout in seconds (default: 300.0)
        read_timeout: General read timeout in seconds (default: 120.0)
    """

    server_url: str
    tool_prefix: str | None = None
    headers: dict[str, str] | None = None
    timeout: float = 60.0
    sse_read_timeout: float = 300.0
    read_timeout: float = 120.0


@dataclass(frozen=True)
class A2AConfig:
    """Configuration for A2A (Agent-to-Agent) remote agent clients.

    Attributes:
        base_url: Base URL of the remote A2A agent
        api_key: Optional API key for authentication
        bearer_token: Optional bearer token for authentication
        timeout_seconds: Request timeout in seconds (default: 60.0)
        tool_prefix: Optional prefix for tool names. If None, derives from agent card name.
            Final format: a2a_<tool_prefix>_<skill_name>
        name_override: Optional override for the generated tool name (bypasses prefix)
        description_override: Optional override for the generated tool description
    """

    base_url: str
    api_key: str | None = None
    bearer_token: str | None = None
    timeout_seconds: float = 60.0
    tool_prefix: str | None = None
    name_override: str | None = None
    description_override: str | None = None


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for agent behavior.

    Attributes:
        max_reasoning_steps: Maximum reasoning iterations before forcing completion
        artifact_threshold: Hide tool outputs larger than this (None disables)
        always_visible_tools: Tool names (frozenset) that are never hidden by artifact pattern (exact match)
        always_visible_tool_suffixes: Tool name suffixes (frozenset) that are never hidden
            (e.g., "_fetch_relevant_tools" matches "mcp_myprefix_fetch_relevant_tools")
        recursion_limit: LangGraph recursion limit
        max_context_tokens: Maximum tokens before trimming old messages (None disables)
    """

    max_reasoning_steps: int
    always_visible_tools: frozenset[str]
    recursion_limit: int
    artifact_threshold: int = 5000
    always_visible_tool_suffixes: frozenset[str] = frozenset()
    max_context_tokens: int = 150000


@dataclass(frozen=True)
class AgentIdentity:
    """Identity information for an agent.

    Attributes:
        name: Human-readable display name for the agent
        description: Brief description of the agent's capabilities
        slug: URL-safe identifier used in API routes
        squad: Group identifier for the agent
        origin: Name of the service hosting the agent
        audience: Target audience for the agent
    """

    name: str
    description: str
    slug: str
    squad: str
    origin: str
    audience: Audience = Audience.INTERNAL

    @property
    def unique_id(self) -> str:
        """Generate a unique identifier from squad, origin, and slug."""
        return f"{self.squad}:{self.origin}:{self.slug}"
