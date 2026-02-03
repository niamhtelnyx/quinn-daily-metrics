"""Unit tests for synchronous execution strategy."""

from unittest.mock import AsyncMock, Mock

import pytest
from a2a.types import (
    Artifact,
    Message,
    Part,
    Role,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import (
    A2AInputRequiredError,
    A2ATaskCanceledError,
    A2ATaskFailedError,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.sync import SyncStrategy


class TestSyncStrategyInit:
    """Tests for SyncStrategy initialization."""

    def test_init_stores_client(self):
        """SyncStrategy stores the client reference."""
        mock_client = Mock()
        strategy = SyncStrategy(mock_client)
        assert strategy._client is mock_client


class TestSyncStrategyExecute:
    """Tests for SyncStrategy.execute()."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock A2A client."""
        return AsyncMock()

    @pytest.fixture
    def sample_message(self):
        """Create a sample message."""
        return Message(
            role=Role.user,
            message_id="msg-123",
            parts=[Part(root=TextPart(text="Hello"))],
        )

    @pytest.fixture
    def completed_task(self):
        """Create a completed task."""
        return Task(
            id="task-123",
            context_id="ctx-456",
            status=TaskStatus(state=TaskState.completed),
            artifacts=[
                Artifact(
                    artifact_id="art-1",
                    parts=[Part(root=TextPart(text="Agent response"))],
                ),
            ],
        )

    async def test_execute_returns_result_on_success(
        self, mock_client, sample_message, completed_task
    ):
        """execute() returns ExecutionResult on success."""

        async def mock_send(msg):
            yield (completed_task, None)

        mock_client.send_message = mock_send
        strategy = SyncStrategy(mock_client)

        result = await strategy.execute(sample_message)

        assert result.task_id == "task-123"
        assert result.context_id == "ctx-456"
        assert result.state == TaskState.completed
        assert result.response_text == "Agent response"

    async def test_execute_aggregates_multiple_events(self, mock_client, sample_message):
        """execute() aggregates events and uses final task."""
        task1 = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.working),
        )
        task2 = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
            artifacts=[
                Artifact(
                    artifact_id="art-1",
                    parts=[Part(root=TextPart(text="Final response"))],
                ),
            ],
        )

        async def mock_send(msg):
            yield (task1, None)
            yield (task2, None)

        mock_client.send_message = mock_send
        strategy = SyncStrategy(mock_client)

        result = await strategy.execute(sample_message)

        assert result.state == TaskState.completed
        assert result.response_text == "Final response"

    async def test_execute_raises_on_unexpected_message(self, mock_client, sample_message):
        """execute() raises error on unexpected Message response."""
        response_message = Message(
            role=Role.agent,
            message_id="msg-resp",
            parts=[Part(root=TextPart(text="Unexpected"))],
        )

        async def mock_send(msg):
            yield response_message

        mock_client.send_message = mock_send
        strategy = SyncStrategy(mock_client)

        with pytest.raises(A2ATaskFailedError, match="unexpected Message"):
            await strategy.execute(sample_message)

    async def test_execute_raises_when_no_task_received(self, mock_client, sample_message):
        """execute() raises error when no task is received."""

        async def mock_send(msg):
            # Empty async generator
            if False:
                yield

        mock_client.send_message = mock_send
        strategy = SyncStrategy(mock_client)

        with pytest.raises(A2ATaskFailedError, match="No task received"):
            await strategy.execute(sample_message)


class TestSyncStrategyProcessFinalTask:
    """Tests for SyncStrategy._process_final_task()."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock A2A client."""
        return Mock()

    @pytest.fixture
    def sample_message(self):
        """Create a sample message."""
        return Message(
            role=Role.user,
            message_id="msg-123",
            parts=[Part(root=TextPart(text="Hello"))],
        )

    def test_raises_on_failed_state(self, mock_client, sample_message):
        """_process_final_task raises A2ATaskFailedError for failed task."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(
                state=TaskState.failed,
                message=Message(
                    role=Role.agent,
                    message_id="msg-err",
                    parts=[Part(root=TextPart(text="Something went wrong"))],
                ),
            ),
        )
        strategy = SyncStrategy(mock_client)

        with pytest.raises(A2ATaskFailedError) as exc_info:
            strategy._process_final_task(task, sample_message)

        assert "Something went wrong" in str(exc_info.value)

    def test_raises_on_canceled_state(self, mock_client, sample_message):
        """_process_final_task raises A2ATaskCanceledError for canceled task."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.canceled),
        )
        strategy = SyncStrategy(mock_client)

        with pytest.raises(A2ATaskCanceledError) as exc_info:
            strategy._process_final_task(task, sample_message)

        assert exc_info.value.task_id == "task-123"

    def test_raises_on_input_required_state(self, mock_client, sample_message):
        """_process_final_task raises A2AInputRequiredError for input_required."""
        task = Task(
            id="task-123",
            context_id="ctx-456",
            status=TaskStatus(
                state=TaskState.input_required,
                message=Message(
                    role=Role.agent,
                    message_id="msg-q",
                    parts=[Part(root=TextPart(text="What currency?"))],
                ),
            ),
        )
        strategy = SyncStrategy(mock_client)

        with pytest.raises(A2AInputRequiredError) as exc_info:
            strategy._process_final_task(task, sample_message)

        assert exc_info.value.task_id == "task-123"
        assert exc_info.value.context_id == "ctx-456"
        assert exc_info.value.agent_question == "What currency?"

    def test_raises_when_no_status(self, mock_client, sample_message):
        """_process_final_task raises error when task has no status."""
        # Use a Mock since SDK Task doesn't allow status=None
        task = Mock(spec=Task)
        task.status = None
        task.id = "task-123"
        strategy = SyncStrategy(mock_client)

        with pytest.raises(A2ATaskFailedError, match="no status"):
            strategy._process_final_task(task, sample_message)

    def test_returns_result_for_completed_state(self, mock_client, sample_message):
        """_process_final_task returns ExecutionResult for completed task."""
        task = Task(
            id="task-123",
            context_id="ctx-456",
            status=TaskStatus(state=TaskState.completed),
            artifacts=[
                Artifact(
                    artifact_id="art-1",
                    parts=[Part(root=TextPart(text="Response"))],
                ),
            ],
        )
        strategy = SyncStrategy(mock_client)

        result = strategy._process_final_task(task, sample_message)

        assert result.task_id == "task-123"
        assert result.response_text == "Response"
        assert result.state == TaskState.completed

    def test_failed_state_extracts_error_from_message(self, mock_client, sample_message):
        """_process_final_task extracts error message from status.message."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(
                state=TaskState.failed,
                message=Message(
                    role=Role.agent,
                    message_id="msg-err",
                    parts=[Part(root=TextPart(text="Custom error message"))],
                ),
            ),
        )
        strategy = SyncStrategy(mock_client)

        with pytest.raises(A2ATaskFailedError) as exc_info:
            strategy._process_final_task(task, sample_message)

        assert "Custom error message" in str(exc_info.value)
