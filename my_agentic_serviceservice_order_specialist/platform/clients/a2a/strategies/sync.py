"""Synchronous execution strategy.

Sends a message and waits for the complete response.
"""

from a2a.client.client import Client
from a2a.types import Message, Task, TaskState, TextPart

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import (
    A2AInputRequiredError,
    A2ATaskCanceledError,
    A2ATaskFailedError,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.base import ExecutionResult


class SyncStrategy:
    """Synchronous (blocking) execution strategy.

    Sends a message and collects all events until the task completes.
    Suitable for quick, single-turn interactions.
    """

    def __init__(self, client: Client):
        """Initialize the strategy.

        Args:
            client: The A2A client to use for communication.
        """
        self._client = client

    async def execute(self, message: Message) -> ExecutionResult:
        """Execute a message synchronously.

        Sends the message and waits for the complete response,
        aggregating all events.

        Args:
            message: The message to send.

        Returns:
            ExecutionResult with the complete response.

        Raises:
            A2ATaskFailedError: If the task fails.
            A2ATaskCanceledError: If the task is canceled.
            A2AInputRequiredError: If the agent requires additional input.
        """
        final_task: Task | None = None

        async for event in self._client.send_message(message):
            if isinstance(event, tuple):
                task, _update = event
                final_task = task
            elif isinstance(event, Message):
                raise A2ATaskFailedError(
                    message="Received unexpected Message response",
                )

        if final_task is None:
            raise A2ATaskFailedError(message="No task received from agent")

        return self._process_final_task(final_task, message)

    def _process_final_task(self, task: Task, original_message: Message) -> ExecutionResult:
        """Process the final task and handle terminal states.

        Args:
            task: The final task.
            original_message: The original message sent.

        Returns:
            ExecutionResult if successful.

        Raises:
            A2ATaskFailedError: If the task failed.
            A2ATaskCanceledError: If the task was canceled.
            A2AInputRequiredError: If input is required.
        """
        if task.status is None:
            raise A2ATaskFailedError(
                message="Task has no status",
                task_id=task.id,
            )

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

        return ExecutionResult.from_task(task)
