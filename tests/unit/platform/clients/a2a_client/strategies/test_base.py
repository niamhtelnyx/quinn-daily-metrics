"""Unit tests for A2A client strategy base classes."""

from unittest.mock import Mock

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

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.base import ExecutionResult, StreamEvent


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    @pytest.fixture
    def sample_task(self):
        """Create a sample completed Task."""
        return Task(
            id="task-123",
            context_id="ctx-456",
            status=TaskStatus(
                state=TaskState.completed,
                message=Message(
                    role=Role.agent,
                    message_id="msg-1",
                    parts=[Part(root=TextPart(text="Status message"))],
                ),
            ),
            artifacts=[
                Artifact(
                    artifact_id="art-1",
                    parts=[Part(root=TextPart(text="Response text"))],
                ),
            ],
        )

    def test_from_task_extracts_response_text(self, sample_task):
        """from_task extracts text from artifacts."""
        result = ExecutionResult.from_task(sample_task)
        assert result.response_text == "Response text"

    def test_from_task_extracts_task_id(self, sample_task):
        """from_task extracts task ID."""
        result = ExecutionResult.from_task(sample_task)
        assert result.task_id == "task-123"

    def test_from_task_extracts_context_id(self, sample_task):
        """from_task extracts context ID."""
        result = ExecutionResult.from_task(sample_task)
        assert result.context_id == "ctx-456"

    def test_from_task_extracts_state(self, sample_task):
        """from_task extracts task state."""
        result = ExecutionResult.from_task(sample_task)
        assert result.state == TaskState.completed

    def test_from_task_stores_task(self, sample_task):
        """from_task stores the original task."""
        result = ExecutionResult.from_task(sample_task)
        assert result.task is sample_task

    def test_from_task_stores_artifacts(self, sample_task):
        """from_task stores artifacts."""
        result = ExecutionResult.from_task(sample_task)
        assert len(result.artifacts) == 1

    def test_from_task_empty_artifacts(self):
        """from_task handles missing artifacts."""
        task = Task(
            id="task-no-artifacts",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
        )
        result = ExecutionResult.from_task(task)
        assert result.response_text == ""
        assert result.artifacts == []

    def test_from_task_falls_back_to_status_message(self):
        """from_task uses status message when no artifacts."""
        task = Task(
            id="task-status",
            context_id="ctx-1",
            status=TaskStatus(
                state=TaskState.completed,
                message=Message(
                    role=Role.agent,
                    message_id="msg-1",
                    parts=[Part(root=TextPart(text="Status response"))],
                ),
            ),
        )
        result = ExecutionResult.from_task(task)
        assert result.response_text == "Status response"

    def test_from_task_multiple_text_parts(self):
        """from_task concatenates multiple text parts."""
        task = Task(
            id="task-multi",
            context_id="ctx-1",
            status=TaskStatus(state=TaskState.completed),
            artifacts=[
                Artifact(
                    artifact_id="art-1",
                    parts=[
                        Part(root=TextPart(text="Part 1")),
                        Part(root=TextPart(text="Part 2")),
                    ],
                ),
            ],
        )
        result = ExecutionResult.from_task(task)
        assert result.response_text == "Part 1Part 2"


class TestStreamEvent:
    """Tests for StreamEvent dataclass."""

    def test_default_values(self):
        """StreamEvent has correct defaults."""
        event = StreamEvent(event_type="status_update")
        assert event.task is None
        assert event.text_chunk is None
        assert event.is_final is False

    def test_with_task(self):
        """StreamEvent can include task."""
        task = Mock(spec=Task)
        event = StreamEvent(event_type="status_update", task=task)
        assert event.task is task

    def test_with_text_chunk(self):
        """StreamEvent can include text chunk."""
        event = StreamEvent(
            event_type="artifact_update",
            text_chunk="Partial response...",
        )
        assert event.text_chunk == "Partial response..."

    def test_final_event(self):
        """StreamEvent can be marked as final."""
        event = StreamEvent(event_type="status_update", is_final=True)
        assert event.is_final is True
