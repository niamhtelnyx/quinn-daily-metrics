"""Agent Card discovery and caching.

This module provides components for fetching, parsing, and caching
A2A Agent Cards from remote agents.
"""

import time
from dataclasses import dataclass, field

import httpx
from a2a.client.card_resolver import A2ACardResolver
from a2a.client.errors import A2AClientHTTPError, A2AClientJSONError
from a2a.types import AgentCard

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import A2AClientConfig
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import A2AConnectionError, A2AProtocolError


@dataclass
class CachedCard:
    """A cached Agent Card with expiration tracking.

    Attributes:
        card: The cached AgentCard.
        fetched_at: Unix timestamp when the card was fetched.
        ttl_seconds: Time-to-live in seconds.
    """

    card: AgentCard
    fetched_at: float
    ttl_seconds: float

    def is_expired(self) -> bool:
        """Check if this cached card has expired."""
        return time.time() > (self.fetched_at + self.ttl_seconds)


@dataclass
class AgentCardCache:
    """In-memory cache for Agent Cards.

    Provides TTL-based caching to avoid repeated fetches of Agent Cards.
    Safe for use in async contexts since Python's GIL ensures atomic dict
    operations. For multi-threaded environments with concurrent writes,
    external synchronization is recommended.

    Attributes:
        default_ttl_seconds: Default TTL for cached cards.
    """

    default_ttl_seconds: float = 300.0
    _cache: dict[str, CachedCard] = field(default_factory=dict)

    def get(self, url: str) -> AgentCard | None:
        """Get a cached Agent Card if it exists and is not expired.

        Args:
            url: The base URL of the agent.

        Returns:
            The cached AgentCard if valid, None otherwise.
        """
        cached = self._cache.get(url)
        if cached is None:
            return None
        if cached.is_expired():
            del self._cache[url]
            return None
        return cached.card

    def set(self, url: str, card: AgentCard, ttl_seconds: float | None = None) -> None:
        """Cache an Agent Card.

        Args:
            url: The base URL of the agent.
            card: The AgentCard to cache.
            ttl_seconds: Optional custom TTL (uses default if not specified).
        """
        self._cache[url] = CachedCard(
            card=card,
            fetched_at=time.time(),
            ttl_seconds=ttl_seconds or self.default_ttl_seconds,
        )

    def invalidate(self, url: str) -> None:
        """Remove a cached Agent Card.

        Args:
            url: The base URL of the agent to invalidate.
        """
        self._cache.pop(url, None)

    def clear(self) -> None:
        """Clear all cached Agent Cards."""
        self._cache.clear()


class CachedAgentCardResolver:
    """Agent Card resolver with caching support.

    Wraps the SDK's A2ACardResolver with caching functionality to
    reduce network calls for frequently accessed agents.
    """

    def __init__(
        self,
        httpx_client: httpx.AsyncClient,
        cache: AgentCardCache | None = None,
        config: A2AClientConfig | None = None,
    ):
        """Initialize the resolver.

        Args:
            httpx_client: HTTP client for making requests.
            cache: Optional pre-configured cache (creates new if not provided).
            config: Optional client configuration for TTL settings.
        """
        self._httpx_client = httpx_client
        self._config = config or A2AClientConfig()
        self._cache = cache or AgentCardCache(
            default_ttl_seconds=self._config.agent_card_cache_ttl_seconds
        )

    async def get_agent_card(
        self,
        base_url: str,
        *,
        force_refresh: bool = False,
        agent_card_path: str | None = None,
    ) -> AgentCard:
        """Fetch an Agent Card, using cache if available.

        Args:
            base_url: The base URL of the agent.
            force_refresh: If True, bypass cache and fetch fresh.
            agent_card_path: Optional custom path to the agent card.

        Returns:
            The AgentCard for the specified agent.

        Raises:
            A2AConnectionError: If the agent cannot be reached.
            A2AProtocolError: If the agent card is invalid.
        """
        if not force_refresh:
            cached = self._cache.get(base_url)
            if cached is not None:
                return cached

        try:
            resolver = A2ACardResolver(
                httpx_client=self._httpx_client,
                base_url=base_url,
            )
            card = await resolver.get_agent_card(
                relative_card_path=agent_card_path,
            )
            self._cache.set(base_url, card)
            return card

        except A2AClientHTTPError as e:
            raise A2AConnectionError(
                message=e.message,
                url=base_url,
            ) from e
        except A2AClientJSONError as e:
            raise A2AProtocolError(
                message=f"Invalid agent card: {e.message}",
            ) from e

    def invalidate(self, base_url: str) -> None:
        """Invalidate a cached Agent Card.

        Args:
            base_url: The base URL of the agent to invalidate.
        """
        self._cache.invalidate(base_url)

    def clear_cache(self) -> None:
        """Clear all cached Agent Cards."""
        self._cache.clear()
