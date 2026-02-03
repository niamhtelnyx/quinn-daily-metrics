"""Unit tests for A2A client discovery module."""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from a2a.client.errors import A2AClientHTTPError, A2AClientJSONError
from a2a.types import AgentCapabilities, AgentCard

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.discovery import (
    AgentCardCache,
    CachedAgentCardResolver,
    CachedCard,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import A2AConnectionError, A2AProtocolError


class TestCachedCard:
    """Tests for CachedCard dataclass."""

    def test_is_expired_false_when_fresh(self):
        """is_expired returns False for fresh cards."""
        card = Mock(spec=AgentCard)
        cached = CachedCard(
            card=card,
            fetched_at=time.time(),
            ttl_seconds=300.0,
        )
        assert cached.is_expired() is False

    def test_is_expired_true_when_old(self):
        """is_expired returns True for old cards."""
        card = Mock(spec=AgentCard)
        cached = CachedCard(
            card=card,
            fetched_at=time.time() - 400,
            ttl_seconds=300.0,
        )
        assert cached.is_expired() is True

    def test_is_expired_boundary(self):
        """is_expired handles boundary condition."""
        card = Mock(spec=AgentCard)
        now = time.time()
        cached = CachedCard(
            card=card,
            fetched_at=now - 299,
            ttl_seconds=300.0,
        )
        assert cached.is_expired() is False


class TestAgentCardCache:
    """Tests for AgentCardCache."""

    def test_get_returns_none_for_missing(self):
        """get returns None for uncached URLs."""
        cache = AgentCardCache()
        assert cache.get("http://unknown.example.com") is None

    def test_set_and_get(self):
        """set stores and get retrieves cards."""
        cache = AgentCardCache()
        card = Mock(spec=AgentCard)
        cache.set("http://agent.example.com", card)
        retrieved = cache.get("http://agent.example.com")
        assert retrieved is card

    def test_get_returns_none_for_expired(self):
        """get returns None for expired cards."""
        cache = AgentCardCache(default_ttl_seconds=1.0)
        card = Mock(spec=AgentCard)
        cache.set("http://agent.example.com", card)

        # Manually expire the card
        cached = cache._cache["http://agent.example.com"]
        cache._cache["http://agent.example.com"] = CachedCard(
            card=cached.card,
            fetched_at=time.time() - 100,
            ttl_seconds=1.0,
        )

        assert cache.get("http://agent.example.com") is None

    def test_set_with_custom_ttl(self):
        """set accepts custom TTL."""
        cache = AgentCardCache(default_ttl_seconds=300.0)
        card = Mock(spec=AgentCard)
        cache.set("http://agent.example.com", card, ttl_seconds=60.0)
        cached = cache._cache["http://agent.example.com"]
        assert cached.ttl_seconds == 60.0

    def test_invalidate_removes_card(self):
        """invalidate removes a specific card."""
        cache = AgentCardCache()
        card = Mock(spec=AgentCard)
        cache.set("http://agent.example.com", card)
        cache.invalidate("http://agent.example.com")
        assert cache.get("http://agent.example.com") is None

    def test_invalidate_nonexistent_is_noop(self):
        """invalidate handles nonexistent URLs gracefully."""
        cache = AgentCardCache()
        cache.invalidate("http://unknown.example.com")  # Should not raise

    def test_clear_removes_all(self):
        """clear removes all cached cards."""
        cache = AgentCardCache()
        card1 = Mock(spec=AgentCard)
        card2 = Mock(spec=AgentCard)
        cache.set("http://agent1.example.com", card1)
        cache.set("http://agent2.example.com", card2)
        cache.clear()
        assert cache.get("http://agent1.example.com") is None
        assert cache.get("http://agent2.example.com") is None


class TestCachedAgentCardResolver:
    """Tests for CachedAgentCardResolver."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Create a mock httpx client."""
        return Mock()

    @pytest.fixture
    def sample_agent_card(self):
        """Create a sample AgentCard."""
        return AgentCard(
            name="Test Agent",
            description="A test agent",
            url="http://agent.example.com/a2a",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=True),
            skills=[],
            default_input_modes=["text"],
            default_output_modes=["text"],
        )

    async def test_get_agent_card_from_cache(self, mock_httpx_client, sample_agent_card):
        """get_agent_card returns cached card when available."""
        cache = AgentCardCache()
        cache.set("http://agent.example.com", sample_agent_card)

        resolver = CachedAgentCardResolver(
            httpx_client=mock_httpx_client,
            cache=cache,
        )

        card = await resolver.get_agent_card("http://agent.example.com")
        assert card is sample_agent_card

    async def test_get_agent_card_fetches_when_not_cached(
        self, mock_httpx_client, sample_agent_card
    ):
        """get_agent_card fetches from server when not cached."""
        cache = AgentCardCache()
        resolver = CachedAgentCardResolver(
            httpx_client=mock_httpx_client,
            cache=cache,
        )

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.discovery.A2ACardResolver"
        ) as mock_resolver_cls:
            mock_resolver = AsyncMock()
            mock_resolver.get_agent_card = AsyncMock(return_value=sample_agent_card)
            mock_resolver_cls.return_value = mock_resolver

            card = await resolver.get_agent_card("http://agent.example.com")

            assert card is sample_agent_card
            mock_resolver.get_agent_card.assert_called_once()

    async def test_get_agent_card_force_refresh(self, mock_httpx_client, sample_agent_card):
        """get_agent_card bypasses cache when force_refresh=True."""
        cache = AgentCardCache()
        old_card = Mock(spec=AgentCard)
        cache.set("http://agent.example.com", old_card)

        resolver = CachedAgentCardResolver(
            httpx_client=mock_httpx_client,
            cache=cache,
        )

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.discovery.A2ACardResolver"
        ) as mock_resolver_cls:
            mock_resolver = AsyncMock()
            mock_resolver.get_agent_card = AsyncMock(return_value=sample_agent_card)
            mock_resolver_cls.return_value = mock_resolver

            card = await resolver.get_agent_card(
                "http://agent.example.com",
                force_refresh=True,
            )

            assert card is sample_agent_card
            mock_resolver.get_agent_card.assert_called_once()

    async def test_get_agent_card_caches_result(self, mock_httpx_client, sample_agent_card):
        """get_agent_card caches the fetched card."""
        cache = AgentCardCache()
        resolver = CachedAgentCardResolver(
            httpx_client=mock_httpx_client,
            cache=cache,
        )

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.discovery.A2ACardResolver"
        ) as mock_resolver_cls:
            mock_resolver = AsyncMock()
            mock_resolver.get_agent_card = AsyncMock(return_value=sample_agent_card)
            mock_resolver_cls.return_value = mock_resolver

            await resolver.get_agent_card("http://agent.example.com")

            # Second call should use cache
            card = await resolver.get_agent_card("http://agent.example.com")
            assert card is sample_agent_card
            assert mock_resolver.get_agent_card.call_count == 1

    async def test_get_agent_card_http_error(self, mock_httpx_client):
        """get_agent_card raises A2AConnectionError on HTTP error."""
        resolver = CachedAgentCardResolver(httpx_client=mock_httpx_client)

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.discovery.A2ACardResolver"
        ) as mock_resolver_cls:
            mock_resolver = AsyncMock()
            mock_resolver.get_agent_card = AsyncMock(
                side_effect=A2AClientHTTPError(404, "Not found")
            )
            mock_resolver_cls.return_value = mock_resolver

            with pytest.raises(A2AConnectionError) as exc_info:
                await resolver.get_agent_card("http://agent.example.com")

            assert exc_info.value.url == "http://agent.example.com"

    async def test_get_agent_card_json_error(self, mock_httpx_client):
        """get_agent_card raises A2AProtocolError on JSON error."""
        resolver = CachedAgentCardResolver(httpx_client=mock_httpx_client)

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.discovery.A2ACardResolver"
        ) as mock_resolver_cls:
            mock_resolver = AsyncMock()
            mock_resolver.get_agent_card = AsyncMock(side_effect=A2AClientJSONError("Invalid JSON"))
            mock_resolver_cls.return_value = mock_resolver

            with pytest.raises(A2AProtocolError):
                await resolver.get_agent_card("http://agent.example.com")

    def test_invalidate(self, mock_httpx_client, sample_agent_card):
        """invalidate removes card from cache."""
        cache = AgentCardCache()
        cache.set("http://agent.example.com", sample_agent_card)
        resolver = CachedAgentCardResolver(
            httpx_client=mock_httpx_client,
            cache=cache,
        )
        resolver.invalidate("http://agent.example.com")
        assert cache.get("http://agent.example.com") is None

    def test_clear_cache(self, mock_httpx_client, sample_agent_card):
        """clear_cache removes all cards from cache."""
        cache = AgentCardCache()
        cache.set("http://agent1.example.com", sample_agent_card)
        cache.set("http://agent2.example.com", sample_agent_card)
        resolver = CachedAgentCardResolver(
            httpx_client=mock_httpx_client,
            cache=cache,
        )
        resolver.clear_cache()
        assert cache.get("http://agent1.example.com") is None
        assert cache.get("http://agent2.example.com") is None
