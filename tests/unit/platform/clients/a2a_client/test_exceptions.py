"""Unit tests for A2A client exceptions."""

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import (
    A2AAuthenticationError,
    A2AClientError,
    A2AConnectionError,
    A2AInputRequiredError,
    A2AMaxTurnsExceededError,
    A2AProtocolError,
    A2ATaskCanceledError,
    A2ATaskError,
    A2ATaskFailedError,
    A2ATaskNotFoundError,
    A2ATimeoutError,
)


class TestA2AClientError:
    """Tests for A2AClientError base exception."""

    def test_is_base_exception(self):
        """A2AClientError is the base for all A2A client errors."""
        error = A2AClientError("test error")
        assert isinstance(error, Exception)

    def test_stores_message(self):
        """Error stores the provided message."""
        error = A2AClientError("test error message")
        assert str(error) == "test error message"


class TestA2AConnectionError:
    """Tests for A2AConnectionError."""

    def test_inherits_from_base(self):
        """A2AConnectionError inherits from A2AClientError."""
        error = A2AConnectionError("connection failed")
        assert isinstance(error, A2AClientError)

    def test_message_without_url(self):
        """Error message formats without URL."""
        error = A2AConnectionError("timeout")
        assert "Connection failed" in str(error)
        assert "timeout" in str(error)

    def test_message_with_url(self):
        """Error message includes URL when provided."""
        error = A2AConnectionError("timeout", url="http://example.com")
        assert "http://example.com" in str(error)
        assert error.url == "http://example.com"


class TestA2ATimeoutError:
    """Tests for A2ATimeoutError."""

    def test_inherits_from_base(self):
        """A2ATimeoutError inherits from A2AClientError."""
        error = A2ATimeoutError("operation timed out")
        assert isinstance(error, A2AClientError)

    def test_message_without_timeout(self):
        """Error message formats without timeout."""
        error = A2ATimeoutError("request failed")
        assert "timed out" in str(error)

    def test_message_with_timeout(self):
        """Error message includes timeout when provided."""
        error = A2ATimeoutError("request failed", timeout_seconds=30.0)
        assert "30" in str(error)
        assert error.timeout_seconds == 30.0


class TestA2AAuthenticationError:
    """Tests for A2AAuthenticationError."""

    def test_inherits_from_base(self):
        """A2AAuthenticationError inherits from A2AClientError."""
        error = A2AAuthenticationError("invalid token")
        assert isinstance(error, A2AClientError)

    def test_stores_status_code(self):
        """Error stores the HTTP status code."""
        error = A2AAuthenticationError("unauthorized", status_code=401)
        assert error.status_code == 401


class TestA2AProtocolError:
    """Tests for A2AProtocolError."""

    def test_inherits_from_base(self):
        """A2AProtocolError inherits from A2AClientError."""
        error = A2AProtocolError("invalid response")
        assert isinstance(error, A2AClientError)

    def test_message_with_error_code(self):
        """Error message includes error code when provided."""
        error = A2AProtocolError("parse error", error_code=-32700)
        assert "-32700" in str(error)
        assert error.error_code == -32700


class TestA2ATaskError:
    """Tests for A2ATaskError base class."""

    def test_inherits_from_base(self):
        """A2ATaskError inherits from A2AClientError."""
        error = A2ATaskError("task failed")
        assert isinstance(error, A2AClientError)

    def test_message_with_task_id(self):
        """Error message includes task ID when provided."""
        error = A2ATaskError("processing failed", task_id="task-123")
        assert "task-123" in str(error)
        assert error.task_id == "task-123"


class TestA2ATaskNotFoundError:
    """Tests for A2ATaskNotFoundError."""

    def test_inherits_from_task_error(self):
        """A2ATaskNotFoundError inherits from A2ATaskError."""
        error = A2ATaskNotFoundError("task-456")
        assert isinstance(error, A2ATaskError)

    def test_includes_task_id_in_message(self):
        """Error message includes the task ID."""
        error = A2ATaskNotFoundError("task-456")
        assert "task-456" in str(error)
        assert error.task_id == "task-456"


class TestA2ATaskFailedError:
    """Tests for A2ATaskFailedError."""

    def test_inherits_from_task_error(self):
        """A2ATaskFailedError inherits from A2ATaskError."""
        error = A2ATaskFailedError("execution error")
        assert isinstance(error, A2ATaskError)

    def test_message_format(self):
        """Error message includes failure reason."""
        error = A2ATaskFailedError("out of memory", task_id="task-789")
        assert "out of memory" in str(error)
        assert "task-789" in str(error)


class TestA2ATaskCanceledError:
    """Tests for A2ATaskCanceledError."""

    def test_inherits_from_task_error(self):
        """A2ATaskCanceledError inherits from A2ATaskError."""
        error = A2ATaskCanceledError("task-abc")
        assert isinstance(error, A2ATaskError)

    def test_includes_task_id(self):
        """Error includes the canceled task ID."""
        error = A2ATaskCanceledError("task-abc")
        assert "task-abc" in str(error)
        assert error.task_id == "task-abc"


class TestA2AInputRequiredError:
    """Tests for A2AInputRequiredError."""

    def test_inherits_from_base(self):
        """A2AInputRequiredError inherits from A2AClientError."""
        error = A2AInputRequiredError("What currency?", task_id="task-xyz")
        assert isinstance(error, A2AClientError)

    def test_stores_agent_question(self):
        """Error stores the agent's question."""
        error = A2AInputRequiredError(
            "What currency should I convert to?",
            task_id="task-xyz",
            context_id="ctx-123",
        )
        assert error.agent_question == "What currency should I convert to?"
        assert error.task_id == "task-xyz"
        assert error.context_id == "ctx-123"


class TestA2AMaxTurnsExceededError:
    """Tests for A2AMaxTurnsExceededError."""

    def test_inherits_from_base(self):
        """A2AMaxTurnsExceededError inherits from A2AClientError."""
        error = A2AMaxTurnsExceededError(max_turns=10)
        assert isinstance(error, A2AClientError)

    def test_stores_max_turns(self):
        """Error stores the max turns value."""
        error = A2AMaxTurnsExceededError(max_turns=5, task_id="task-limit")
        assert error.max_turns == 5
        assert error.task_id == "task-limit"
        assert "5" in str(error)
