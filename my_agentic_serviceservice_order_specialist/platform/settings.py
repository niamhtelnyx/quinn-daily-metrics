"""Application settings and configuration.

This module provides Pydantic settings classes for application configuration,
loaded from environment variables with support for nested configuration.
"""

import logging

import pydantic_settings
from pydantic import BaseModel, Field, field_validator


class DBConnectionSettings(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str
    echo: bool = False


class AppHTTPSettings(BaseModel):
    url: str = Field("")
    host: str = Field("0.0.0.0")
    port: int = Field(8000)
    log_level: str = Field("INFO")
    log_json: bool | None = Field(
        None, description="Override log format: True=JSON, False=console, None=auto"
    )

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v):
        v_upper = v.upper()
        if v_upper not in logging._nameToLevel:
            raise ValueError(f'invalid value "{v}"')
        return v_upper


class OpenTelemetrySettings(BaseModel):
    host: str = Field("")
    port: int = Field(4317)
    enabled: bool = Field(True)
    excluded_urls: str = Field("metrics,health,info")


class BugsnagSettings(BaseModel):
    api_key: str
    release_stage: str = Field("development")

    @field_validator("release_stage")
    @classmethod
    def _validate_bugsnag_release_stage(cls, v):
        if v not in ["development", "production", "local"]:
            raise ValueError(f'invalid bugsnag release stage "{v}"')
        return v


class LitellmSettings(BaseModel):
    proxy_api_base: str
    proxy_api_key: str


class MCPServerSettings(BaseModel):
    """Configuration for a single MCP server.

    Attributes:
        url: URL of the MCP server endpoint
        prefix: Optional prefix for tool names to avoid collisions
        timeout: Connection timeout in seconds
        sse_read_timeout: SSE stream read timeout in seconds
        read_timeout: General read timeout in seconds
    """

    url: str
    prefix: str | None = None
    timeout: float = 60.0
    sse_read_timeout: float = 300.0
    read_timeout: float = 120.0


class AgentsMCPSettings(BaseModel):
    """MCP server configurations keyed by agent slug.

    Each agent can have multiple MCP servers configured via JSON env vars.
    Example: AGENTS_MCP__KNOWLEDGE='[{"url":"http://...","prefix":"knowledge"}]'
    """

    knowledge: list[MCPServerSettings] = []


class A2ARemoteAgentSettings(BaseModel):
    """Configuration for a remote A2A agent.

    Attributes:
        url: Base URL of the remote A2A agent
        api_key: Optional API key for authentication
        bearer_token: Optional bearer token for authentication
        timeout_seconds: Request timeout in seconds
        tool_prefix: Optional prefix for tool names. If None, derives from agent card name.
        name_override: Optional override for the tool name (bypasses prefix)
        description_override: Optional override for the tool description
    """

    url: str
    api_key: str | None = None
    bearer_token: str | None = None
    timeout_seconds: float = 60.0
    tool_prefix: str | None = None
    name_override: str | None = None
    description_override: str | None = None


class AgentsA2ASettings(BaseModel):
    """A2A remote agent configurations keyed by agent slug.

    Each agent can have multiple remote A2A agents configured via JSON env vars.
    Example: AGENTS_A2A__KNOWLEDGE='[{"url":"http://remote-agent:8000/a2a"}]'
    """

    knowledge: list[A2ARemoteAgentSettings] = []


class A2ASettings(BaseModel):
    protocol_version: str = Field("0.3.0")
    path: str = Field("/a2a")
    agent_card_path: str = Field(".well-known/agent-card.json")


class AgentRegistrySettings(BaseModel):
    url: str = Field("")
    enabled: bool = Field(True)

    @property
    def should_register(self) -> bool:
        return bool(self.url and self.enabled)


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(env_nested_delimiter="__")

    app_http: AppHTTPSettings
    opentelemetry: OpenTelemetrySettings
    bugsnag: BugsnagSettings

    # Database configuration
    primary_db: DBConnectionSettings
    replica_db: DBConnectionSettings

    # LiteLLM configuration
    litellm: LitellmSettings

    # A2A configuration
    a2a: A2ASettings

    # Agent registry configuration
    agent_registry: AgentRegistrySettings = AgentRegistrySettings()

    # MCP server configurations per agent
    agents_mcp: AgentsMCPSettings = AgentsMCPSettings()

    # A2A remote agent configurations per agent
    agents_a2a: AgentsA2ASettings = AgentsA2ASettings()

    @property
    def a2a_base_url(self) -> str:
        """Construct the A2A base URL from HTTP settings and A2A path."""
        return f"{self.app_http.url}:{self.app_http.port}{self.a2a.path}"
