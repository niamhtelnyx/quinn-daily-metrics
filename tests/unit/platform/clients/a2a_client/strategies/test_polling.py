"""Unit tests for polling execution strategy."""

from unittest.mock import AsyncMock, Mock, patch

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

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import A2AClientConfig
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import (
    A2AInputRequiredError,
    A2ATaskCanceledError,
    A2ATaskFailedError,
    A2ATimeoutError,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.polling import PollingStrategy


class TestPollingStrategyInit:
    """Tests for PollingStrategy initialization."""

    def test_init_stores_client(self):
        """PollingStrategy stores the client reference."""
        mock_client = Mock()
        strategy = PollingStrategy(mock_client)
        assert strategy._client is mock_client

    def test_init_uses_default_config(self):
        """PollingStrategy uses default config when not provided."""
        mock_client = Mock()
        strategy = PollingStrategy(mock_client)
        assert strategy._config is not None
        assert strategy._config.poll_interval_seconds == 1.0

    def test_init_accepts_custom_config(self):
        """PollingStrategy accepts custom configuration."""
        mock_client = Mock()
        config = A2AClientConfig(poll_interval_seconds=2.0)
        strategy = PollingStrategy(mock_client, config=config)
        assert strategy._config.poll_interval_seconds == 2.0


class TestPollingStrategyIsTerminalState:
    """Tests for PollingStrategy._is_terminal_state()."""

    @pytest.fixture
    def strategy(self):
        """Create a strategy instance."""
        mock_client = Mock()
        return PollingStrategy(mock_client)

    def test_completed_is_terminal(self, strategy):
        """completed state is terminal."""
        task = Task(
            id="task-1",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
        )
        assert strategy._is_terminal_state(task) is True

    def test_failed_is_terminal(self, strategy):
        """failed state is terminal."""
        task = Task(
            id="task-1",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.failed),
        )
        assert strategy._is_terminal_state(task) is True

    def test_canceled_is_terminal(self, strategy):
        """canceled state is terminal."""
        task = Task(
            id="task-1",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.canceled),
        )
        assert strategy._is_terminal_state(task) is True

    def test_input_required_is_terminal(self, strategy):
        """input_required state is terminal."""
        task = Task(
            id="task-1",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.input_required),
        )
        assert strategy._is_terminal_state(task) is True

    def test_rejected_is_terminal(self, strategy):
        """rejected state is terminal."""
        task = Task(
            id="task-1",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.rejected),
        )
        assert strategy._is_terminal_state(task) is True

    def test_working_is_not_terminal(self, strategy):
        """working state is not terminal."""
        task = Task(
            id="task-1",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.working),
        )
        assert strategy._is_terminal_state(task) is False

    def test_submitted_is_not_terminal(self, strategy):
        """submitted state is not terminal."""
        task = Task(
            id="task-1",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.submitted),
        )
        assert strategy._is_terminal_state(task) is False

    def test_no_status_is_not_terminal(self, strategy):
        """task without status is not terminal."""
        # Use a Mock since SDK Task doesn't allow status=None
        task = Mock(spec=Task)
        task.status = None
        assert strategy._is_terminal_state(task) is False


