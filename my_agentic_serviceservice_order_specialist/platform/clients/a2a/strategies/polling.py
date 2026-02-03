"""Polling execution strategy.

Sends a message and polls for completion status.
"""

import asyncio
import time

from a2a.client.client import Client
from a2a.types import Message, Task, TaskQueryParams, TaskState, TextPart

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import A2AClientConfig
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import (
    A2AInputRequiredError,
    A2ATaskCanceledError,
    A2ATaskFailedError,
    A2ATimeoutError,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.base import ExecutionResult


class PollingStrategy:
    """Polling execution strategy.

    Sends a message and polls the task status until completion.
    Suitable for long-running tasks when streaming is not available.
    Uses exponential backoff to reduce server load.
    """

    def __init__(
        self,
        client: Client,
        config: A2AClientConfig | None = None,
    ):
        """Initialize the strategy.

        Args:
            client: The A2A client to use for communication.
            config: Optional client configuration for polling parameters.
        """
        self._client = client
        self._config = config or A2AClientConfig()

    async def execute(self, message: Message) -> ExecutionResult:
        """Execute a message with polling.

        Sends the message, then polls for task completion using
        exponential backoff.

        Args:
            message: The message to send.

        Returns:
            ExecutionResult with the complete response.

        Raises:
            A2ATimeoutError: If polling exceeds max_poll_time.
            A2ATaskFailedError: If the task fails.
            A2ATaskCanceledError: If the task is canceled.
            A2AInputRequiredError: If the agent requires additional input.
        """
        task_id: str | None = None

        async for event in self._client.send_message(message):
            if isinstance(event, tuple):
                task, _update = event
                task_id = task.id
                if self._is_terminal_state(task):
                    return self._process_final_task(task)
            elif isinstance(event, Message):
                raise A2ATaskFailedError(
                    message="Received unexpected Message response",
                )

        if task_id is None:
            raise A2ATaskFailedError(message="No task ID received from agent")

        return await self._poll_until_complete(task_id)

    async def _poll_until_complete(self, task_id: str) -> ExecutionResult:
        """Poll for task completion with exponential backoff.

        Args:
            task_id: The task ID to poll.

        Returns:
            ExecutionResult when task completes.

        Raises:
            A2ATimeoutError: If polling exceeds max_poll_time.
        """
        start_time = time.time()
        interval = self._config.poll_interval_seconds

        while True:
            elapsed = time.time() - start_time
            if elapsed > self._config.max_poll_time_seconds:
                raise A2ATimeoutError(
                    message=f"Polling timed out for task {task_id}",
                    timeout_seconds=self._config.max_poll_time_seconds,
                )

            task = await self._client.get_task(TaskQueryParams(id=task_id))

            if self._is_terminal_state(task):
                return self._process_final_task(task)

            await asyncio.sleep(interval)

            interval = min(
                interval * self._config.poll_backoff_multiplier,
                self._config.poll_max_interval_seconds,
            )

    def _is_terminal_state(self, task: Task) -> bool:
        """Check if the task is in a terminal state.

        Args:
            task: The task to check.

        Returns:
            True if the task is in a terminal state.
        """
        if task.status is None:
            return False

        terminal_states = {
            TaskState.completed,
            TaskState.failed,
            TaskState.canceled,
            TaskState.input_required,
            TaskState.rejected,
        }
        return task.status.state in terminal_states

    def _process_final_task(self, task: Task) -> ExecutionResult:
        """Process the final task and handle terminal states.

        Args:
            task: The final task.

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

        if state == TaskState.rejected:
            raise A2ATaskFailedError(
                message="Task was rejected by the agent",
                task_id=task.id,
            )

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
