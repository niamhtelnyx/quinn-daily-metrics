"""Base execution strategy interface.

Defines the protocol and common types for all execution strategies.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from a2a.types import Artifact, Message, Task, TaskState, TextPart


@dataclass
class ExecutionResult:
    """Result of executing a message via A2A.

    Attributes:
        task: The final Task object.
        response_text: Extracted text response from the task.
        artifacts: List of artifacts produced by the task.
        state: Final task state.
        task_id: The task ID for multi-turn conversations.
        context_id: The context ID for grouping.
        metadata: Additional metadata from the response.
    """

    task: Task
    response_text: str
    artifacts: list[Artifact] = field(default_factory=list)
    state: TaskState = TaskState.completed
    task_id: str | None = None
    context_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_task(cls, task: Task) -> "ExecutionResult":
        """Create an ExecutionResult from a Task.

        Args:
            task: The completed Task object.

        Returns:
            ExecutionResult with extracted data.
        """
        response_text = ""
        if task.artifacts:
            for artifact in task.artifacts:
                for part in artifact.parts:
                    if isinstance(part.root, TextPart):
                        response_text += part.root.text

        if not response_text and task.status and task.status.message:
            for part in task.status.message.parts:
                if isinstance(part.root, TextPart):
                    response_text += part.root.text

        return cls(
            task=task,
            response_text=response_text,
            artifacts=task.artifacts or [],
            state=task.status.state if task.status else TaskState.unknown,
            task_id=task.id,
            context_id=task.context_id,
            metadata={},
        )


@dataclass
class StreamEvent:
    """Event emitted during streaming execution.

    Attributes:
        event_type: Type of event (status_update, artifact_update, message).
        task: Current task state.
        text_chunk: Text chunk if this is a content event.
        is_final: Whether this is the final event.
    """

    event_type: str
    task: Task | None = None
    text_chunk: str | None = None
    is_final: bool = False


class ExecutionStrategyProtocol(Protocol):
    """Protocol for execution strategies."""

    async def execute(self, message: Message) -> ExecutionResult:
        """Execute a message and return the result.

        Args:
            message: The message to send.

        Returns:
            ExecutionResult with the response.
        """
        ...


class StreamingStrategyProtocol(Protocol):
    """Protocol for streaming execution strategies."""

    async def execute_stream(self, message: Message) -> AsyncIterator[StreamEvent]:
        """Execute a message and stream results.

        Args:
            message: The message to send.

        Yields:
            StreamEvent objects as they arrive.
        """
        ...
