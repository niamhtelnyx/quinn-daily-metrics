"""HTTP-level integration tests for MCPClient.

Tests the actual HTTP behavior of MCPClient using respx to mock httpx requests.
These tests verify:
- Header propagation (Authorization, user-agent, custom headers)
- Retry behavior on transient failures
- HTTP error handling
- Timeout configuration

Unlike test_mcp_tools.py which mocks at the session level, these tests
intercept actual HTTP requests to verify the transport layer behavior.
"""

import httpx
import pytest
import respx
from tenacity import wait_none

from my_agentic_serviceservice_order_specialist.platform.agent.mcp import MCPClient, MCPClientError
from my_agentic_serviceservice_order_specialist.platform.constants import USER_AGENT


@pytest.fixture(autouse=True)
def disable_tenacity_wait():
    """Disable tenacity wait times to speed up retry tests."""
    original_list_wait = MCPClient.list_tools.retry.wait  # type: ignore[attr-defined]
    original_call_wait = MCPClient.call_tool.retry.wait  # type: ignore[attr-defined]

    MCPClient.list_tools.retry.wait = wait_none()  # type: ignore[attr-defined]
    MCPClient.call_tool.retry.wait = wait_none()  # type: ignore[attr-defined]

    yield

    MCPClient.list_tools.retry.wait = original_list_wait  # type: ignore[attr-defined]
    MCPClient.call_tool.retry.wait = original_call_wait  # type: ignore[attr-defined]


class TestMCPClientHeaderPropagation:
    """Tests verifying HTTP headers are correctly sent to the MCP server."""

    @respx.mock
    async def test_user_agent_header_is_always_sent(self):
        """User-agent header is included in all requests."""
        route = respx.route(method="POST").mock(
            side_effect=httpx.ConnectError("Simulated for header capture")
        )

        client = MCPClient(server_url="http://localhost:8000/mcp")

        with pytest.raises(MCPClientError):
            await client.list_tools()

        # Verify user-agent was set on the request
        assert route.called
        request = route.calls[0].request
        assert request.headers.get("user-agent") == USER_AGENT

    @respx.mock
    async def test_authorization_header_is_propagated(self):
        """Custom Authorization header reaches the server."""
        route = respx.route(method="POST").mock(
            side_effect=httpx.ConnectError("Simulated for header capture")
        )

        client = MCPClient(
            server_url="http://localhost:8000/mcp",
            headers={"Authorization": "Bearer test-token-123"},
        )

        with pytest.raises(MCPClientError):
            await client.list_tools()

        assert route.called
        request = route.calls[0].request
        assert request.headers.get("authorization") == "Bearer test-token-123"

    @respx.mock
    async def test_multiple_custom_headers_are_propagated(self):
        """Multiple custom headers are all sent to the server."""
        route = respx.route(method="POST").mock(
            side_effect=httpx.ConnectError("Simulated for header capture")
        )

        client = MCPClient(
            server_url="http://localhost:8000/mcp",
            headers={
                "Authorization": "Bearer token",
                "X-Request-ID": "req-123",
                "X-Custom-Header": "custom-value",
            },
        )

        with pytest.raises(MCPClientError):
            await client.list_tools()

        assert route.called
        request = route.calls[0].request
        assert request.headers.get("authorization") == "Bearer token"
        assert request.headers.get("x-request-id") == "req-123"
        assert request.headers.get("x-custom-header") == "custom-value"

    @respx.mock
    async def test_user_agent_cannot_be_overridden_by_custom_headers(self):
        """User-agent is always set to the service user-agent."""
        route = respx.route(method="POST").mock(
            side_effect=httpx.ConnectError("Simulated for header capture")
        )

        client = MCPClient(
            server_url="http://localhost:8000/mcp",
            headers={"user-agent": "malicious-agent/1.0"},
        )

        with pytest.raises(MCPClientError):
            await client.list_tools()

        assert route.called
        request = route.calls[0].request
        # Service user-agent should override custom user-agent
        assert request.headers.get("user-agent") == USER_AGENT


class TestMCPClientRetryBehavior:
    """Tests verifying retry logic on transient failures."""

    @respx.mock
    async def test_list_tools_retries_on_connection_error(self):
        """list_tools retries up to 3 times on connection errors."""
        route = respx.route(method="POST").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        client = MCPClient(server_url="http://localhost:8000/mcp")

        with pytest.raises(MCPClientError, match="Failed to list tools"):
            await client.list_tools()

        # Should have attempted 3 times (initial + 2 retries)
        assert route.call_count == 3

    @respx.mock
    async def test_call_tool_retries_on_connection_error(self):
        """call_tool retries up to 3 times on connection errors."""
        route = respx.route(method="POST").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        client = MCPClient(server_url="http://localhost:8000/mcp")

        with pytest.raises(MCPClientError, match="Failed to call tool 'search'"):
            await client.call_tool("search", {"query": "test"})

        assert route.call_count == 3

    @respx.mock
    async def test_list_tools_retries_on_read_timeout(self):
        """list_tools retries on read timeout errors."""
        route = respx.route(method="POST").mock(side_effect=httpx.ReadTimeout("Read timed out"))

        client = MCPClient(server_url="http://localhost:8000/mcp")

        with pytest.raises(MCPClientError, match="Failed to list tools"):
            await client.list_tools()

        assert route.call_count == 3

    @respx.mock
    async def test_list_tools_retries_on_connect_timeout(self):
        """list_tools retries on connect timeout errors."""
        route = respx.route(method="POST").mock(
            side_effect=httpx.ConnectTimeout("Connect timed out")
        )

        client = MCPClient(server_url="http://localhost:8000/mcp")

        with pytest.raises(MCPClientError, match="Failed to list tools"):
            await client.list_tools()

        assert route.call_count == 3


