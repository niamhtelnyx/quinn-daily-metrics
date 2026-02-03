"""Integration tests for MCP tools integration.

Tests the MCPClient and LangGraphMCPTools classes with mocked MCP servers.

Note: Parsing method tests (_parse_result, _parse_content) have been moved to
tests/unit/platform/agent/test_mcp_parsing.py
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.tools import StructuredTool
from mcp.types import Tool as MCPTool
from tenacity import wait_none

from my_agentic_serviceservice_order_specialist.platform.agent.config import MCPConfig
from my_agentic_serviceservice_order_specialist.platform.agent.langgraph import LangGraphMCPTools
from my_agentic_serviceservice_order_specialist.platform.agent.mcp import MCPClient, MCPClientError


@pytest.fixture(autouse=True)
def disable_tenacity_wait():
    """Disable tenacity wait times to speed up retry tests.

    Tenacity decorators capture wait strategy at import time, so we need
    to modify the retry object directly on the decorated methods.
    """
    # Store original wait strategies (tenacity adds .retry attr at runtime)
    original_list_wait = MCPClient.list_tools.retry.wait  # type: ignore[attr-defined]
    original_call_wait = MCPClient.call_tool.retry.wait  # type: ignore[attr-defined]

    # Set wait to zero
    MCPClient.list_tools.retry.wait = wait_none()  # type: ignore[attr-defined]
    MCPClient.call_tool.retry.wait = wait_none()  # type: ignore[attr-defined]

    yield

    # Restore original wait strategies
    MCPClient.list_tools.retry.wait = original_list_wait  # type: ignore[attr-defined]
    MCPClient.call_tool.retry.wait = original_call_wait  # type: ignore[attr-defined]


class TestMCPClientInit:
    """Tests for MCPClient initialization."""

    def test_init_with_required_args(self):
        """Can create client with just server URL."""
        client = MCPClient(server_url="http://localhost:8000/mcp")
        assert client.server_url == "http://localhost:8000/mcp"

    def test_init_stores_headers(self):
        """Headers are stored with user-agent added."""
        client = MCPClient(
            server_url="http://localhost:8000/mcp",
            headers={"Authorization": "Bearer token"},
        )
        assert "Authorization" in client._base_headers
        assert "user-agent" in client._base_headers

    def test_init_default_timeout(self):
        """Default timeout is 60 seconds."""
        client = MCPClient(server_url="http://localhost:8000/mcp")
        assert client.timeout == 60.0

    def test_init_custom_timeout(self):
        """Can set custom timeout."""
        client = MCPClient(server_url="http://localhost:8000/mcp", timeout=30.0)
        assert client.timeout == 30.0

    def test_init_sse_read_timeout(self):
        """Default SSE read timeout is 300 seconds."""
        client = MCPClient(server_url="http://localhost:8000/mcp")
        assert client.sse_read_timeout == 300.0


class TestMCPClientListTools:
    """Tests for MCPClient.list_tools() method."""

    @pytest.fixture
    def stub_session(self):
        """Create a stub MCP session with canned tool responses."""
        session = AsyncMock()
        response = Mock()
        response.tools = [
            MCPTool(
                name="search",
                description="Search for information",
                inputSchema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            ),
            MCPTool(
                name="fetch",
                description="Fetch a URL",
                inputSchema={
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                },
            ),
        ]
        session.list_tools = AsyncMock(return_value=response)
        return session

    async def test_list_tools_returns_tools(self, stub_session: AsyncMock):
        """list_tools returns tools from the server."""
        client = MCPClient(server_url="http://localhost:8000/mcp")

        @asynccontextmanager
        async def stub_session_cm():
            yield stub_session

        with patch.object(client, "_session", stub_session_cm):
            tools = await client.list_tools()

        assert len(tools) == 2
        assert tools[0].name == "search"
        assert tools[1].name == "fetch"

    async def test_list_tools_calls_session_list_tools(self, stub_session: AsyncMock):
        """list_tools calls session.list_tools()."""
        client = MCPClient(server_url="http://localhost:8000/mcp")

        @asynccontextmanager
        async def stub_session_cm():
            yield stub_session

        with patch.object(client, "_session", stub_session_cm):
            await client.list_tools()

        stub_session.list_tools.assert_called_once()

    async def test_list_tools_raises_on_error(self):
        """list_tools raises MCPClientError on failure."""
        client = MCPClient(server_url="http://localhost:8000/mcp")

        with patch.object(client, "_session", side_effect=ConnectionError("Connection refused")):
            with pytest.raises(MCPClientError, match="Failed to list tools"):
                await client.list_tools()


class TestMCPClientCallTool:
    """Tests for MCPClient.call_tool() method."""

    @pytest.fixture
    def stub_session(self):
        """Create a stub MCP session with canned call_tool response."""
        session = AsyncMock()
        result = Mock()
        result.content = [Mock(text='{"result": "success"}')]
        session.call_tool = AsyncMock(return_value=result)
        return session

    async def test_call_tool_returns_result(self, stub_session: AsyncMock):
        """call_tool returns parsed result."""
        client = MCPClient(server_url="http://localhost:8000/mcp")

        @asynccontextmanager
        async def stub_session_cm():
            yield stub_session

        with patch.object(client, "_session", stub_session_cm):
            result = await client.call_tool("search", {"query": "test"})

        assert result == {"result": "success"}

    async def test_call_tool_passes_arguments(self, stub_session: AsyncMock):
        """call_tool passes arguments to session.call_tool()."""
        client = MCPClient(server_url="http://localhost:8000/mcp")

        @asynccontextmanager
        async def stub_session_cm():
            yield stub_session

        with patch.object(client, "_session", stub_session_cm):
            await client.call_tool("search", {"query": "test", "limit": 10})

        stub_session.call_tool.assert_called_once_with("search", {"query": "test", "limit": 10})

    async def test_call_tool_raises_on_error(self):
        """call_tool raises MCPClientError on failure."""
        client = MCPClient(server_url="http://localhost:8000/mcp")

        with patch.object(client, "_session", side_effect=ConnectionError("Connection refused")):
            with pytest.raises(MCPClientError, match="Failed to call tool 'search'"):
                await client.call_tool("search", {"query": "test"})


class TestLangGraphMCPToolsInit:
    """Tests for LangGraphMCPTools initialization."""

    def test_init_stores_client(self):
        """Stores the MCP client."""
        mock_client = Mock(spec=MCPClient)
        tools = LangGraphMCPTools(mcp_client=mock_client)
        assert tools.mcp_client is mock_client

    def test_init_stores_prefix(self):
        """Stores the tool prefix."""
        mock_client = Mock(spec=MCPClient)
        tools = LangGraphMCPTools(mcp_client=mock_client, tool_prefix="github")
        assert tools.tool_prefix == "github"

    def test_init_prefix_defaults_none(self):
        """Tool prefix defaults to None."""
        mock_client = Mock(spec=MCPClient)
        tools = LangGraphMCPTools(mcp_client=mock_client)
        assert tools.tool_prefix is None


class TestLangGraphMCPToolsFromConfig:
    """Tests for LangGraphMCPTools.from_config() class method."""

    def test_from_config_creates_client(self):
        """Creates MCPClient from config."""
        config = MCPConfig(
            server_url="http://localhost:8000/mcp",
            tool_prefix="test",
        )
        tools = LangGraphMCPTools.from_config(config)
        assert tools.mcp_client.server_url == "http://localhost:8000/mcp"
        assert tools.tool_prefix == "test"

    def test_from_config_passes_headers(self):
        """Headers are passed to MCPClient."""
        config = MCPConfig(
            server_url="http://localhost:8000/mcp",
            headers={"Authorization": "Bearer token"},
        )
        tools = LangGraphMCPTools.from_config(config)
        assert "Authorization" in tools.mcp_client._base_headers

    def test_from_config_passes_timeout(self):
        """Timeout is passed to MCPClient."""
        config = MCPConfig(
            server_url="http://localhost:8000/mcp",
            timeout=30.0,
        )
        tools = LangGraphMCPTools.from_config(config)
        assert tools.mcp_client.timeout == 30.0


class TestLangGraphMCPToolsConvertTools:
    """Tests for LangGraphMCPTools.convert_tools() method."""

    @pytest.fixture
    def stub_mcp_tools(self) -> list[MCPTool]:
        """Create stub MCP tools with canned configuration."""
        return [
            MCPTool(
                name="search",
                description="Search for information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                },
            ),
            MCPTool(
                name="fetch",
                description="Fetch a URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to fetch"},
                        "timeout": {"type": "integer", "description": "Timeout"},
                    },
                    "required": ["url"],
                },
            ),
        ]

    async def test_convert_tools_returns_structured_tools(self, stub_mcp_tools: list[MCPTool]):
        """convert_tools returns StructuredTool instances."""
        mock_client = Mock(spec=MCPClient)
        mock_client.list_tools = AsyncMock(return_value=stub_mcp_tools)

        tools_adapter = LangGraphMCPTools(mcp_client=mock_client)
        tools = await tools_adapter.convert_tools()

        assert len(tools) == 2
        assert all(isinstance(t, StructuredTool) for t in tools)

    async def test_convert_tools_adds_mcp_prefix(self, stub_mcp_tools: list[MCPTool]):
        """Tool names get mcp_ prefix."""
        mock_client = Mock(spec=MCPClient)
        mock_client.list_tools = AsyncMock(return_value=stub_mcp_tools)

        tools_adapter = LangGraphMCPTools(mcp_client=mock_client)
        tools = await tools_adapter.convert_tools()

        assert tools[0].name == "mcp_search"
        assert tools[1].name == "mcp_fetch"

    async def test_convert_tools_adds_tool_prefix(self, stub_mcp_tools: list[MCPTool]):
        """Tool names include tool_prefix when set."""
        mock_client = Mock(spec=MCPClient)
        mock_client.list_tools = AsyncMock(return_value=stub_mcp_tools)

        tools_adapter = LangGraphMCPTools(mcp_client=mock_client, tool_prefix="github")
        tools = await tools_adapter.convert_tools()

        assert tools[0].name == "mcp_github_search"
        assert tools[1].name == "mcp_github_fetch"

    async def test_convert_tools_preserves_description(self, stub_mcp_tools: list[MCPTool]):
        """Tool descriptions are preserved."""
        mock_client = Mock(spec=MCPClient)
        mock_client.list_tools = AsyncMock(return_value=stub_mcp_tools)

        tools_adapter = LangGraphMCPTools(mcp_client=mock_client)
        tools = await tools_adapter.convert_tools()

        assert tools[0].description == "Search for information"
        assert tools[1].description == "Fetch a URL"

    async def test_convert_tools_skips_tools_without_schema(self):
        """Tools without inputSchema are skipped."""
        mock_client = Mock(spec=MCPClient)
        # Tool with empty inputSchema (falsy) should be skipped
        mock_client.list_tools = AsyncMock(
            return_value=[
                MCPTool(name="no_schema", description="No schema", inputSchema={}),
                MCPTool(
                    name="with_schema",
                    description="Has schema",
                    inputSchema={
                        "type": "object",
                        "properties": {"x": {"type": "string"}},
                    },
                ),
            ]
        )

        tools_adapter = LangGraphMCPTools(mcp_client=mock_client)
        tools = await tools_adapter.convert_tools()

        # Only the tool with non-empty schema should be converted
        assert len(tools) == 1
        assert tools[0].name == "mcp_with_schema"

    async def test_convert_tools_creates_callable(self, stub_mcp_tools: list[MCPTool]):
        """Converted tools have async callable coroutine."""
        mock_client = Mock(spec=MCPClient)
        mock_client.list_tools = AsyncMock(return_value=stub_mcp_tools)
        mock_client.call_tool = AsyncMock(return_value="result")

        tools_adapter = LangGraphMCPTools(mcp_client=mock_client)
        tools = await tools_adapter.convert_tools()

        # The tool should be callable
        result = await tools[0].ainvoke({"query": "test"})
        assert result == "result"

    async def test_convert_tools_callable_uses_original_name(self, stub_mcp_tools: list[MCPTool]):
        """Tool callable uses original MCP name, not prefixed name."""
        mock_client = Mock(spec=MCPClient)
        mock_client.list_tools = AsyncMock(return_value=stub_mcp_tools)
        mock_client.call_tool = AsyncMock(return_value="result")

        tools_adapter = LangGraphMCPTools(mcp_client=mock_client, tool_prefix="gh")
        tools = await tools_adapter.convert_tools()

        # Call the tool
        await tools[0].ainvoke({"query": "test"})

        # Should call MCP with original name, not prefixed name
        mock_client.call_tool.assert_called_once_with("search", {"query": "test"})


class TestLangGraphMCPToolsFetchAll:
    """Tests for LangGraphMCPTools.fetch_all() class method."""

    async def test_fetch_all_from_multiple_configs(self):
        """fetch_all fetches tools from multiple MCP servers."""
        configs = [
            MCPConfig(server_url="http://server1/mcp", tool_prefix="s1"),
            MCPConfig(server_url="http://server2/mcp", tool_prefix="s2"),
        ]

        with patch.object(LangGraphMCPTools, "from_config") as mock_from_config:
            # Note: Mock(name="x") sets debug name, not .name attribute
            tool1 = Mock()
            tool1.name = "mcp_s1_tool1"
            tool2 = Mock()
            tool2.name = "mcp_s2_tool2"

            mock_adapter1 = Mock()
            mock_adapter1.convert_tools = AsyncMock(return_value=[tool1])
            mock_adapter2 = Mock()
            mock_adapter2.convert_tools = AsyncMock(return_value=[tool2])
            mock_from_config.side_effect = [mock_adapter1, mock_adapter2]

            tools = await LangGraphMCPTools.fetch_all(configs)

        assert len(tools) == 2

    async def test_fetch_all_detects_name_collision(self):
        """fetch_all raises ValueError on tool name collision."""
        configs = [
            MCPConfig(server_url="http://server1/mcp"),
            MCPConfig(server_url="http://server2/mcp"),
        ]

        with patch.object(LangGraphMCPTools, "from_config") as mock_from_config:
            # Both servers return a tool with the same name
            # Note: Mock(name="x") sets debug name, not .name attribute
            tool1 = Mock()
            tool1.name = "mcp_search"
            tool2 = Mock()
            tool2.name = "mcp_search"

            mock_adapter1 = Mock()
            mock_adapter1.convert_tools = AsyncMock(return_value=[tool1])
            mock_adapter2 = Mock()
            mock_adapter2.convert_tools = AsyncMock(return_value=[tool2])
            mock_from_config.side_effect = [mock_adapter1, mock_adapter2]

            with pytest.raises(ValueError, match="Tool name collision"):
                await LangGraphMCPTools.fetch_all(configs)

    async def test_fetch_all_empty_configs(self):
        """fetch_all with empty configs returns empty list."""
        tools = await LangGraphMCPTools.fetch_all([])
        assert tools == []
