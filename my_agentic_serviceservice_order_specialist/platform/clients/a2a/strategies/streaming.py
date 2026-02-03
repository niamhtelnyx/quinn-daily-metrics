"""Streaming execution strategy.

Sends a message and yields events as they arrive via SSE.
"""

from collections.abc import AsyncIterator

from a2a.client.client import Client
from a2a.types import (
    Message,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
)

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import (
    A2AInputRequiredError,
    A2ATaskCanceledError,
    A2ATaskFailedError,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.base import ExecutionResult, StreamEvent


class StreamingStrategy:
    """Streaming execution strategy using Server-Sent Events.

    Sends a message and yields events as they arrive in real-time.
    Suitable for long-running tasks where progress updates are desired.
    """

    def __init__(self, client: Client):
        """Initialize the strategy.

        Args:
            client: The A2A client to use for communication.
        """
        self._client = client

    async def execute_stream(self, message: Message) -> AsyncIterator[StreamEvent]:
        """Execute a message with streaming.

        Sends the message and yields events as they arrive.

        Args:
            message: The message to send.

        Yields:
            StreamEvent objects with progress updates.

        Raises:
            A2ATaskFailedError: If the task fails.
            A2ATaskCanceledError: If the task is canceled.
            A2AInputRequiredError: If the agent requires additional input.
        """
        final_task: Task | None = None

        async for event in self._client.send_message(message):
            if isinstance(event, tuple):
                task, update = event
                final_task = task

                if isinstance(update, TaskStatusUpdateEvent):
                    yield StreamEvent(
                        event_type="status_update",
                        task=task,
                        is_final=update.final if update.final else False,
                    )
                elif isinstance(update, TaskArtifactUpdateEvent):
                    text_chunk = self._extract_text_from_artifact_update(update)
                    yield StreamEvent(
                        event_type="artifact_update",
                        task=task,
                        text_chunk=text_chunk,
                        is_final=update.last_chunk if update.last_chunk else False,
                    )
                else:
                    yield StreamEvent(
                        event_type="task_update",
                        task=task,
                    )
            elif isinstance(event, Message):
                raise A2ATaskFailedError(
                    message="Received unexpected Message response during streaming",
                )

        if final_task:
            self._validate_final_state(final_task, message)

    async def execute(self, message: Message) -> ExecutionResult:
        """Execute a message and return the final result.

        Convenience method that consumes the stream and returns
        the final result.

        Args:
            message: The message to send.

        Returns:
            ExecutionResult with the complete response.
        """
        final_task: Task | None = None
        async for event in self.execute_stream(message):
            if event.task:
                final_task = event.task

        if final_task is None:
            raise A2ATaskFailedError(message="No task received from agent")

        return ExecutionResult.from_task(final_task)

    def _extract_text_from_artifact_update(self, update: TaskArtifactUpdateEvent) -> str | None:
        """Extract text content from an artifact update event.

        Args:
            update: The artifact update event.

        Returns:
            Text content if available, None otherwise.
        """
        if update.artifact and update.artifact.parts:
            for part in update.artifact.parts:
                if isinstance(part.root, TextPart):
                    return part.root.text
        return None

    def _validate_final_state(self, task: Task, original_message: Message) -> None:
        """Validate the final task state and raise appropriate exceptions.

        Args:
            task: The final task.
            original_message: The original message sent.

        Raises:
            A2ATaskFailedError: If the task failed.
            A2ATaskCanceledError: If the task was canceled.
            A2AInputRequiredError: If input is required.
        """
        if task.status is None:
            return

        state = task.status.state

        if state == TaskState.failed:
            error_message = "Task execution failed"
            if task.status.message and task.status.message.parts:
                for part in task.status.message.parts:
                    if isinstance(part.root, TextPart):
                        error_message = part.root.text
                        break
            raise A2ATaskFailedError(message=error_message, task_id=task.id)

        if state == TaskState.canceled:
            raise A2ATaskCanceledError(task_id=task.id or "unknown")

        if state == TaskState.input_required:
            question = "Agent requires additional input"
            if task.status.message and task.status.message.parts:
                for part in task.status.message.parts:
                    if isinstance(part.root, TextPart):
                        question = part.root.text
                        break
            raise A2AInputRequiredError(
                message=question,
                task_id=task.id or "unknown",
                context_id=task.context_id,
            )
