"""Unit tests for A2A client wrapper."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    Artifact,
    Part,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.client import A2AClientWrapper, create_client
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import (
    A2AClientConfig,
    AuthConfig,
    ExecutionStrategy,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.discovery import AgentCardCache
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import A2AConnectionError


class TestA2AClientWrapperInit:
    """Tests for A2AClientWrapper initialization."""

    def test_init_with_base_url_only(self):
        """Client can be initialized with just base URL."""
        client = A2AClientWrapper("http://agent.example.com")
        assert client._base_url == "http://agent.example.com"
        assert client._config is not None
        assert client._auth is None

    def test_init_strips_trailing_slash(self):
        """Base URL trailing slash is stripped."""
        client = A2AClientWrapper("http://agent.example.com/")
        assert client._base_url == "http://agent.example.com"

    def test_init_with_config(self):
        """Client accepts custom configuration."""
        config = A2AClientConfig(timeout_seconds=30.0)
        client = A2AClientWrapper("http://agent.example.com", config=config)
        assert client._config.timeout_seconds == 30.0

    def test_init_with_auth(self):
        """Client accepts authentication configuration."""
        auth = AuthConfig(api_key="test-key")
        client = A2AClientWrapper("http://agent.example.com", auth=auth)
        assert client._auth is auth

    def test_init_with_httpx_client(self):
        """Client accepts pre-configured HTTP client."""
        httpx_client = httpx.AsyncClient()
        client = A2AClientWrapper(
            "http://agent.example.com",
            httpx_client=httpx_client,
        )
        assert client._httpx_client is httpx_client
        assert client._owns_httpx_client is False

    def test_init_with_agent_card_cache(self):
        """Client accepts shared agent card cache."""
        cache = AgentCardCache()
        client = A2AClientWrapper(
            "http://agent.example.com",
            agent_card_cache=cache,
        )
        assert client._cache is cache


class TestA2AClientWrapperProperties:
    """Tests for A2AClientWrapper properties."""

    def test_agent_card_initially_none(self):
        """agent_card is None before connection."""
        client = A2AClientWrapper("http://agent.example.com")
        assert client.agent_card is None

    def test_is_connected_initially_false(self):
        """is_connected is False before connection."""
        client = A2AClientWrapper("http://agent.example.com")
        assert client.is_connected is False


class TestA2AClientWrapperConnect:
    """Tests for A2AClientWrapper connection."""

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

    async def test_connect_creates_httpx_client_if_not_provided(self, sample_agent_card):
        """connect creates httpx client when not provided."""
        client = A2AClientWrapper("http://agent.example.com")

        with (
            patch(
                "my_agentic_serviceservice_order_specialist.platform.clients.a2a.client.CachedAgentCardResolver"
            ) as mock_resolver_cls,
            patch("my_agentic_serviceservice_order_specialist.platform.clients.a2a.client.ClientFactory") as mock_factory,
        ):
            mock_resolver = AsyncMock()
            mock_resolver.get_agent_card = AsyncMock(return_value=sample_agent_card)
            mock_resolver_cls.return_value = mock_resolver

            mock_sdk_client = AsyncMock()
            mock_factory.connect = AsyncMock(return_value=mock_sdk_client)

            await client.connect()

            assert client._httpx_client is not None
            assert client._owns_httpx_client is True

            await client.disconnect()

    async def test_connect_reuses_existing_connection(self, sample_agent_card):
        """connect is idempotent when already connected."""
        client = A2AClientWrapper("http://agent.example.com")

        with (
            patch(
                "my_agentic_serviceservice_order_specialist.platform.clients.a2a.client.CachedAgentCardResolver"
            ) as mock_resolver_cls,
            patch("my_agentic_serviceservice_order_specialist.platform.clients.a2a.client.ClientFactory") as mock_factory,
        ):
            mock_resolver = AsyncMock()
            mock_resolver.get_agent_card = AsyncMock(return_value=sample_agent_card)
            mock_resolver_cls.return_value = mock_resolver

            mock_sdk_client = AsyncMock()
            mock_factory.connect = AsyncMock(return_value=mock_sdk_client)

            await client.connect()
            await client.connect()

            assert mock_factory.connect.call_count == 1

            await client.disconnect()

    async def test_connect_raises_on_failure(self):
        """connect raises A2AConnectionError on failure."""
        client = A2AClientWrapper("http://agent.example.com")

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.client.CachedAgentCardResolver"
        ) as mock_resolver_cls:
            mock_resolver = AsyncMock()
            mock_resolver.get_agent_card = AsyncMock(side_effect=Exception("Connection failed"))
            mock_resolver_cls.return_value = mock_resolver

            with pytest.raises(A2AConnectionError) as exc_info:
                await client.connect()

            assert exc_info.value.url == "http://agent.example.com"


class TestA2AClientWrapperDisconnect:
    """Tests for A2AClientWrapper disconnect."""

    async def test_disconnect_closes_client(self):
        """disconnect closes the SDK client."""
        client = A2AClientWrapper("http://agent.example.com")
        mock_sdk_client = AsyncMock()
        client._client = mock_sdk_client

        await client.disconnect()

        mock_sdk_client.close.assert_called_once()
        assert client._client is None

    async def test_disconnect_closes_owned_httpx_client(self):
        """disconnect closes owned httpx client."""
        client = A2AClientWrapper("http://agent.example.com")
        mock_httpx_client = AsyncMock()
        client._httpx_client = mock_httpx_client
        client._owns_httpx_client = True

        await client.disconnect()

        mock_httpx_client.aclose.assert_called_once()
        assert client._httpx_client is None

    async def test_disconnect_does_not_close_external_httpx_client(self):
        """disconnect does not close externally provided httpx client."""
        mock_httpx_client = AsyncMock()
        client = A2AClientWrapper(
            "http://agent.example.com",
            httpx_client=mock_httpx_client,
        )

        await client.disconnect()

        mock_httpx_client.aclose.assert_not_called()


class TestA2AClientWrapperContextManager:
    """Tests for A2AClientWrapper async context manager."""

    async def test_context_manager_connects_and_disconnects(self):
        """Context manager connects on entry and disconnects on exit."""
        sample_card = AgentCard(
            name="Test",
            description="Test",
            url="http://example.com",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=True),
            skills=[],
            default_input_modes=["text"],
            default_output_modes=["text"],
        )

        with (
            patch(
                "my_agentic_serviceservice_order_specialist.platform.clients.a2a.client.CachedAgentCardResolver"
            ) as mock_resolver_cls,
            patch("my_agentic_serviceservice_order_specialist.platform.clients.a2a.client.ClientFactory") as mock_factory,
        ):
            mock_resolver = AsyncMock()
            mock_resolver.get_agent_card = AsyncMock(return_value=sample_card)
            mock_resolver_cls.return_value = mock_resolver

            mock_sdk_client = AsyncMock()
            mock_factory.connect = AsyncMock(return_value=mock_sdk_client)

            async with A2AClientWrapper("http://example.com") as client:
                assert client.is_connected is True

            assert client.is_connected is False  # type: ignore[unnecessary-comparison]


class TestA2AClientWrapperHeaders:
    """Tests for A2AClientWrapper header application."""

    def test_apply_headers_with_api_key(self):
        """_apply_headers_to_client adds API key header."""
        auth = AuthConfig(api_key="test-key", api_key_header="X-Custom-Key")
        client = A2AClientWrapper("http://example.com", auth=auth)
        client._httpx_client = httpx.AsyncClient()

        client._apply_headers_to_client()

        assert client._httpx_client.headers["X-Custom-Key"] == "test-key"

    def test_apply_headers_with_bearer_token(self):
        """_apply_headers_to_client adds Bearer token header."""
        auth = AuthConfig(bearer_token="jwt.token.here")
        client = A2AClientWrapper("http://example.com", auth=auth)
        client._httpx_client = httpx.AsyncClient()

        client._apply_headers_to_client()

        assert client._httpx_client.headers["Authorization"] == "Bearer jwt.token.here"

    def test_apply_headers_with_no_auth(self):
        """_apply_headers_to_client handles no auth gracefully."""
        client = A2AClientWrapper("http://example.com")
        client._httpx_client = httpx.AsyncClient()

        client._apply_headers_to_client()  # Should not raise

    async def test_inject_trace_context_propagates_correlation_id(self):
        """_inject_trace_context adds X-Request-ID from correlation context."""
        from my_agentic_serviceservice_order_specialist.platform.clients.a2a.client import _inject_trace_context
        from my_agentic_serviceservice_order_specialist.platform.observability import correlation_id_ctx

        request = httpx.Request("GET", "http://example.com")

        token = correlation_id_ctx.set("test-correlation-123")
        try:
            await _inject_trace_context(request)
            assert request.headers["X-Request-ID"] == "test-correlation-123"
        finally:
            correlation_id_ctx.reset(token)

    async def test_inject_trace_context_skips_correlation_id_when_not_set(self):
        """_inject_trace_context skips X-Request-ID when context is empty."""
        from my_agentic_serviceservice_order_specialist.platform.clients.a2a.client import _inject_trace_context

        request = httpx.Request("GET", "http://example.com")

        await _inject_trace_context(request)

        assert "X-Request-ID" not in request.headers

    async def test_inject_trace_context_propagates_trace_context(self):
        """_inject_trace_context injects OpenTelemetry trace context."""
        from opentelemetry import trace
        from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

        from my_agentic_serviceservice_order_specialist.platform.clients.a2a.client import _inject_trace_context

        request = httpx.Request("GET", "http://example.com")

        # Create a span context to propagate
        span_context = SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000CAFEBABE,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        span = NonRecordingSpan(span_context)

        with trace.use_span(span, end_on_exit=False):
            await _inject_trace_context(request)

        # traceparent header should be set with the trace context
        assert "traceparent" in request.headers
        traceparent = request.headers["traceparent"]
        assert "deadbeef" in traceparent.lower()
        assert "cafebabe" in traceparent.lower()


class TestA2AClientWrapperStrategySelection:
    """Tests for A2AClientWrapper strategy selection."""

    @pytest.fixture
    def connected_client(self):
        """Create a client with mocked connection."""
        client = A2AClientWrapper("http://example.com")
        client._client = AsyncMock()
        client._agent_card = AgentCard(
            name="Test",
            description="Test",
            url="http://example.com",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=True),
            skills=[],
            default_input_modes=["text"],
            default_output_modes=["text"],
        )
        return client

    def test_get_strategy_returns_sync_for_sync(self, connected_client):
        """_get_strategy returns SyncStrategy for SYNC."""
        from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.sync import SyncStrategy

        strategy = connected_client._get_strategy(ExecutionStrategy.SYNC)
        assert isinstance(strategy, SyncStrategy)

    def test_get_strategy_returns_streaming_for_streaming(self, connected_client):
        """_get_strategy returns StreamingStrategy for STREAMING."""
        from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.streaming import StreamingStrategy

        strategy = connected_client._get_strategy(ExecutionStrategy.STREAMING)
        assert isinstance(strategy, StreamingStrategy)

    def test_get_strategy_returns_polling_for_polling(self, connected_client):
        """_get_strategy returns PollingStrategy for POLLING."""
        from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.polling import PollingStrategy

        strategy = connected_client._get_strategy(ExecutionStrategy.POLLING)
        assert isinstance(strategy, PollingStrategy)

    def test_auto_strategy_prefers_streaming_when_supported(self, connected_client):
        """AUTO strategy uses streaming when agent supports it."""
        from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.streaming import StreamingStrategy

        connected_client._config = A2AClientConfig(streaming_enabled=True)
        strategy = connected_client._select_auto_strategy()
        assert isinstance(strategy, StreamingStrategy)

    def test_auto_strategy_falls_back_to_sync(self, connected_client):
        """AUTO strategy falls back to sync when streaming disabled."""
        from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.sync import SyncStrategy

        connected_client._config = A2AClientConfig(streaming_enabled=False)
        strategy = connected_client._select_auto_strategy()
        assert isinstance(strategy, SyncStrategy)


class TestA2AClientWrapperSendMessage:
    """Tests for A2AClientWrapper message sending."""

    @pytest.fixture
    def mock_client_with_response(self):
        """Create a client with mocked response."""
        client = A2AClientWrapper("http://example.com")
        client._client = AsyncMock()
        client._agent_card = AgentCard(
            name="Test",
            description="Test",
            url="http://example.com",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=False),
            skills=[],
            default_input_modes=["text"],
            default_output_modes=["text"],
        )
        return client

    async def test_send_text_creates_message(self, mock_client_with_response):
        """send_text creates a text message and sends it."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
            artifacts=[
                Artifact(
                    artifact_id="art-1",
                    parts=[Part(root=TextPart(text="Response"))],
                ),
            ],
        )

        async def mock_send_message(msg):
            yield (task, None)

        mock_client_with_response._client.send_message = mock_send_message

        result = await mock_client_with_response.send_text("Hello")

        assert result.response_text == "Response"
        assert result.task_id == "task-123"


class TestCreateClient:
    """Tests for create_client context manager."""

    async def test_create_client_connects_and_disconnects(self):
        """create_client manages connection lifecycle."""
        sample_card = AgentCard(
            name="Test",
            description="Test",
            url="http://example.com",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=True),
            skills=[],
            default_input_modes=["text"],
            default_output_modes=["text"],
        )

        with (
            patch(
                "my_agentic_serviceservice_order_specialist.platform.clients.a2a.client.CachedAgentCardResolver"
            ) as mock_resolver_cls,
            patch("my_agentic_serviceservice_order_specialist.platform.clients.a2a.client.ClientFactory") as mock_factory,
        ):
            mock_resolver = AsyncMock()
            mock_resolver.get_agent_card = AsyncMock(return_value=sample_card)
            mock_resolver_cls.return_value = mock_resolver

            mock_sdk_client = AsyncMock()
            mock_factory.connect = AsyncMock(return_value=mock_sdk_client)

            async with create_client("http://example.com") as client:
                assert client.is_connected is True

            assert client.is_connected is False  # type: ignore[unnecessary-comparison]