class TestPollingStrategyProcessFinalTask:
    """Tests for PollingStrategy._process_final_task()."""

    @pytest.fixture
    def strategy(self):
        """Create a strategy instance."""
        mock_client = Mock()
        return PollingStrategy(mock_client)

    def test_returns_result_for_completed(self, strategy):
        """_process_final_task returns ExecutionResult for completed task."""
        task = Task(
            id="task-123",
            context_id="ctx-456",
            status=TaskStatus(state=TaskState.completed),
            artifacts=[
                Artifact(
                    artifact_id="art-1",
                    parts=[Part(root=TextPart(text="Result"))],
                ),
            ],
        )

        result = strategy._process_final_task(task)

        assert result.task_id == "task-123"
        assert result.response_text == "Result"

    def test_raises_on_failed(self, strategy):
        """_process_final_task raises A2ATaskFailedError for failed task."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(
                state=TaskState.failed,
                message=Message(
                    role=Role.agent,
                    message_id="msg-err",
                    parts=[Part(root=TextPart(text="Task failed"))],
                ),
            ),
        )

        with pytest.raises(A2ATaskFailedError) as exc_info:
            strategy._process_final_task(task)

        assert "Task failed" in str(exc_info.value)

    def test_raises_on_canceled(self, strategy):
        """_process_final_task raises A2ATaskCanceledError for canceled task."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.canceled),
        )

        with pytest.raises(A2ATaskCanceledError):
            strategy._process_final_task(task)

    def test_raises_on_rejected(self, strategy):
        """_process_final_task raises A2ATaskFailedError for rejected task."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.rejected),
        )

        with pytest.raises(A2ATaskFailedError, match="rejected"):
            strategy._process_final_task(task)

    def test_raises_on_input_required(self, strategy):
        """_process_final_task raises A2AInputRequiredError for input_required."""
        task = Task(
            id="task-123",
            context_id="ctx-456",
            status=TaskStatus(
                state=TaskState.input_required,
                message=Message(
                    role=Role.agent,
                    message_id="msg-q",
                    parts=[Part(root=TextPart(text="What is X?"))],
                ),
            ),
        )

        with pytest.raises(A2AInputRequiredError) as exc_info:
            strategy._process_final_task(task)

        assert exc_info.value.agent_question == "What is X?"

    def test_raises_when_no_status(self, strategy):
        """_process_final_task raises error when task has no status."""
        # Use a Mock since SDK Task doesn't allow status=None
        task = Mock(spec=Task)
        task.status = None
        task.id = "task-123"

        with pytest.raises(A2ATaskFailedError, match="no status"):
            strategy._process_final_task(task)


class TestPollingStrategyExecute:
    """Tests for PollingStrategy.execute()."""

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

    async def test_execute_returns_immediately_when_complete(self, mock_client, sample_message):
        """execute() returns immediately when initial response is complete."""
        task = Task(
            id="task-123",
            context_id="ctx-456",
            status=TaskStatus(state=TaskState.completed),
            artifacts=[
                Artifact(
                    artifact_id="art-1",
                    parts=[Part(root=TextPart(text="Done"))],
                ),
            ],
        )

        async def mock_send(msg):
            yield (task, None)

        mock_client.send_message = mock_send
        strategy = PollingStrategy(mock_client)

        result = await strategy.execute(sample_message)

        assert result.response_text == "Done"
        mock_client.get_task.assert_not_called()

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
        strategy = PollingStrategy(mock_client)

        with pytest.raises(A2ATaskFailedError, match="unexpected Message"):
            await strategy.execute(sample_message)

    async def test_execute_raises_when_no_task_id(self, mock_client, sample_message):
        """execute() raises error when no task ID is received."""

        async def mock_send(msg):
            # Empty async generator
            if False:
                yield

        mock_client.send_message = mock_send
        strategy = PollingStrategy(mock_client)

        with pytest.raises(A2ATaskFailedError, match="No task ID"):
            await strategy.execute(sample_message)

    async def test_execute_polls_until_complete(self, mock_client, sample_message):
        """execute() polls until task completes."""
        working_task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.working),
        )
        completed_task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
            artifacts=[
                Artifact(
                    artifact_id="art-1",
                    parts=[Part(root=TextPart(text="Polled result"))],
                ),
            ],
        )

        async def mock_send(msg):
            yield (working_task, None)

        mock_client.send_message = mock_send
        mock_client.get_task = AsyncMock(return_value=completed_task)

        config = A2AClientConfig(
            poll_interval_seconds=0.01,
            max_poll_time_seconds=10.0,
        )
        strategy = PollingStrategy(mock_client, config=config)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await strategy.execute(sample_message)

        assert result.response_text == "Polled result"
        mock_client.get_task.assert_called()


class TestPollingStrategyPollUntilComplete:
    """Tests for PollingStrategy._poll_until_complete()."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock A2A client."""
        return AsyncMock()

    async def test_poll_returns_on_completion(self, mock_client):
        """_poll_until_complete returns when task completes."""
        completed_task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
            artifacts=[
                Artifact(
                    artifact_id="art-1",
                    parts=[Part(root=TextPart(text="Done"))],
                ),
            ],
        )
        mock_client.get_task = AsyncMock(return_value=completed_task)

        config = A2AClientConfig(
            poll_interval_seconds=0.01,
            max_poll_time_seconds=10.0,
        )
        strategy = PollingStrategy(mock_client, config=config)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await strategy._poll_until_complete("task-123")

        assert result.response_text == "Done"

    async def test_poll_times_out(self, mock_client):
        """_poll_until_complete raises A2ATimeoutError on timeout."""
        working_task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.working),
        )
        mock_client.get_task = AsyncMock(return_value=working_task)

        config = A2AClientConfig(
            poll_interval_seconds=0.01,
            max_poll_time_seconds=0.001,
        )
        strategy = PollingStrategy(mock_client, config=config)

        with pytest.raises(A2ATimeoutError) as exc_info:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await strategy._poll_until_complete("task-123")

        assert "task-123" in str(exc_info.value)
        assert exc_info.value.timeout_seconds == 0.001

    async def test_poll_uses_exponential_backoff(self, mock_client):
        """_poll_until_complete uses exponential backoff."""
        working_task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.working),
        )
        completed_task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
            artifacts=[],
        )

        call_count = 0

        async def mock_get_task(params):
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                return completed_task
            return working_task

        mock_client.get_task = mock_get_task

        config = A2AClientConfig(
            poll_interval_seconds=0.01,
            poll_backoff_multiplier=2.0,
            poll_max_interval_seconds=10.0,
            max_poll_time_seconds=100.0,
        )
        strategy = PollingStrategy(mock_client, config=config)

        sleep_durations = []

        async def mock_sleep(duration):
            sleep_durations.append(duration)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await strategy._poll_until_complete("task-123")

        assert len(sleep_durations) >= 2
        assert sleep_durations[1] > sleep_durations[0]
