"""LangGraph integration components.

This module provides LangGraph-specific implementations including:
- LangGraphMCPTools: Converts MCP tools to LangChain StructuredTools
- LangGraphMessageParser: Converts LangGraph messages to framework-agnostic types
- LangGraphAgent: A runnable agent that implements the Agent protocol
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from datetime import datetime
from typing import Any, Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.graph.state import CompiledStateGraph
from mcp.types import Tool as MCPTool
from openinference.instrumentation import using_session
from opentelemetry import trace
from pydantic import Field, create_model

from my_agentic_serviceservice_order_specialist.platform.agent.config import A2AConfig, AgentIdentity, MCPConfig
from my_agentic_serviceservice_order_specialist.platform.agent.mcp import MCPClient
from my_agentic_serviceservice_order_specialist.platform.agent.messages import (
    ExecutionResult,
    Message,
    StreamEvent,
)
from my_agentic_serviceservice_order_specialist.platform.agent.metrics import (
    AgentMetricsLabels,
    collect_agent_metrics,
)
from my_agentic_serviceservice_order_specialist.platform.agent.protocol import Agent
from my_agentic_serviceservice_order_specialist.platform.clients.a2a import A2AClientConfig, A2AClientWrapper
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import AuthConfig
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.tools import (
    A2AToolConfig,
    create_a2a_tool,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Type alias for tool fetcher functions (injectable dependency)
type ToolFetcher = Callable[[Sequence[MCPConfig]], Awaitable[list[BaseTool]]]
type A2AToolFetcher = Callable[[Sequence[A2AConfig]], Awaitable[list[BaseTool]]]


class LangGraphMCPTools:
    """Adapter that converts MCP tools to LangChain StructuredTools.

    This class fetches tools from an MCP server and converts them to
    LangChain-compatible StructuredTools for use with LangGraph's ToolNode.
    """

    def __init__(self, mcp_client: MCPClient, tool_prefix: str | None = None) -> None:
        """Initialize with an MCP client.

        Args:
            mcp_client: Configured MCPClient for tool discovery and execution
            tool_prefix: Optional prefix to add after 'mcp_' for collision avoidance
                         between multiple MCP servers. Final format: mcp_<prefix>_<name>
        """
        self.mcp_client = mcp_client
        self.tool_prefix = tool_prefix

    @classmethod
    def from_config(cls, config: MCPConfig) -> "LangGraphMCPTools":
        """Create a LangGraphMCPTools instance from an MCPConfig.

        Args:
            config: MCP server configuration

        Returns:
            Configured LangGraphMCPTools instance
        """
        mcp_client = MCPClient(
            server_url=config.server_url,
            headers=config.headers,
            timeout=config.timeout,
            sse_read_timeout=config.sse_read_timeout,
            read_timeout=config.read_timeout,
        )
        return cls(mcp_client, config.tool_prefix)

    async def convert_tools(self) -> list[StructuredTool]:
        """Convert MCP tools to LangChain StructuredTools.

        Returns:
            List of StructuredTool instances ready for use with LangGraph
        """
        tools = await self.mcp_client.list_tools()
        return [self._to_langchain_tool(tool) for tool in tools if tool.inputSchema]

    def _prefixed_name(self, name: str) -> str:
        """Apply mcp_ prefix and optional tool prefix to tool name.

        All MCP tools get the 'mcp_' prefix for metrics distinction.
        If a tool_prefix is configured, it's added after 'mcp_'.

        Args:
            name: Original tool name

        Returns:
            Prefixed name: mcp_<name> or mcp_<tool_prefix>_<name>
        """
        if self.tool_prefix:
            return f"mcp_{self.tool_prefix}_{name}"
        return f"mcp_{name}"

    def _to_langchain_tool(self, mcp_tool: MCPTool) -> StructuredTool:
        """Convert a single MCP tool to a LangChain StructuredTool.

        Args:
            mcp_tool: MCP tool definition with name, description, and input schema

        Returns:
            StructuredTool with async coroutine that delegates to the MCP client
        """
        # Store original name for MCP calls, use prefixed name for LangChain
        original_name = mcp_tool.name
        prefixed_name = self._prefixed_name(original_name)

        async def invoke(**kwargs: Any) -> str:
            # Always call MCP with the original tool name
            result = await self.mcp_client.call_tool(original_name, kwargs)
            if result is None:
                return "No result"
            if isinstance(result, str):
                return result
            return json.dumps(result)

        args_schema = self._build_args_schema(mcp_tool)
        tool_kwargs: dict[str, Any] = {
            "name": prefixed_name,
            "description": mcp_tool.description or f"MCP tool: {original_name}",
            "coroutine": invoke,
        }
        if args_schema is not None:
            tool_kwargs["args_schema"] = args_schema

        return StructuredTool(**tool_kwargs)

    @staticmethod
    def _json_type_to_python(json_type: str) -> type:
        """Convert JSON schema type string to Python type.

        Args:
            json_type: JSON schema type (string, integer, number, boolean, object, array)

        Returns:
            Corresponding Python type, defaults to str for unknown types
        """
        return {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "object": dict,
            "array": list,
        }.get(json_type, str)

    @classmethod
    def _build_args_schema(cls, mcp_tool: MCPTool) -> type | None:
        """Build a Pydantic model from an MCP tool's input schema.

        Args:
            mcp_tool: MCP tool with inputSchema containing JSON Schema properties

        Returns:
            Dynamically created Pydantic model class, or None if schema is invalid/empty
        """
        if not hasattr(mcp_tool, "inputSchema") or not mcp_tool.inputSchema:
            return None

        schema = mcp_tool.inputSchema
        if not isinstance(schema, dict) or "properties" not in schema:
            logger.warning(
                "Invalid tool schema for '%s': expected dict with 'properties' key, "
                "got %s. Tool will not have argument validation.",
                mcp_tool.name,
                type(schema).__name__,
            )
            return None

        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        if not properties:
            return None

        fields = {}
        for name, info in properties.items():
            field_type = cls._json_type_to_python(info.get("type", "string"))
            description = info.get("description", "")
            default = info.get("default", ...)

            if name not in required and default == ...:
                default = None
                field_type = field_type | None

            if default == ...:
                fields[name] = (field_type, Field(description=description))
            else:
                fields[name] = (
                    field_type,
                    Field(default=default, description=description),
                )

        model_name = f"{mcp_tool.name.replace('-', '_').title()}Args"
        return create_model(model_name, **fields)  # type: ignore

    @classmethod
    async def fetch_all(cls, configs: Sequence[MCPConfig]) -> list[BaseTool]:
        """Fetch tools from multiple MCP servers concurrently.

        Args:
            configs: Sequence of MCP server configurations

        Returns:
            Combined list of tools from all MCP servers

        Raises:
            ExceptionGroup: If any MCP server fails to respond
            ValueError: If tool name collision is detected across MCP servers
        """

        async def fetch_from_config(config: MCPConfig) -> list[StructuredTool]:
            return await cls.from_config(config).convert_tools()

        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch_from_config(config)) for config in configs]

        # Collect tools and detect collisions
        tools: list[BaseTool] = []
        seen: dict[str, str] = {}  # tool_name -> server_url
        for config, task in zip(configs, tasks):
            for tool in task.result():
                if tool.name in seen:
                    raise ValueError(
                        f"Tool name collision: '{tool.name}' from {config.server_url} "
                        f"conflicts with {seen[tool.name]}. "
                        f"Set tool_prefix on one or both MCPConfigs."
                    )
                seen[tool.name] = config.server_url
                tools.append(tool)
        return tools


class LangGraphA2ATools:
    """Adapter that creates LangChain StructuredTools from A2A remote agents.

    This class fetches agent cards from A2A agents and creates tools
    that can be used with LangGraph's ToolNode.
    """

    @classmethod
    async def fetch_all(cls, configs: Sequence[A2AConfig]) -> list[BaseTool]:
        """Fetch tools from multiple A2A agents concurrently with graceful degradation.

        Args:
            configs: Sequence of A2A remote agent configurations

        Returns:
            Combined list of tools from all successfully connected A2A agents.
            Agents that fail to connect are logged and skipped.

        Raises:
            ValueError: If tool name collision is detected
        """

        async def fetch_from_config(
            config: A2AConfig,
        ) -> tuple[A2AConfig, list[StructuredTool] | Exception]:
            """Fetch tools for a single A2A agent, returning exception on failure."""
            try:
                auth = None
                if config.api_key or config.bearer_token:
                    auth = AuthConfig(
                        api_key=config.api_key,
                        bearer_token=config.bearer_token,
                    )

                client_config = A2AClientConfig(timeout_seconds=config.timeout_seconds)

                client = A2AClientWrapper(
                    base_url=config.base_url,
                    config=client_config,
                    auth=auth,
                )

                tools: list[StructuredTool] = []
                async with client:
                    agent_card = await client.get_agent_card()

                    if not agent_card.skills:
                        # Create a single tool for the agent
                        tool_config = A2AToolConfig(
                            base_url=config.base_url,
                            tool_prefix=config.tool_prefix,
                            name_override=config.name_override,
                            description_override=config.description_override,
                            client_config=client_config,
                            auth=auth,
                        )
                        tools.append(create_a2a_tool(tool_config, agent_card=agent_card))
                    else:
                        # Create a tool for each skill
                        for skill in agent_card.skills:
                            tool_config = A2AToolConfig(
                                base_url=config.base_url,
                                skill_id=skill.id,
                                tool_prefix=config.tool_prefix,
                                client_config=client_config,
                                auth=auth,
                            )
                            tools.append(create_a2a_tool(tool_config, agent_card=agent_card))

                return (config, tools)
            except Exception as e:
                return (config, e)

        if not configs:
            return []

        # Fetch all concurrently - exceptions are caught inside fetch_from_config
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch_from_config(config)) for config in configs]

        results = [task.result() for task in tasks]

        # Collect tools and handle failures gracefully
        tools: list[BaseTool] = []
        seen: dict[str, str] = {}  # tool_name -> base_url
        for config, result in results:
            if isinstance(result, Exception):
                logger.warning(
                    "A2A agent unavailable at %s: %s. Continuing without this agent.",
                    config.base_url,
                    result,
                )
                continue

            for tool in result:
                if tool.name in seen:
                    raise ValueError(
                        f"Tool name collision: '{tool.name}' from {config.base_url} "
                        f"conflicts with {seen[tool.name]}. "
                        f"Use tool_prefix or name_override on one or both A2AConfigs."
                    )
                seen[tool.name] = config.base_url
                tools.append(tool)
        return tools


class LangGraphMessageParser:
    """Parser that converts LangGraph messages to framework-agnostic types.

    Transforms LangGraph state dictionaries and stream events into the
    common ExecutionResult and StreamEvent types used across the application.
    """

    def to_execution_result(
        self,
        langgraph_result: dict[str, Any],
        thread_id: str,
    ) -> ExecutionResult:
        """Convert LangGraph state to ExecutionResult.

        Args:
            langgraph_result: State dict from Agent.run()
            thread_id: The thread ID used

        Returns:
            Framework-agnostic ExecutionResult
        """
        messages = langgraph_result.get("messages", [])
        reasoning_steps = langgraph_result.get("reasoning_steps", 0)

        # Extract the final response
        response = self._extract_response(messages)

        # Convert messages to framework-agnostic format
        converted_messages = self._convert_messages(messages)

        return ExecutionResult(
            response=response,
            messages=converted_messages,
            reasoning_steps=reasoning_steps,
            thread_id=thread_id,
            metadata={
                "framework": "langgraph",
                "raw_state": langgraph_result,
            },
        )

    def to_stream_event(self, event: dict[str, Any]) -> StreamEvent:
        """Convert LangGraph stream event to StreamEvent.

        Args:
            LangGraph's astream() with default stream_mode="updates" returns events
            keyed by node name: {'node_name': {'messages': [...], ...}}

        Returns:
            Framework-agnostic StreamEvent
        """
        # LangGraph events are keyed by node name (e.g., 'agent', 'tools')
        # Iterate through event to find messages in any node's state update
        for node_name, node_data in event.items():
            if not isinstance(node_data, dict):
                continue

            messages = node_data.get("messages", [])
            if not messages:
                continue

            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage):
                if last_msg.tool_calls:
                    return StreamEvent(
                        event_type="tool_call",
                        data={
                            "node": node_name,
                            "tool_calls": last_msg.tool_calls,
                            "content": self._extract_content(last_msg),
                        },
                    )
                else:
                    return StreamEvent(
                        event_type="message",
                        data={
                            "node": node_name,
                            "content": self._extract_content(last_msg),
                        },
                    )
            elif hasattr(last_msg, "tool_call_id"):
                # ToolMessage
                return StreamEvent(
                    event_type="tool_result",
                    data={
                        "node": node_name,
                        "tool_call_id": getattr(last_msg, "tool_call_id", None),
                        "name": getattr(last_msg, "name", None),
                        "content": self._extract_content(last_msg),
                    },
                )

        # Default: pass through as generic event
        return StreamEvent(
            event_type="state_update",
            data=event,
        )

    def _extract_response(self, messages: list[BaseMessage]) -> str:
        """Extract the final assistant response from messages.

        Args:
            messages: List of LangChain messages

        Returns:
            The final assistant response text
        """
        # Find the last AI message that doesn't have tool calls
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                # Skip messages that are just tool calls
                if msg.tool_calls:
                    continue
                content = msg.content
                if isinstance(content, str):
                    return content
                # Handle list content (e.g., multimodal)
                if isinstance(content, list):
                    text_parts = [
                        p.get("text", "") if isinstance(p, dict) else str(p) for p in content
                    ]
                    return " ".join(text_parts)
        return ""

    def _convert_messages(self, messages: list[BaseMessage]) -> list[Message]:
        """Convert LangChain messages to framework-agnostic Messages.

        Args:
            messages: List of LangChain BaseMessage instances

        Returns:
            List of framework-agnostic Message instances
        """
        converted = []
        for msg in messages:
            role = self._get_role(msg)
            content = self._extract_content(msg)

            # Extract tool-related fields
            tool_calls = None
            tool_call_id = None
            name = None

            if isinstance(msg, AIMessage) and msg.tool_calls:
                tool_calls = [
                    {
                        "id": tc.get("id", ""),
                        "name": tc.get("name", ""),
                        "args": tc.get("args", {}),
                    }
                    for tc in msg.tool_calls
                ]

            if hasattr(msg, "tool_call_id"):
                tool_call_id = msg.tool_call_id

            if hasattr(msg, "name"):
                name = msg.name

            converted.append(
                Message(
                    role=role,
                    content=content,
                    tool_calls=tool_calls,
                    tool_call_id=tool_call_id,
                    name=name,
                )
            )

        return converted

    @staticmethod
    def _get_role(msg: BaseMessage) -> str:
        """Get the role string for a message.

        Args:
            msg: LangChain message

        Returns:
            Role string ("system", "user", "assistant", "tool")
        """
        if isinstance(msg, SystemMessage):
            return "system"
        elif isinstance(msg, HumanMessage):
            return "user"
        elif isinstance(msg, AIMessage):
            return "assistant"
        else:
            # ToolMessage or other
            return "tool"

    @staticmethod
    def _extract_content(msg: BaseMessage) -> str:
        """Extract string content from a message.

        Args:
            msg: LangChain message

        Returns:
            Message content as string
        """
        content = msg.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = [p.get("text", "") if isinstance(p, dict) else str(p) for p in content]
            return " ".join(text_parts)
        return str(content)


class InitialStateBuilder(Protocol):
    """Protocol for building the initial state for an agent."""

    def __call__(
        self,
        message: str,
        thread_id: str,
        utc_now: datetime | None = None,
    ) -> dict[str, Any]:
        """Build the initial state for an agent.

        Args:
            message: User's input message
            thread_id: Thread ID for conversation persistence, if None, a new thread will be created
            utc_now: Optional UTC now time, if None, the current time will be used

        Returns:
            Initial state for the agent
        """
        ...


class LangGraphAgent(Agent):
    """A configured, runnable LangGraph agent instance."""

    def __init__(
        self,
        graph: CompiledStateGraph,
        identity: AgentIdentity,
        initial_state_builder: InitialStateBuilder,
        message_parser: LangGraphMessageParser | None = None,
        tools: list[BaseTool] | None = None,
    ) -> None:
        """Initialize the agent.

        Args:
            graph: Compiled LangGraph ready for execution
            identity: Agent identity information
            initial_state_builder: Initial state builder
            message_parser: Optional custom message parser
            tools: Optional list of tools available to the agent
        """
        self._graph = graph
        self._identity = identity
        self._initial_state_builder = initial_state_builder
        self._message_parser = message_parser or LangGraphMessageParser()
        self._tools = tools or []

    @property
    def identity(self) -> AgentIdentity:
        return self._identity

    @property
    def name(self) -> str:
        return self._identity.name

    @property
    def description(self) -> str:
        return self._identity.description

    @property
    def slug(self) -> str:
        return self._identity.slug

    @property
    def tools(self) -> list[BaseTool]:
        """Tools available to this agent."""
        return self._tools

    async def run(
        self,
        message: str,
        thread_id: str,
        utc_now: datetime | None = None,
    ) -> ExecutionResult:
        """Run the agent with a user message and return the execution result.
        If thread_id is provided, the conversation will be continued in the existing thread.
        If thread_id is not provided, a new thread will be created and returned.

        Args:
            message: User's input message
            thread_id: Thread ID for conversation persistence, if None, a new thread will be created
            utc_now: Optional UTC now time, if None, the current time will be used

        Returns:
            Framework-agnostic ExecutionResult
        """
        init_state = self._initial_state_builder(
            message=message,
            thread_id=thread_id,
            utc_now=utc_now,
        )

        with tracer.start_as_current_span(self.name):
            with using_session(thread_id):
                async with collect_agent_metrics(AgentMetricsLabels(self.slug)):
                    result = await self._graph.ainvoke(
                        init_state,
                        config={"configurable": {"thread_id": thread_id}},
                    )

        return self._message_parser.to_execution_result(
            langgraph_result=result,
            thread_id=thread_id,
        )

    async def run_stream(
        self,
        message: str,
        thread_id: str,
        utc_now: datetime | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Run the agent with streaming output.
        If thread_id is provided, the conversation will be continued in the existing thread.
        If thread_id is not provided, a new thread will be created and returned.

        Args:
            message: User's input message
            thread_id: Thread ID for conversation persistence, if None, a new thread will be created
            utc_now: Optional UTC now time, if None, the current time will be used

        Yields:
            Framework-agnostic StreamEvent
        """
        init_state = self._initial_state_builder(
            message=message,
            thread_id=thread_id,
            utc_now=utc_now,
        )

        with tracer.start_as_current_span(self.name):
            with using_session(session_id=thread_id):
                async with collect_agent_metrics(AgentMetricsLabels(self.slug)):
                    async for event in self._graph.astream(
                        init_state,
                        config={"configurable": {"thread_id": thread_id}},
                    ):
                        yield self._message_parser.to_stream_event(event)
