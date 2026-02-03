"""Tool node with optional artifact wrapper."""

import uuid
from collections.abc import Awaitable, Callable
from time import monotonic

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentConfig
from my_agentic_serviceservice_order_specialist.platform.agent.metrics import (
    ToolMetricsLabels,
    record_tool_call,
)


class ArtifactWrapper:
    """Wrapper that intercepts tool execution to implement the Artifact Pattern.

    Large tool outputs are hidden and replaced with a summary + artifact ID.
    The agent can then use inspect_artifact to query the hidden data.
    """

    def __init__(self, config: AgentConfig, agent_slug: str):
        """Initialize the artifact wrapper.

        Args:
            config: Agent configuration with artifact settings
            agent_slug: The agent's slug for metrics labeling
        """
        self.config = config
        self.agent_slug = agent_slug

    async def __call__(
        self,
        tool_call_request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
        **kwargs,
    ) -> ToolMessage | Command:
        """Intercept tool execution and optionally hide large outputs.

        Args:
            tool_call_request: The tool call request
            handler: The original tool handler
            **kwargs: Additional arguments

        Returns:
            ToolMessage with content or artifact reference
        """
        tool_call = tool_call_request.tool_call
        tool_name = tool_call["name"]

        # Extract proxy tool name when using MCP Proxy's execute-tool
        proxy_tool_name = ""
        if "execute-tool" in tool_name:
            tool_args = tool_call.get("args", {})
            proxy_tool_name = tool_args.get("tool_name", "")

        labels = ToolMetricsLabels(self.agent_slug, tool_name, proxy_tool_name)
        start_time = monotonic()
        try:
            raw_response = await handler(tool_call_request)
        except Exception as e:
            record_tool_call(labels, duration=monotonic() - start_time, error=True)
            return ToolMessage(
                content=f"Error: {e!s}",
                tool_call_id=tool_call["id"],
                status="error",
            )

        record_tool_call(labels, duration=monotonic() - start_time)

        response_content = raw_response.content
        response_str = str(response_content)
        exceeds_threshold = len(response_str) > self.config.artifact_threshold
        is_exact_match = tool_name in self.config.always_visible_tools
        is_suffix_match = any(
            tool_name.endswith(suffix) for suffix in self.config.always_visible_tool_suffixes
        )
        is_exempt_from_hiding = is_exact_match or is_suffix_match

        if is_exempt_from_hiding or not exceeds_threshold:
            return ToolMessage(
                content=response_content,
                artifact=response_content,
                tool_call_id=tool_call["id"],
                name=tool_name,
            )

        artifact_id = f"art_{uuid.uuid4().hex[:8]}"
        summary = (
            f"Tool '{tool_name}' executed successfully.\n"
            f"Output Hidden (Size: {len(response_content)} chars).\n"
            f"Artifact ID: {artifact_id}\n"
            f"Snippet: {response_content[:200]}...\n"
            f"NEXT STEP: Use 'inspect_artifact' with ID '{artifact_id}' to analyze this data."
        )
        artifact_data = {
            "id": artifact_id,
            "data": response_content,
            "source": tool_name,
        }

        return ToolMessage(
            content=summary,
            artifact=artifact_data,
            tool_call_id=tool_call["id"],
            name=tool_name,
        )


class ToolNodeFactory:
    """Factory for creating tool nodes with optional artifact wrapping."""

    def __init__(self, config: AgentConfig, agent_slug: str):
        """Initialize the factory.

        Args:
            config: Agent configuration
            agent_slug: The agent's slug for metrics labeling
        """
        self.config = config
        self.agent_slug = agent_slug

    def create(self, tools: list[BaseTool]) -> ToolNode:
        """Create a tool node with optional artifact wrapper.

        Args:
            tools: List of tools to include

        Returns:
            Configured ToolNode
        """
        if self.config.artifact_threshold is not None:
            wrapper = ArtifactWrapper(self.config, self.agent_slug)
            return ToolNode(tools, awrap_tool_call=wrapper)
        return ToolNode(tools)
