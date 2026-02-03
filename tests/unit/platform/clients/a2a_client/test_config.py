"""Unit tests for A2A client configuration."""

from dataclasses import FrozenInstanceError

import pytest

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import (
    A2AClientConfig,
    AuthConfig,
    ExecutionStrategy,
)


class TestExecutionStrategy:
    """Tests for ExecutionStrategy enum."""

    def test_all_values_exist(self):
        """All expected strategy values exist."""
        assert ExecutionStrategy.AUTO == "auto"
        assert ExecutionStrategy.SYNC == "sync"
        assert ExecutionStrategy.STREAMING == "streaming"
        assert ExecutionStrategy.POLLING == "polling"

    def test_is_string_enum(self):
        """ExecutionStrategy values are usable as strings."""
        assert str(ExecutionStrategy.AUTO) == "auto"


class TestA2AClientConfig:
    """Tests for A2AClientConfig dataclass."""

    def test_default_values(self):
        """Config has sensible defaults."""
        config = A2AClientConfig()
        assert config.timeout_seconds == 60.0
        assert config.streaming_enabled is True
        assert config.polling_enabled is True
        assert config.preferred_strategy == ExecutionStrategy.POLLING
        assert config.poll_interval_seconds == 1.0
        assert config.max_poll_time_seconds == 600.0
        assert config.poll_backoff_multiplier == 1.5
        assert config.poll_max_interval_seconds == 30.0
        assert config.max_retries == 3
        assert config.retry_delay_seconds == 1.0
        assert config.agent_card_cache_ttl_seconds == 3600.0
        assert config.max_conversation_turns == 10

    def test_custom_values(self):
        """Config accepts custom values."""
        config = A2AClientConfig(
            timeout_seconds=120.0,
            streaming_enabled=False,
            polling_enabled=False,
            preferred_strategy=ExecutionStrategy.SYNC,
            poll_interval_seconds=2.0,
            max_poll_time_seconds=600.0,
            max_conversation_turns=5,
        )
        assert config.timeout_seconds == 120.0
        assert config.streaming_enabled is False
        assert config.polling_enabled is False
        assert config.preferred_strategy == ExecutionStrategy.SYNC
        assert config.poll_interval_seconds == 2.0
        assert config.max_poll_time_seconds == 600.0
        assert config.max_conversation_turns == 5

    def test_frozen_immutability(self):
        """A2AClientConfig is immutable."""
        config = A2AClientConfig()
        with pytest.raises(FrozenInstanceError):
            config.timeout_seconds = 120.0  # type: ignore


class TestAuthConfig:
    """Tests for AuthConfig dataclass."""

    def test_default_values(self):
        """AuthConfig has correct defaults."""
        config = AuthConfig()
        assert config.api_key is None
        assert config.api_key_header == "X-API-Key"
        assert config.bearer_token is None

    def test_api_key_config(self):
        """AuthConfig accepts API key."""
        config = AuthConfig(
            api_key="sk-test-key-123",
            api_key_header="X-Custom-Key",
        )
        assert config.api_key == "sk-test-key-123"
        assert config.api_key_header == "X-Custom-Key"

    def test_bearer_token_config(self):
        """AuthConfig accepts bearer token."""
        config = AuthConfig(bearer_token="jwt.token.here")
        assert config.bearer_token == "jwt.token.here"

    def test_frozen_immutability(self):
        """AuthConfig is immutable."""
        config = AuthConfig(api_key="test")
        with pytest.raises(FrozenInstanceError):
            config.api_key = "new-key"  # type: ignore
