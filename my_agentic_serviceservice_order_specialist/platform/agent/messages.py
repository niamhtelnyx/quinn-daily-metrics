"""Framework-agnostic message and result types.

These types are used across all implementations and define the common
vocabulary for agent execution.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Message:
    """Framework-agnostic message representation.

    Attributes:
        role: Message role ("system", "user", "assistant", "tool")
        content: Message text content
        tool_calls: List of tool call dicts (for assistant messages)
        tool_call_id: ID of the tool call this message responds to (for tool messages)
        name: Tool name (for tool messages)
    """

    role: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class ExecutionResult:
    """Result of agent execution.

    Attributes:
        response: Final assistant response text
        messages: Full conversation history as framework-agnostic Messages
        reasoning_steps: Number of reasoning iterations performed
        thread_id: Conversation thread identifier
        metadata: Additional framework-specific metadata
    """

    response: str
    messages: list[Message]
    reasoning_steps: int
    thread_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StreamEvent:
    """Streaming execution event.

    Attributes:
        event_type: Type of event ("message", "tool_call", "tool_result", "done", "error")
        data: Event-specific data payload
    """

    event_type: str
    data: dict[str, Any]
