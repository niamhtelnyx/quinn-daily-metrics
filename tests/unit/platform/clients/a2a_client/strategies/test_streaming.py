"""Unit tests for streaming execution strategy."""

from unittest.mock import AsyncMock, Mock

import pytest
from a2a.types import (
    Artifact,
    Message,
    Part,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import (
    A2AInputRequiredError,
    A2ATaskCanceledError,
    A2ATaskFailedError,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.streaming import StreamingStrategy


class TestStreamingStrategyInit:
    """Tests for StreamingStrategy initialization."""

    def test_init_stores_client(self):
        """StreamingStrategy stores the client reference."""
        mock_client = Mock()
        strategy = StreamingStrategy(mock_client)
        assert strategy._client is mock_client


class TestStreamingStrategyExecuteStream:
    """Tests for StreamingStrategy.execute_stream()."""

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

    async def test_execute_stream_yields_status_updates(self, mock_client, sample_message):
        """execute_stream yields StreamEvent for status updates."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.working),
        )
        status_update = TaskStatusUpdateEvent(
            task_id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.working),
            final=False,
        )

        async def mock_send(msg):
            yield (task, status_update)

        mock_client.send_message = mock_send
        strategy = StreamingStrategy(mock_client)

        events = []
        async for event in strategy.execute_stream(sample_message):
            events.append(event)

        assert len(events) == 1
        assert events[0].event_type == "status_update"
        assert events[0].task is task
        assert events[0].is_final is False

    async def test_execute_stream_yields_artifact_updates(self, mock_client, sample_message):
        """execute_stream yields StreamEvent with text chunk for artifact updates."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.working),
        )
        artifact = Artifact(
            artifact_id="art-1",
            parts=[Part(root=TextPart(text="Partial response..."))],
        )
        artifact_update = TaskArtifactUpdateEvent(
            task_id="task-123",
            context_id="ctx-1",
            artifact=artifact,
            last_chunk=False,
        )

        async def mock_send(msg):
            yield (task, artifact_update)

        mock_client.send_message = mock_send
        strategy = StreamingStrategy(mock_client)

        events = []
        async for event in strategy.execute_stream(sample_message):
            events.append(event)

        assert len(events) == 1
        assert events[0].event_type == "artifact_update"
        assert events[0].text_chunk == "Partial response..."
        assert events[0].is_final is False

    async def test_execute_stream_handles_final_event(self, mock_client, sample_message):
        """execute_stream sets is_final for final events."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
        )
        status_update = TaskStatusUpdateEvent(
            task_id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
            final=True,
        )

        async def mock_send(msg):
            yield (task, status_update)

        mock_client.send_message = mock_send
        strategy = StreamingStrategy(mock_client)

        events = []
        async for event in strategy.execute_stream(sample_message):
            events.append(event)

        assert len(events) == 1
        assert events[0].is_final is True

    async def test_execute_stream_handles_multiple_events(self, mock_client, sample_message):
        """execute_stream yields multiple events in sequence."""
        task1 = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.working),
        )
        task2 = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
        )
        status1 = TaskStatusUpdateEvent(
            task_id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.working),
            final=False,
        )
        status2 = TaskStatusUpdateEvent(
            task_id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
            final=True,
        )

        async def mock_send(msg):
            yield (task1, status1)
            yield (task2, status2)

        mock_client.send_message = mock_send
        strategy = StreamingStrategy(mock_client)

        events = []
        async for event in strategy.execute_stream(sample_message):
            events.append(event)

        assert len(events) == 2
        assert events[0].is_final is False
        assert events[1].is_final is True

    async def test_execute_stream_raises_on_unexpected_message(self, mock_client, sample_message):
        """execute_stream raises error on unexpected Message response."""
        response_message = Message(
            role=Role.agent,
            message_id="msg-resp",
            parts=[Part(root=TextPart(text="Unexpected"))],
        )

        async def mock_send(msg):
            yield response_message

        mock_client.send_message = mock_send
        strategy = StreamingStrategy(mock_client)

        with pytest.raises(A2ATaskFailedError, match="unexpected Message"):
            async for _ in strategy.execute_stream(sample_message):
                pass

    async def test_execute_stream_handles_task_without_update_type(
        self, mock_client, sample_message
    ):
        """execute_stream yields generic event when update type is unknown."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.working),
        )

        async def mock_send(msg):
            yield (task, None)

        mock_client.send_message = mock_send
        strategy = StreamingStrategy(mock_client)

        events = []
        async for event in strategy.execute_stream(sample_message):
            events.append(event)

        assert len(events) == 1
        assert events[0].event_type == "task_update"


