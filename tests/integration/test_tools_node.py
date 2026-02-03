"""Integration tests for ToolNode components.

Tests the ArtifactWrapper and ToolNodeFactory including
artifact pattern, error handling, and metrics recording.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.messages import ToolMessage
from langchain_core.tools import StructuredTool

from my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools import (
    ArtifactWrapper,
    ToolNodeFactory,
)
from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentConfig


@pytest.fixture
def agent_config() -> AgentConfig:
    """Create a test agent config."""
    return AgentConfig(
        max_reasoning_steps=10,
        always_visible_tools=frozenset({"always_visible_tool"}),
        recursion_limit=50,
        artifact_threshold=100,  # Low threshold for testing
        max_context_tokens=150000,
    )


@pytest.fixture
def agent_config_no_artifacts() -> AgentConfig:
    """Create a config with artifacts disabled."""
    return AgentConfig(
        max_reasoning_steps=10,
        always_visible_tools=frozenset(),
        recursion_limit=50,
        artifact_threshold=None,  # type: ignore[arg-type]
        max_context_tokens=150000,
    )


@pytest.fixture
def artifact_wrapper(agent_config) -> ArtifactWrapper:
    """Create an ArtifactWrapper."""
    return ArtifactWrapper(config=agent_config, agent_slug="test-agent")


@pytest.fixture
def mock_tool_call_request():
    """Create a mock tool call request."""
    request = Mock()
    request.tool_call = {
        "id": "call_123",
        "name": "search",
        "args": {"query": "test"},
    }
    return request


class TestArtifactWrapperNormalExecution:
    """Tests for normal tool execution (under threshold)."""

    async def test_small_output_not_hidden(self, artifact_wrapper, mock_tool_call_request):
        """Small outputs are returned as-is."""
        handler = AsyncMock(
            return_value=ToolMessage(content="Small result", tool_call_id="call_123")
        )

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call") as mock_record:
            result = await artifact_wrapper(mock_tool_call_request, handler)

        assert result.content == "Small result"
        assert result.artifact == "Small result"
        assert result.tool_call_id == "call_123"
        mock_record.assert_called_once()

    async def test_always_visible_tool_not_hidden(self, agent_config):
        """Tools in always_visible_tools are never hidden."""
        wrapper = ArtifactWrapper(config=agent_config, agent_slug="test-agent")

        request = Mock()
        request.tool_call = {
            "id": "call_123",
            "name": "always_visible_tool",
            "args": {},
        }

        # Large output that would normally be hidden
        large_content = "x" * 500
        handler = AsyncMock(
            return_value=ToolMessage(content=large_content, tool_call_id="call_123")
        )

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call"):
            result = await wrapper(request, handler)

        # Should NOT be hidden despite exceeding threshold
        assert result.content == large_content
        assert "Artifact ID" not in result.content


class TestArtifactWrapperLargeOutput:
    """Tests for large output handling (artifact pattern)."""

    async def test_large_output_hidden(self, artifact_wrapper, mock_tool_call_request):
        """Large outputs are hidden and replaced with summary."""
        large_content = "x" * 500  # Exceeds threshold of 100

        handler = AsyncMock(
            return_value=ToolMessage(content=large_content, tool_call_id="call_123")
        )

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call"):
            result = await artifact_wrapper(mock_tool_call_request, handler)

        # Content should be a summary, not the full output
        assert "Tool 'search' executed successfully" in result.content
        assert "Output Hidden" in result.content
        assert "Artifact ID: art_" in result.content
        assert "inspect_artifact" in result.content
        assert len(result.content) < len(large_content)

    async def test_large_output_artifact_contains_data(
        self, artifact_wrapper, mock_tool_call_request
    ):
        """Artifact field contains the full data."""
        large_content = "important data " * 50

        handler = AsyncMock(
            return_value=ToolMessage(content=large_content, tool_call_id="call_123")
        )

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call"):
            result = await artifact_wrapper(mock_tool_call_request, handler)

        # Artifact should contain full data
        assert isinstance(result.artifact, dict)
        assert result.artifact["data"] == large_content
        assert result.artifact["source"] == "search"
        assert result.artifact["id"].startswith("art_")

    async def test_summary_includes_snippet(self, artifact_wrapper, mock_tool_call_request):
        """Summary includes first 200 chars as snippet."""
        large_content = "A" * 100 + "B" * 100 + "C" * 300

        handler = AsyncMock(
            return_value=ToolMessage(content=large_content, tool_call_id="call_123")
        )

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call"):
            result = await artifact_wrapper(mock_tool_call_request, handler)

        # Should have first 200 chars in snippet
        assert "A" * 100 in result.content
        assert "B" * 100 in result.content
        assert "C" * 100 not in result.content  # Beyond 200 chars


class TestArtifactWrapperErrorHandling:
    """Tests for error handling in tool execution."""

    async def test_handler_exception_returns_error_message(
        self, artifact_wrapper, mock_tool_call_request
    ):
        """Exceptions are caught and returned as error ToolMessage."""
        handler = AsyncMock(side_effect=ValueError("Tool failed"))

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call") as mock_record:
            result = await artifact_wrapper(mock_tool_call_request, handler)

        assert "Error: Tool failed" in result.content
        assert result.tool_call_id == "call_123"
        assert result.status == "error"
        # Should record with error=True
        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args
        assert call_kwargs[1]["error"] is True

    async def test_connection_error_handled(self, artifact_wrapper, mock_tool_call_request):
        """Connection errors are handled gracefully."""
        handler = AsyncMock(side_effect=ConnectionError("Network unreachable"))

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call"):
            result = await artifact_wrapper(mock_tool_call_request, handler)

        assert "Error: Network unreachable" in result.content
        assert result.status == "error"


class TestArtifactWrapperMetrics:
    """Tests for metrics recording."""

    async def test_metrics_recorded_on_success(self, artifact_wrapper, mock_tool_call_request):
        """Metrics are recorded on successful execution."""
        handler = AsyncMock(return_value=ToolMessage(content="result", tool_call_id="call_123"))

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call") as mock_record:
            await artifact_wrapper(mock_tool_call_request, handler)

        mock_record.assert_called_once()
        call_args = mock_record.call_args
        labels = call_args[0][0]
        assert labels.agent == "test-agent"
        assert labels.tool_name == "search"
        assert "duration" in call_args[1]
        assert call_args[1].get("error") is None or call_args[1].get("error") is False

    async def test_metrics_recorded_on_error(self, artifact_wrapper, mock_tool_call_request):
        """Metrics are recorded with error flag on failure."""
        handler = AsyncMock(side_effect=Exception("Failed"))

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call") as mock_record:
            await artifact_wrapper(mock_tool_call_request, handler)

        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args[1]
        assert call_kwargs["error"] is True


class TestArtifactWrapperProxyTool:
    """Tests for MCP proxy tool handling."""

    async def test_proxy_tool_extracts_inner_name(self, artifact_wrapper):
        """Extracts proxy tool name from execute-tool args."""
        request = Mock()
        request.tool_call = {
            "id": "call_123",
            "name": "mcp-execute-tool",
            "args": {"tool_name": "inner_search", "params": {}},
        }

        handler = AsyncMock(return_value=ToolMessage(content="result", tool_call_id="call_123"))

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call") as mock_record:
            await artifact_wrapper(request, handler)

        labels = mock_record.call_args[0][0]
        assert labels.proxy_tool_name == "inner_search"


class TestToolNodeFactory:
    """Tests for ToolNodeFactory."""

    def test_create_with_artifact_wrapper(self, agent_config):
        """Creates ToolNode with artifact wrapper when threshold set."""
        factory = ToolNodeFactory(config=agent_config, agent_slug="test-agent")

        def dummy_tool(x: str) -> str:
            """Dummy tool."""
            return x

        tools = [
            StructuredTool.from_function(func=dummy_tool, name="dummy", description="A dummy tool")
        ]

        node = factory.create(tools)  # type: ignore[arg-type]

        # Node should be created (we can't easily inspect internals)
        assert node is not None

    def test_create_without_artifact_wrapper(self, agent_config_no_artifacts):
        """Creates ToolNode without wrapper when threshold is None."""
        factory = ToolNodeFactory(config=agent_config_no_artifacts, agent_slug="test-agent")

        def dummy_tool(x: str) -> str:
            """Dummy tool."""
            return x

        tools = [
            StructuredTool.from_function(func=dummy_tool, name="dummy", description="A dummy tool")
        ]

        node = factory.create(tools)  # type: ignore[arg-type]

        assert node is not None


class TestArtifactWrapperEdgeCases:
    """Tests for edge cases."""

    async def test_exactly_at_threshold_not_hidden(self, agent_config):
        """Content exactly at threshold is not hidden."""
        wrapper = ArtifactWrapper(config=agent_config, agent_slug="test-agent")

        request = Mock()
        request.tool_call = {
            "id": "call_123",
            "name": "tool",
            "args": {},
        }

        # Exactly 100 chars (threshold)
        content = "x" * 100
        handler = AsyncMock(return_value=ToolMessage(content=content, tool_call_id="call_123"))

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call"):
            result = await wrapper(request, handler)

        # Should NOT be hidden (not exceeding, just equal)
        assert result.content == content

    async def test_one_over_threshold_is_hidden(self, agent_config):
        """Content one char over threshold is hidden."""
        wrapper = ArtifactWrapper(config=agent_config, agent_slug="test-agent")

        request = Mock()
        request.tool_call = {
            "id": "call_123",
            "name": "tool",
            "args": {},
        }

        # 101 chars (threshold is 100)
        content = "x" * 101
        handler = AsyncMock(return_value=ToolMessage(content=content, tool_call_id="call_123"))

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call"):
            result = await wrapper(request, handler)

        # Should be hidden
        assert "Artifact ID" in result.content

    async def test_empty_response_not_hidden(self, artifact_wrapper):
        """Empty responses are not hidden."""
        request = Mock()
        request.tool_call = {
            "id": "call_123",
            "name": "tool",
            "args": {},
        }

        handler = AsyncMock(return_value=ToolMessage(content="", tool_call_id="call_123"))

        with patch("my_agentic_serviceservice_order_specialist.agents.knowledge.nodes.tools.record_tool_call"):
            result = await artifact_wrapper(request, handler)

        assert result.content == ""
