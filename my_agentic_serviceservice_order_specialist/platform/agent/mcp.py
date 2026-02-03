"""MCP Client for LangGraph integration.

Provides a clean MCP client with LangChain StructuredTool conversion
for use with LangGraph's ToolNode.

Usage:
    client = MCPClient("http://localhost:8000/mcp")
    tools = await client.get_langchain_tools()

    tool_node = ToolNode(tools)
    llm_with_tools = llm.bind_tools(tools)
"""

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Tool as MCPTool
from tenacity import retry, stop_after_attempt, stop_after_delay, wait_fixed

from my_agentic_serviceservice_order_specialist.platform.constants import USER_AGENT


class MCPClientError(Exception):
    """MCP client error."""


class MCPClient:
    """MCP client for StreamableHTTP servers.

    Provides methods to list available tools and call them via the MCP protocol.
    Includes automatic retry logic for transient failures.
    """

    def __init__(
        self,
        server_url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 60.0,
        sse_read_timeout: float = 300.0,
        read_timeout: float = 120.0,
    ) -> None:
        """Initialize the MCP client.

        Args:
            server_url: URL of the MCP server endpoint
            headers: Optional HTTP headers to include in requests
            timeout: Connection timeout in seconds (default: 60.0)
            sse_read_timeout: SSE stream read timeout in seconds (default: 300.0)
            read_timeout: General read timeout in seconds (default: 120.0)
        """
        self.server_url = server_url
        # Store base headers (static configuration)
        self._base_headers = (headers or {}) | {"user-agent": USER_AGENT}
        self.timeout = timeout
        self.sse_read_timeout = sse_read_timeout
        self.read_timeout = timedelta(seconds=read_timeout)

    def __repr__(self) -> str:
        """Obfuscate sensitive fields in string representation."""
        headers_repr = "<obfuscated>" if self._base_headers else "None"
        return (
            f"MCPClient(server_url={self.server_url!r}, "
            f"headers={headers_repr}, "
            f"timeout={self.timeout}, "
            f"sse_read_timeout={self.sse_read_timeout}, "
            f"read_timeout={self.read_timeout})"
        )

    @asynccontextmanager
    async def _session(self) -> AsyncGenerator[ClientSession]:
        """Create an MCP session with context-aware headers."""
        http_client = httpx.AsyncClient(
            headers=self._base_headers,
            timeout=httpx.Timeout(
                connect=self.timeout,
                read=self.sse_read_timeout,
                write=self.timeout,
                pool=self.timeout,
            ),
        )
        async with http_client:
            async with streamable_http_client(
                url=self.server_url,
                http_client=http_client,
            ) as (read_stream, write_stream, _):
                async with ClientSession(
                    read_stream,
                    write_stream,
                    read_timeout_seconds=self.read_timeout,
                ) as session:
                    await session.initialize()
                    yield session

    @retry(
        wait=wait_fixed(2),
        stop=(stop_after_attempt(3) | stop_after_delay(10)),
        reraise=True,
    )
    async def list_tools(self) -> list[MCPTool]:
        """Fetch available tools from the MCP server.

        Retries up to 3 times with 2-second delays on transient failures.

        Returns:
            List of MCPTool definitions available on the server

        Raises:
            MCPClientError: If tool listing fails after retries
        """
        try:
            async with self._session() as session:
                response = await session.list_tools()
                return response.tools
        except Exception as e:
            raise MCPClientError(f"Failed to list tools: {e}") from e

    @retry(
        wait=wait_fixed(2),
        stop=(stop_after_attempt(3) | stop_after_delay(10)),
        reraise=True,
    )
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the MCP server and return the parsed response.

        Retries up to 3 times with 2-second delays on transient failures.

        Args:
            name: Name of the tool to invoke
            arguments: Dictionary of arguments to pass to the tool

        Returns:
            Parsed tool result (JSON decoded if possible, otherwise raw text)

        Raises:
            MCPClientError: If tool invocation fails after retries
        """
        try:
            async with self._session() as session:
                result = await session.call_tool(name, arguments)
                return self._parse_result(result)
        except Exception as e:
            raise MCPClientError(f"Failed to call tool '{name}': {e}") from e

    def _parse_result(self, result: Any) -> Any:
        """Parse tool result, attempting JSON decode.

        Args:
            result: Raw result from MCP tool call with content array

        Returns:
            Parsed content - single item if one result, list if multiple, None if empty
        """
        if not result.content:
            return None
        if len(result.content) == 1:
            return self._parse_content(result.content[0])
        return [self._parse_content(item) for item in result.content]

    def _parse_content(self, content: Any) -> Any:
        """Parse a single content item from tool output.

        Args:
            content: Content object with optional text attribute

        Returns:
            JSON-decoded dict/list if valid JSON, otherwise the raw text string
        """
        text = getattr(content, "text", None) or str(content)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
