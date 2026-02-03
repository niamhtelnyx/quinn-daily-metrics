"""Configuration for the A2A client.

This module provides configuration dataclasses for the A2A client,
including settings for execution strategies, timeouts, and retry behavior.
"""

from dataclasses import dataclass
from enum import StrEnum


class ExecutionStrategy(StrEnum):
    """Execution strategy for A2A communication."""

    AUTO = "auto"
    SYNC = "sync"
    STREAMING = "streaming"
    POLLING = "polling"


@dataclass(frozen=True)
class A2AClientConfig:
    """Configuration for an A2A client instance.

    Attributes:
        timeout_seconds: Default timeout for HTTP requests (default: 60s).
        streaming_enabled: Whether to attempt streaming when available (default: True).
        polling_enabled: Whether to use polling for long-running tasks (default: True).
        preferred_strategy: Preferred execution strategy (default: POLLING).
        poll_interval_seconds: Interval between polling requests (default: 1.0s).
        max_poll_time_seconds: Maximum time to poll before giving up (default: 600s).
        poll_backoff_multiplier: Multiplier for exponential backoff (default: 1.5).
        poll_max_interval_seconds: Maximum polling interval after backoff (default: 30s).
        max_retries: Maximum number of retries for transient errors (default: 3).
        retry_delay_seconds: Initial delay between retries (default: 1.0s).
        agent_card_cache_ttl_seconds: TTL for cached agent cards (default: 3600s).
        max_conversation_turns: Maximum turns in a multi-turn conversation (default: 10).
    """

    timeout_seconds: float = 60.0
    streaming_enabled: bool = True
    polling_enabled: bool = True
    preferred_strategy: ExecutionStrategy = ExecutionStrategy.POLLING
    poll_interval_seconds: float = 1.0
    max_poll_time_seconds: float = 600.0
    poll_backoff_multiplier: float = 1.5
    poll_max_interval_seconds: float = 30.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    agent_card_cache_ttl_seconds: float = 3600.0
    max_conversation_turns: int = 10


@dataclass(frozen=True)
class AuthConfig:
    """Authentication configuration for A2A client.

    Supports API key and JWT/Bearer token authentication.

    Attributes:
        api_key: API key for apiKey authentication.
        api_key_header: Header name for API key (default: X-API-Key).
        bearer_token: Bearer token for JWT authentication.
        token_refresh_callback: Optional callback to refresh expired tokens.
    """

    api_key: str | None = None
    api_key_header: str = "X-API-Key"
    bearer_token: str | None = None
