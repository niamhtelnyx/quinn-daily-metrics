"""Core A2A client wrapper.

Provides a high-level interface for communicating with A2A protocol agents,
handling connection management, strategy selection, and response processing.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

import httpx
from a2a.client.base_client import BaseClient
from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.types import AgentCard, Message, TaskIdParams
from opentelemetry import propagate

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import (
    A2AClientConfig,
    AuthConfig,
    ExecutionStrategy,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.discovery import (
    AgentCardCache,
    CachedAgentCardResolver,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import A2AConnectionError
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.messages import create_text_message
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.base import (
    ExecutionResult,
    StreamEvent,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.polling import PollingStrategy
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.streaming import (
    StreamingStrategy,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.sync import SyncStrategy
from my_agentic_serviceservice_order_specialist.platform.observability import correlation_id_ctx


async def _inject_trace_context(request: httpx.Request) -> None:
    """Inject OpenTelemetry trace context into each outgoing request.

    This ensures trace context is propagated per-request rather than
    per-connection, enabling proper distributed trace correlation.

    Note: Must be async because httpx AsyncClient awaits event hooks.
    """
    propagate.inject(request.headers)

    correlation_id = correlation_id_ctx.get()
    if correlation_id:
        request.headers["X-Request-ID"] = correlation_id


class A2AClientWrapper:
    """High-level A2A client wrapper.

    Provides a simplified interface for communicating with A2A agents,
    with automatic strategy selection based on agent capabilities and
    client preferences.
    """

    def __init__(
        self,
        base_url: str,
        config: A2AClientConfig | None = None,
        auth: AuthConfig | None = None,
        httpx_client: httpx.AsyncClient | None = None,
        agent_card_cache: AgentCardCache | None = None,
    ):
        """Initialize the client wrapper.

        Args:
            base_url: Base URL of the A2A agent.
            config: Optional client configuration.
            auth: Optional authentication configuration.
            httpx_client: Optional pre-configured HTTP client.
            agent_card_cache: Optional shared agent card cache.
        """
        self._base_url = base_url.rstrip("/")
        self._config = config or A2AClientConfig()
        self._auth = auth
        self._httpx_client = httpx_client
        self._owns_httpx_client = httpx_client is None
        self._cache = agent_card_cache or AgentCardCache(
            default_ttl_seconds=self._config.agent_card_cache_ttl_seconds
        )
        self._client: BaseClient | None = None
        self._agent_card: AgentCard | None = None

    @property
    def agent_card(self) -> AgentCard | None:
        """Get the cached agent card, if available."""
        return self._agent_card

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected."""
        return self._client is not None

    async def connect(self) -> None:
        """Establish connection to the A2A agent.

        Fetches the agent card and initializes the underlying client.

        Raises:
            A2AConnectionError: If connection fails.
        """
        if self._client is not None:
            return

        if self._httpx_client is None:
            self._httpx_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._config.timeout_seconds),
                event_hooks={"request": [_inject_trace_context]},
            )
            self._owns_httpx_client = True

        self._apply_headers_to_client()

        resolver = CachedAgentCardResolver(
            httpx_client=self._httpx_client,
            cache=self._cache,
            config=self._config,
        )

        try:
            self._agent_card = await resolver.get_agent_card(self._base_url)
        except Exception as e:
            raise A2AConnectionError(
                message=str(e),
                url=self._base_url,
            ) from e

        sdk_config = self._build_sdk_config()

        self._client = cast(
            BaseClient,
            await ClientFactory.connect(
                agent=self._agent_card,
                client_config=sdk_config,
            ),
        )

    async def disconnect(self) -> None:
        """Disconnect from the A2A agent and clean up resources."""
        if self._client is not None:
            await self._client.close()
            self._client = None

        if self._owns_httpx_client and self._httpx_client is not None:
            await self._httpx_client.aclose()
            self._httpx_client = None

    async def __aenter__(self) -> "A2AClientWrapper":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def send_text(
        self,
        text: str,
        *,
        task_id: str | None = None,
        context_id: str | None = None,
        strategy: ExecutionStrategy | None = None,
    ) -> ExecutionResult:
        """Send a simple text message.

        Convenience method for the most common use case.

        Args:
            text: The text message to send.
            task_id: Optional task ID for multi-turn conversations.
            context_id: Optional context ID for grouping.
            strategy: Optional execution strategy override.

        Returns:
            ExecutionResult with the agent's response.
        """
        message = create_text_message(text, task_id=task_id, context_id=context_id)
        return await self.send_message(message, strategy=strategy)

    async def send_message(
        self,
        message: Message,
        *,
        strategy: ExecutionStrategy | None = None,
    ) -> ExecutionResult:
        """Send a message to the agent.

        Args:
            message: The message to send.
            strategy: Optional execution strategy override.

        Returns:
            ExecutionResult with the agent's response.
        """
        await self._ensure_connected()

        effective_strategy = strategy or self._config.preferred_strategy
        executor = self._get_strategy(effective_strategy)
        return await executor.execute(message)

    async def send_text_stream(
        self,
        text: str,
        *,
        task_id: str | None = None,
        context_id: str | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Send a text message and stream the response.

        Args:
            text: The text message to send.
            task_id: Optional task ID for multi-turn conversations.
            context_id: Optional context ID for grouping.

        Yields:
            StreamEvent objects as they arrive.
        """
        message = create_text_message(text, task_id=task_id, context_id=context_id)
        async for event in self.send_message_stream(message):
            yield event

    async def send_message_stream(
        self,
        message: Message,
    ) -> AsyncIterator[StreamEvent]:
        """Send a message and stream the response.

        Args:
            message: The message to send.

        Yields:
            StreamEvent objects as they arrive.
        """
        await self._ensure_connected()
        assert self._client is not None

        streaming = StreamingStrategy(self._client)
        async for event in streaming.execute_stream(message):
            yield event

    async def cancel_task(self, task_id: str) -> None:
        """Cancel a running task.

        Args:
            task_id: The ID of the task to cancel.
        """
        await self._ensure_connected()
        assert self._client is not None

        await self._client.cancel_task(TaskIdParams(id=task_id))

    async def get_agent_card(self, *, force_refresh: bool = False) -> AgentCard:
        """Get the agent card.

        Args:
            force_refresh: If True, fetch fresh from the agent.

        Returns:
            The AgentCard for this agent.
        """
        if force_refresh or self._agent_card is None:
            await self.connect()
            if self._client is not None:
                self._agent_card = await self._client.get_card()

        assert self._agent_card is not None
        return self._agent_card

    async def _ensure_connected(self) -> None:
        """Ensure the client is connected."""
        if self._client is None:
            await self.connect()

    def _apply_headers_to_client(self) -> None:
        """Apply authentication headers to the HTTP client."""
        if self._httpx_client is None:
            return

        if self._auth is None:
            return

        if self._auth.api_key:
            self._httpx_client.headers[self._auth.api_key_header] = self._auth.api_key

        if self._auth.bearer_token:
            self._httpx_client.headers["Authorization"] = f"Bearer {self._auth.bearer_token}"

    def _build_sdk_config(self) -> ClientConfig:
        """Build the SDK ClientConfig from our config."""
        return ClientConfig(
            streaming=self._config.streaming_enabled,
            polling=self._config.polling_enabled,
            httpx_client=self._httpx_client,
        )

    def _get_strategy(
        self,
        strategy: ExecutionStrategy,
    ) -> SyncStrategy | StreamingStrategy | PollingStrategy:
        """Get the appropriate execution strategy.

        Args:
            strategy: The requested strategy.

        Returns:
            The execution strategy to use.
        """
        assert self._client is not None

        if strategy == ExecutionStrategy.STREAMING:
            return StreamingStrategy(self._client)
        if strategy == ExecutionStrategy.POLLING:
            return PollingStrategy(self._client, self._config)
        if strategy == ExecutionStrategy.SYNC:
            return SyncStrategy(self._client)

        return self._select_auto_strategy()

    def _select_auto_strategy(
        self,
    ) -> SyncStrategy | StreamingStrategy | PollingStrategy:
        """Automatically select the best strategy based on capabilities.

        Returns:
            The selected execution strategy.
        """
        assert self._client is not None

        if (
            self._config.streaming_enabled
            and self._agent_card
            and self._agent_card.capabilities
            and self._agent_card.capabilities.streaming
        ):
            return StreamingStrategy(self._client)

        return SyncStrategy(self._client)


@asynccontextmanager
async def create_client(
    base_url: str,
    config: A2AClientConfig | None = None,
    auth: AuthConfig | None = None,
) -> AsyncIterator[A2AClientWrapper]:
    """Create an A2A client as an async context manager.

    Convenience function for creating and managing a client.

    Args:
        base_url: Base URL of the A2A agent.
        config: Optional client configuration.
        auth: Optional authentication configuration.

    Yields:
        Connected A2AClientWrapper instance.
    """
    client = A2AClientWrapper(base_url, config=config, auth=auth)
    try:
        await client.connect()
        yield client
    finally:
        await client.disconnect()