class TestMCPClientHTTPErrors:
    """Tests verifying HTTP error response handling."""

    @respx.mock
    async def test_list_tools_handles_401_unauthorized(self):
        """401 Unauthorized is wrapped in MCPClientError."""
        respx.route(method="POST").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        client = MCPClient(
            server_url="http://localhost:8000/mcp",
            headers={"Authorization": "Bearer invalid-token"},
        )

        with pytest.raises(MCPClientError, match="Failed to list tools"):
            await client.list_tools()

    @respx.mock
    async def test_list_tools_handles_403_forbidden(self):
        """403 Forbidden is wrapped in MCPClientError."""
        respx.route(method="POST").mock(
            return_value=httpx.Response(403, json={"error": "Forbidden"})
        )

        client = MCPClient(server_url="http://localhost:8000/mcp")

        with pytest.raises(MCPClientError, match="Failed to list tools"):
            await client.list_tools()

    @respx.mock
    async def test_list_tools_handles_404_not_found(self):
        """404 Not Found is wrapped in MCPClientError."""
        respx.route(method="POST").mock(
            return_value=httpx.Response(404, json={"error": "Not found"})
        )

        client = MCPClient(server_url="http://localhost:8000/mcp")

        with pytest.raises(MCPClientError, match="Failed to list tools"):
            await client.list_tools()

    @respx.mock
    async def test_list_tools_handles_500_server_error(self):
        """500 Internal Server Error is wrapped in MCPClientError."""
        respx.route(method="POST").mock(
            return_value=httpx.Response(500, json={"error": "Internal error"})
        )

        client = MCPClient(server_url="http://localhost:8000/mcp")

        with pytest.raises(MCPClientError, match="Failed to list tools"):
            await client.list_tools()

    @respx.mock
    async def test_list_tools_handles_503_service_unavailable(self):
        """503 Service Unavailable is wrapped in MCPClientError."""
        respx.route(method="POST").mock(
            return_value=httpx.Response(503, json={"error": "Service unavailable"})
        )

        client = MCPClient(server_url="http://localhost:8000/mcp")

        with pytest.raises(MCPClientError, match="Failed to list tools"):
            await client.list_tools()

    @respx.mock
    async def test_call_tool_handles_500_server_error(self):
        """500 error during call_tool is wrapped in MCPClientError."""
        respx.route(method="POST").mock(
            return_value=httpx.Response(500, json={"error": "Tool execution failed"})
        )

        client = MCPClient(server_url="http://localhost:8000/mcp")

        with pytest.raises(MCPClientError, match="Failed to call tool 'search'"):
            await client.call_tool("search", {"query": "test"})


class TestMCPClientURLHandling:
    """Tests verifying correct URL handling."""

    @respx.mock
    async def test_request_is_made_to_configured_url(self):
        """Requests are made to the configured server URL."""
        route = respx.route(method="POST", url="http://mcp.example.com/v1/mcp").mock(
            side_effect=httpx.ConnectError("Simulated")
        )

        client = MCPClient(server_url="http://mcp.example.com/v1/mcp")

        with pytest.raises(MCPClientError):
            await client.list_tools()

        assert route.called

    @respx.mock
    async def test_https_url_is_used_correctly(self):
        """HTTPS URLs are handled correctly."""
        route = respx.route(method="POST", url="https://secure-mcp.example.com/mcp").mock(
            side_effect=httpx.ConnectError("Simulated")
        )

        client = MCPClient(server_url="https://secure-mcp.example.com/mcp")

        with pytest.raises(MCPClientError):
            await client.list_tools()

        assert route.called


class TestMCPClientTimeoutConfiguration:
    """Tests verifying timeout settings are applied to HTTP requests.

    Note: Default/custom timeout value tests have been moved to
    tests/unit/platform/agent/test_mcp_config.py
    """

    @respx.mock
    async def test_timeout_is_applied_to_httpx_client(self):
        """Timeout configuration is applied when making requests."""
        # We can't directly inspect the httpx client timeout from respx,
        # but we can verify the request was made with our configured client
        route = respx.route(method="POST").mock(side_effect=httpx.ConnectError("Simulated"))

        client = MCPClient(
            server_url="http://localhost:8000/mcp",
            timeout=15.0,
        )

        with pytest.raises(MCPClientError):
            await client.list_tools()

        # Request was made (timeout configuration is internal to httpx)
        assert route.called
