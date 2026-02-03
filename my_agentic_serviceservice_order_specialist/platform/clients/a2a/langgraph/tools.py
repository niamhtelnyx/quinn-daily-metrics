"""LangGraph tool wrappers for A2A client.

This module provides functions to create LangGraph-compatible tools
from A2A agent skills.
"""

from dataclasses import dataclass
from typing import Any

from a2a.types import AgentCard, AgentSkill
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.client import A2AClientWrapper
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import A2AClientConfig, AuthConfig


@dataclass
class A2AToolConfig:
    """Configuration for creating an A2A tool.

    Attributes:
        base_url: Base URL of the A2A agent.
        skill_id: Optional skill ID to create tool for (uses first skill if not specified).
        tool_prefix: Optional prefix for tool names. If None, derives from agent card name.
            Final format: a2a_<tool_prefix>_<skill_name>
        name_override: Optional override for the tool name (bypasses prefix logic).
        description_override: Optional override for the tool description.
        client_config: Optional client configuration.
        auth: Optional authentication configuration.
    """

    base_url: str
    skill_id: str | None = None
    tool_prefix: str | None = None
    name_override: str | None = None
    description_override: str | None = None
    client_config: A2AClientConfig | None = None
    auth: AuthConfig | None = None


def _json_schema_to_pydantic_model(
    name: str,
    schema: dict[str, Any] | None,
) -> type[BaseModel]:
    """Convert a JSON Schema to a Pydantic model.

    Args:
        name: Name for the generated model.
        schema: JSON Schema dict (can be None for simple text input).

    Returns:
        A dynamically created Pydantic model class.
    """
    if schema is None:
        return create_model(
            name,
            query=(str, Field(description="The query or message to send to the agent")),
        )

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    field_definitions: dict[str, Any] = {}

    for prop_name, prop_schema in properties.items():
        prop_type = _json_schema_type_to_python(prop_schema)
        prop_desc = prop_schema.get("description", "")
        is_required = prop_name in required

        if is_required:
            field_definitions[prop_name] = (prop_type, Field(description=prop_desc))
        else:
            default = prop_schema.get("default", None)
            field_definitions[prop_name] = (
                prop_type | None,
                Field(default=default, description=prop_desc),
            )

    if not field_definitions:
        field_definitions["query"] = (
            str,
            Field(description="The query or message to send to the agent"),
        )

    return create_model(name, **field_definitions)


def _json_schema_type_to_python(schema: dict[str, Any]) -> type:
    """Convert JSON Schema type to Python type.

    Args:
        schema: JSON Schema property definition.

    Returns:
        Corresponding Python type.
    """
    json_type = schema.get("type", "string")

    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    return type_mapping.get(json_type, str)


def _sanitize_name(name: str) -> str:
    """Sanitize a name for use in tool names.

    Args:
        name: The name to sanitize.

    Returns:
        Sanitized name (lowercase, underscores instead of spaces/hyphens).
    """
    return name.replace(" ", "_").replace("-", "_").lower()


def _build_agent_description(card: AgentCard) -> str:
    """Build a tool description from agent card and its skills.

    Args:
        card: The agent card containing agent info and skills.

    Returns:
        Formatted description with agent description and capabilities.
    """
    lines = [card.description]

    if card.skills:
        lines.append("")
        lines.append("Capabilities:")
        for skill in card.skills:
            lines.append(f"- {skill.name}: {skill.description}")

    return "\n".join(lines)


def create_a2a_tool(
    config: A2AToolConfig,
    agent_card: AgentCard | None = None,
) -> StructuredTool:
    """Create a LangGraph-compatible tool from an A2A agent skill.

    Tool naming follows this pattern:
    - If name_override is set: use it directly (no prefix applied)
    - Otherwise: a2a_<prefix>_<skill_name>
      - prefix: config.tool_prefix or derived from agent card name
      - skill_name: from skill or "agent" as fallback

    Args:
        config: Tool configuration.
        agent_card: Optional pre-fetched agent card.

    Returns:
        A StructuredTool that calls the A2A agent.
    """
    skill: AgentSkill | None = None
    card = agent_card

    if card and card.skills:
        if config.skill_id:
            for s in card.skills:
                if s.id == config.skill_id:
                    skill = s
                    break
        else:
            skill = card.skills[0]

    # Determine tool name
    if config.name_override:
        # Use override directly (no prefix)
        tool_name = _sanitize_name(config.name_override)
    else:
        # Build prefixed name: a2a_<prefix>_<skill_name>
        prefix = config.tool_prefix
        if not prefix and card:
            # Derive prefix from agent card name
            prefix = _sanitize_name(card.name)
        prefix = prefix or "remote"

        skill_name = _sanitize_name(skill.name) if skill else "agent"
        tool_name = f"a2a_{prefix}_{skill_name}"

    tool_description = config.description_override or (
        skill.description if skill else "Send a message to the A2A agent"
    )

    # Extract input schema from skill's input_modes if available
    # input_modes can contain various types (strings, dicts, etc.) per A2A spec
    # We only use dict schemas; other types (like MIME type strings) fall back to default
    input_schema: dict[str, Any] | None = None
    if skill and skill.input_modes:
        first_mode = skill.input_modes[0]
        if isinstance(first_mode, dict):
            input_schema = first_mode

    args_schema = _json_schema_to_pydantic_model(
        f"{tool_name.title().replace('_', '')}Args",
        input_schema,
    )

    async def tool_func(**kwargs: Any) -> str:
        """Execute the A2A agent tool."""
        if "query" in kwargs:
            message_text = kwargs["query"]
        else:
            message_text = " ".join(f"{k}={v}" for k, v in kwargs.items())

        client = A2AClientWrapper(
            base_url=config.base_url,
            config=config.client_config,
            auth=config.auth,
        )

        async with client:
            result = await client.send_text(message_text)
            return result.response_text

    return StructuredTool(
        name=tool_name,
        description=tool_description,
        coroutine=tool_func,
        args_schema=args_schema,
    )


async def create_tool_from_agent_card(
    base_url: str,
    config: A2AClientConfig | None = None,
    auth: AuthConfig | None = None,
    name_override: str | None = None,
    description_override: str | None = None,
) -> StructuredTool:
    """Create a single tool from an agent card.

    Creates one tool per agent with a description that concatenates
    the agent description and all skill capabilities.

    Args:
        base_url: Base URL of the A2A agent.
        config: Optional client configuration.
        auth: Optional authentication configuration.
        name_override: Optional override for the tool name.
        description_override: Optional override for the tool description.

    Returns:
        A StructuredTool instance for the agent.
    """
    client = A2AClientWrapper(
        base_url=base_url,
        config=config,
        auth=auth,
    )

    async with client:
        agent_card = await client.get_agent_card()

    if name_override:
        tool_name = _sanitize_name(name_override)
    else:
        tool_name = f"a2a_{_sanitize_name(agent_card.name)}"

    tool_description = description_override or _build_agent_description(agent_card)

    args_schema = create_model(
        f"{tool_name.title().replace('_', '')}Args",
        query=(str, Field(description="The task or query to send to the agent")),
    )

    async def tool_func(query: str) -> str:
        """Execute the A2A agent tool."""
        async with A2AClientWrapper(
            base_url=base_url,
            config=config,
            auth=auth,
        ) as tool_client:
            result = await tool_client.send_text(query)
            return result.response_text

    return StructuredTool(
        name=tool_name,
        description=tool_description,
        coroutine=tool_func,
        args_schema=args_schema,
    )
