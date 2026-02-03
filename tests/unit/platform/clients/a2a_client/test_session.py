"""Unit tests for A2A client conversation session."""

from unittest.mock import AsyncMock, Mock

import pytest
from a2a.types import TaskState

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.client import A2AClientWrapper
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import A2AClientConfig
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import (
    A2AInputRequiredError,
    A2AMaxTurnsExceededError,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.session import (
    ConversationMessage,
    ConversationSession,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.base import ExecutionResult


class TestConversationMessage:
    """Tests for ConversationMessage dataclass."""

    def test_required_fields(self):
        """ConversationMessage requires role and content."""
        msg = ConversationMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_optional_fields_default(self):
        """ConversationMessage has correct defaults."""
        msg = ConversationMessage(role="agent", content="Hi")
        assert msg.task_id is None
        assert msg.state is None

    def test_full_message(self):
        """ConversationMessage accepts all fields."""
        msg = ConversationMessage(
            role="agent",
            content="Response",
            task_id="task-123",
            state=TaskState.completed,
        )
        assert msg.task_id == "task-123"
        assert msg.state == TaskState.completed


class TestConversationSessionCreate:
    """Tests for ConversationSession creation."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock A2A client."""
        return Mock(spec=A2AClientWrapper)

    def test_create_with_client_only(self, mock_client):
        """create() initializes with defaults."""
        session = ConversationSession.create(mock_client)
        assert session.client is mock_client
        assert session.task_id is None
        assert session.context_id is None
        assert session.max_turns == 10
        assert session.current_turn == 0
        assert len(session.history) == 0

    def test_create_with_context_id(self, mock_client):
        """create() accepts context_id."""
        session = ConversationSession.create(mock_client, context_id="ctx-123")
        assert session.context_id == "ctx-123"

    def test_create_with_config(self, mock_client):
        """create() uses config for max_turns."""
        config = A2AClientConfig(max_conversation_turns=5)
        session = ConversationSession.create(mock_client, config=config)
        assert session.max_turns == 5


class TestConversationSessionProperties:
    """Tests for ConversationSession properties."""

    @pytest.fixture
    def session(self):
        """Create a session with mock client."""
        mock_client = Mock(spec=A2AClientWrapper)
        return ConversationSession.create(mock_client)

    def test_is_complete_false_when_empty(self, session):
        """is_complete is False when no messages."""
        assert session.is_complete is False

    def test_is_complete_true_when_completed(self, session):
        """is_complete is True when last state is completed."""
        session.history.append(
            ConversationMessage(
                role="agent",
                content="Done",
                state=TaskState.completed,
            )
        )
        assert session.is_complete is True

    def test_is_complete_true_when_failed(self, session):
        """is_complete is True when last state is failed."""
        session.history.append(
            ConversationMessage(
                role="agent",
                content="Error",
                state=TaskState.failed,
            )
        )
        assert session.is_complete is True

    def test_is_complete_true_when_canceled(self, session):
        """is_complete is True when last state is canceled."""
        session.history.append(
            ConversationMessage(
                role="agent",
                content="Canceled",
                state=TaskState.canceled,
            )
        )
        assert session.is_complete is True

    def test_is_complete_false_when_working(self, session):
        """is_complete is False when last state is working."""
        session.history.append(
            ConversationMessage(
                role="agent",
                content="Working...",
                state=TaskState.working,
            )
        )
        assert session.is_complete is False

    def test_requires_input_false_initially(self, session):
        """requires_input is False when no pending request."""
        assert session.requires_input is False

    def test_pending_question_none_initially(self, session):
        """pending_question is None when no pending request."""
        assert session.pending_question is None


class TestConversationSessionSend:
    """Tests for ConversationSession.send()."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock A2A client."""
        return AsyncMock(spec=A2AClientWrapper)

    @pytest.fixture
    def sample_result(self):
        """Create a sample ExecutionResult."""
        task = Mock()
        task.id = "task-123"
        task.context_id = "ctx-456"
        task.status = Mock()
        task.status.state = TaskState.completed
        task.artifacts = []

        return ExecutionResult(
            task=task,
            response_text="Agent response",
            task_id="task-123",
            context_id="ctx-456",
            state=TaskState.completed,
            artifacts=[],
        )

    async def test_send_increments_turn(self, mock_client, sample_result):
        """send() increments current_turn."""
        mock_client.send_message = AsyncMock(return_value=sample_result)
        session = ConversationSession.create(mock_client)

        await session.send("Hello")

        assert session.current_turn == 1

    async def test_send_adds_user_message_to_history(self, mock_client, sample_result):
        """send() adds user message to history."""
        mock_client.send_message = AsyncMock(return_value=sample_result)
        session = ConversationSession.create(mock_client)

        await session.send("Hello")

        assert len(session.history) == 2
        assert session.history[0].role == "user"
        assert session.history[0].content == "Hello"

    async def test_send_adds_agent_message_to_history(self, mock_client, sample_result):
        """send() adds agent response to history."""
        mock_client.send_message = AsyncMock(return_value=sample_result)
        session = ConversationSession.create(mock_client)

        await session.send("Hello")

        assert session.history[1].role == "agent"
        assert session.history[1].content == "Agent response"

    async def test_send_updates_task_id(self, mock_client, sample_result):
        """send() updates task_id from result."""
        mock_client.send_message = AsyncMock(return_value=sample_result)
        session = ConversationSession.create(mock_client)

        await session.send("Hello")

        assert session.task_id == "task-123"

    async def test_send_uses_existing_task_id(self, mock_client, sample_result):
        """send() includes existing task_id in message."""
        mock_client.send_message = AsyncMock(return_value=sample_result)
        session = ConversationSession.create(mock_client)
        session.task_id = "existing-task"

        await session.send("Continue")

        call_args = mock_client.send_message.call_args
        message = call_args[0][0]
        assert message.task_id == "existing-task"

    async def test_send_raises_max_turns_exceeded(self, mock_client):
        """send() raises A2AMaxTurnsExceededError when limit reached."""
        session = ConversationSession.create(mock_client)
        session.max_turns = 2
        session.current_turn = 2

        with pytest.raises(A2AMaxTurnsExceededError) as exc_info:
            await session.send("One more")

        assert exc_info.value.max_turns == 2

    async def test_send_handles_input_required(self, mock_client):
        """send() handles input_required state."""
        input_error = A2AInputRequiredError(
            message="What currency?",
            task_id="task-123",
            context_id="ctx-456",
        )
        mock_client.send_message = AsyncMock(side_effect=input_error)
        session = ConversationSession.create(mock_client)

        with pytest.raises(A2AInputRequiredError):
            await session.send("Convert 100 dollars")

        assert session.requires_input is True
        assert session.pending_question == "What currency?"
        assert session.task_id == "task-123"


class TestConversationSessionRespondToInputRequired:
    """Tests for ConversationSession.respond_to_input_required()."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock A2A client."""
        return AsyncMock(spec=A2AClientWrapper)

    async def test_respond_requires_pending_input(self, mock_client):
        """respond_to_input_required() requires pending input."""
        session = ConversationSession.create(mock_client)

        with pytest.raises(ValueError, match="No pending input request"):
            await session.respond_to_input_required("euros")

    async def test_respond_sends_response(self, mock_client):
        """respond_to_input_required() sends the response."""
        result = ExecutionResult(
            task=Mock(),
            response_text="100 USD = 92 EUR",
            task_id="task-123",
            context_id="ctx-456",
            state=TaskState.completed,
            artifacts=[],
        )
        mock_client.send_message = AsyncMock(return_value=result)

        session = ConversationSession.create(mock_client)
        session._pending_input_required = A2AInputRequiredError(
            message="What currency?",
            task_id="task-123",
            context_id="ctx-456",
        )

        response = await session.respond_to_input_required("euros")

        assert response.response_text == "100 USD = 92 EUR"


class TestConversationSessionReset:
    """Tests for ConversationSession.reset()."""

    def test_reset_clears_all_state(self):
        """reset() clears all conversation state."""
        mock_client = Mock(spec=A2AClientWrapper)
        session = ConversationSession.create(mock_client)
        session.task_id = "task-123"
        session.context_id = "ctx-456"
        session.current_turn = 5
        session.history.append(ConversationMessage(role="user", content="Hello"))
        session._pending_input_required = A2AInputRequiredError(
            message="Question?",
            task_id="task-123",
        )

        session.reset()

        assert session.task_id is None  # type: ignore[unnecessary-comparison]
        assert session.context_id is None  # type: ignore[unnecessary-comparison]
        assert session.current_turn == 0
        assert len(session.history) == 0
        assert session._pending_input_required is None


class TestConversationSessionHistory:
    """Tests for ConversationSession.get_history_text()."""

    def test_get_history_text_empty(self):
        """get_history_text() returns empty list when no history."""
        mock_client = Mock(spec=A2AClientWrapper)
        session = ConversationSession.create(mock_client)

        history = session.get_history_text()

        assert history == []

    def test_get_history_text_formats_messages(self):
        """get_history_text() returns formatted messages."""
        mock_client = Mock(spec=A2AClientWrapper)
        session = ConversationSession.create(mock_client)
        session.history.append(ConversationMessage(role="user", content="Hello"))
        session.history.append(ConversationMessage(role="agent", content="Hi there!"))

        history = session.get_history_text()

        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "agent", "content": "Hi there!"}