class TestStreamingStrategyExecute:
    """Tests for StreamingStrategy.execute()."""

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

    async def test_execute_returns_final_result(self, mock_client, sample_message):
        """execute() returns ExecutionResult with final task."""
        task = Task(
            id="task-123",
            context_id="ctx-456",
            status=TaskStatus(state=TaskState.completed),
            artifacts=[
                Artifact(
                    artifact_id="art-1",
                    parts=[Part(root=TextPart(text="Final response"))],
                ),
            ],
        )
        status_update = TaskStatusUpdateEvent(
            task_id="task-123",
            context_id="ctx-456",
            status=TaskStatus(state=TaskState.completed),
            final=True,
        )

        async def mock_send(msg):
            yield (task, status_update)

        mock_client.send_message = mock_send
        strategy = StreamingStrategy(mock_client)

        result = await strategy.execute(sample_message)

        assert result.task_id == "task-123"
        assert result.response_text == "Final response"

    async def test_execute_raises_when_no_task(self, mock_client, sample_message):
        """execute() raises error when no task is received."""

        async def mock_send(msg):
            # Empty async generator
            if False:
                yield

        mock_client.send_message = mock_send
        strategy = StreamingStrategy(mock_client)

        with pytest.raises(A2ATaskFailedError, match="No task received"):
            await strategy.execute(sample_message)


class TestStreamingStrategyValidateFinalState:
    """Tests for StreamingStrategy._validate_final_state()."""

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
        """_validate_final_state raises A2ATaskFailedError for failed task."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(
                state=TaskState.failed,
                message=Message(
                    role=Role.agent,
                    message_id="msg-err",
                    parts=[Part(root=TextPart(text="Stream error"))],
                ),
            ),
        )
        strategy = StreamingStrategy(mock_client)

        with pytest.raises(A2ATaskFailedError) as exc_info:
            strategy._validate_final_state(task, sample_message)

        assert "Stream error" in str(exc_info.value)

    def test_raises_on_canceled_state(self, mock_client, sample_message):
        """_validate_final_state raises A2ATaskCanceledError for canceled task."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.canceled),
        )
        strategy = StreamingStrategy(mock_client)

        with pytest.raises(A2ATaskCanceledError):
            strategy._validate_final_state(task, sample_message)

    def test_raises_on_input_required_state(self, mock_client, sample_message):
        """_validate_final_state raises A2AInputRequiredError for input_required."""
        task = Task(
            id="task-123",
            context_id="ctx-456",
            status=TaskStatus(
                state=TaskState.input_required,
                message=Message(
                    role=Role.agent,
                    message_id="msg-q",
                    parts=[Part(root=TextPart(text="Need more info"))],
                ),
            ),
        )
        strategy = StreamingStrategy(mock_client)

        with pytest.raises(A2AInputRequiredError) as exc_info:
            strategy._validate_final_state(task, sample_message)

        assert exc_info.value.agent_question == "Need more info"

    def test_no_error_on_completed_state(self, mock_client, sample_message):
        """_validate_final_state does not raise for completed task."""
        task = Task(
            id="task-123",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
        )
        strategy = StreamingStrategy(mock_client)

        strategy._validate_final_state(task, sample_message)

    def test_no_error_when_no_status(self, mock_client, sample_message):
        """_validate_final_state handles task without status."""
        # Use a Mock since SDK Task doesn't allow status=None
        task = Mock(spec=Task)
        task.status = None
        strategy = StreamingStrategy(mock_client)

        strategy._validate_final_state(task, sample_message)


class TestStreamingStrategyExtractText:
    """Tests for StreamingStrategy._extract_text_from_artifact_update()."""

    def test_extracts_text_from_artifact(self):
        """_extract_text_from_artifact_update extracts text from TextPart."""
        mock_client = Mock()
        strategy = StreamingStrategy(mock_client)

        artifact = Artifact(
            artifact_id="art-1",
            parts=[Part(root=TextPart(text="Extracted text"))],
        )
        update = TaskArtifactUpdateEvent(
            task_id="task-1",
            context_id="ctx-1",
            artifact=artifact,
        )

        result = strategy._extract_text_from_artifact_update(update)

        assert result == "Extracted text"

    def test_returns_none_when_no_artifact(self):
        """_extract_text_from_artifact_update returns None when no artifact."""
        mock_client = Mock()
        strategy = StreamingStrategy(mock_client)

        # Create a minimal artifact since artifact is required
        empty_artifact = Artifact(artifact_id="empty", parts=[])
        update = TaskArtifactUpdateEvent(
            task_id="task-1",
            context_id="ctx-1",
            artifact=empty_artifact,
        )
        # Manually set to None for this test
        update = Mock()
        update.artifact = None

        result = strategy._extract_text_from_artifact_update(update)

        assert result is None

    def test_returns_none_when_no_text_parts(self):
        """_extract_text_from_artifact_update returns None when no text parts."""
        mock_client = Mock()
        strategy = StreamingStrategy(mock_client)

        artifact = Artifact(artifact_id="art-1", parts=[])
        update = TaskArtifactUpdateEvent(
            task_id="task-1",
            context_id="ctx-1",
            artifact=artifact,
        )

        result = strategy._extract_text_from_artifact_update(update)

        assert result is None
