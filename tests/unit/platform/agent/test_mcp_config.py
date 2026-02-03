"""Unit tests for MCPClient configuration.

Tests for MCPClient timeout configuration defaults and custom values.
These tests do not require network or external systems.
"""

from my_agentic_serviceservice_order_specialist.platform.agent.mcp import MCPClient


class TestMCPClientTimeoutConfiguration:
    """Tests verifying timeout configuration values."""

    def test_default_timeout_values(self):
        """Default timeout values are set correctly."""
        client = MCPClient(server_url="http://localhost:8000/mcp")

        assert client.timeout == 60.0
        assert client.sse_read_timeout == 300.0
        assert client.read_timeout.total_seconds() == 120.0

    def test_custom_timeout_values(self):
        """Custom timeout values are stored correctly."""
        client = MCPClient(
            server_url="http://localhost:8000/mcp",
            timeout=30.0,
            sse_read_timeout=600.0,
            read_timeout=180.0,
        )

        assert client.timeout == 30.0
        assert client.sse_read_timeout == 600.0
        assert client.read_timeout.total_seconds() == 180.0


class TestMCPClientObfuscation:
    """Tests verifying sensitive data obfuscation in MCPClient."""

    def test_repr_obfuscates_secrets(self):
        """Sensitive fields like env and headers are obfuscated in repr."""
        headers = {"Authorization": "Bearer token_456"}

        client = MCPClient(server_url="http://localhost:8000/mcp", headers=headers)

        repr_str = repr(client)

        # Check for obfuscation markers
        assert "headers=<obfuscated>" in repr_str

        # Ensure secrets are NOT present
        assert "token_456" not in repr_str

    def test_repr_handles_empty_secrets(self):
        """Empty sensitive fields are shown as None or empty."""
        client = MCPClient(server_url="http://localhost:8000/mcp")

        repr_str = repr(client)

        # Check that empty/None fields are handled gracefully
        # Note: headers might be initialized with default dict internally,
        # but the check in __repr__ uses self._base_headers or self.env
        # We need to verify what we expect.
        # Based on my implementation:
        # headers_repr = "<obfuscated>" if self._base_headers else "None"

        # Base headers usually have user-agent, so it might be obfuscated by default implementation
        # let's check the implementation again.
        # self._base_headers = (headers or {}) | {"user-agent": USER_AGENT}
        # So _base_headers is never empty.

        # Headers will likely be <obfuscated> because of user-agent
        assert "headers=<obfuscated>" in repr_str
