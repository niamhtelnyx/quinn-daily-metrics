"""Unit tests for A2A client message construction."""

import pytest
from a2a.types import DataPart, Message, Role, TextPart

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.messages import (
    MessageBuilder,
    create_data_message,
    create_text_message,
)


class TestMessageBuilder:
    """Tests for MessageBuilder class."""

    def test_add_text_creates_text_part(self):
        """add_text adds a TextPart to the message."""
        builder = MessageBuilder()
        builder.add_text("Hello, world!")
        message = builder.build()
        assert len(message.parts) == 1
        assert isinstance(message.parts[0].root, TextPart)
        assert message.parts[0].root.text == "Hello, world!"

    def test_add_text_with_metadata(self):
        """add_text accepts optional metadata."""
        builder = MessageBuilder()
        builder.add_text("Test", metadata={"key": "value"})
        message = builder.build()
        assert message.parts[0].root.metadata == {"key": "value"}

    def test_add_data_creates_data_part(self):
        """add_data adds a DataPart to the message."""
        builder = MessageBuilder()
        builder.add_data({"query": "test", "limit": 10})
        message = builder.build()
        assert len(message.parts) == 1
        assert isinstance(message.parts[0].root, DataPart)
        assert message.parts[0].root.data == {"query": "test", "limit": 10}

    def test_add_data_with_metadata(self):
        """add_data accepts optional metadata."""
        builder = MessageBuilder()
        builder.add_data({"data": "test"}, metadata={"source": "test"})
        message = builder.build()
        assert message.parts[0].root.metadata == {"source": "test"}

    def test_multiple_parts(self):
        """Builder can add multiple parts."""
        builder = MessageBuilder()
        builder.add_text("Question:")
        builder.add_data({"params": [1, 2, 3]})
        builder.add_text("End")
        message = builder.build()
        assert len(message.parts) == 3

    def test_with_task_id(self):
        """with_task_id sets task ID on message."""
        builder = MessageBuilder()
        builder.add_text("Continue").with_task_id("task-123")
        message = builder.build()
        assert message.task_id == "task-123"

    def test_with_context_id(self):
        """with_context_id sets context ID on message."""
        builder = MessageBuilder()
        builder.add_text("Test").with_context_id("ctx-456")
        message = builder.build()
        assert message.context_id == "ctx-456"

    def test_with_metadata(self):
        """with_metadata sets message-level metadata."""
        builder = MessageBuilder()
        builder.add_text("Test").with_metadata({"source": "test"})
        message = builder.build()
        assert message.metadata == {"source": "test"}

    def test_with_reference_tasks(self):
        """with_reference_tasks sets reference task IDs."""
        builder = MessageBuilder()
        builder.add_text("Test").with_reference_tasks(["task-1", "task-2"])
        message = builder.build()
        assert message.reference_task_ids == ["task-1", "task-2"]

    def test_build_returns_message(self):
        """build() returns a Message object."""
        builder = MessageBuilder()
        builder.add_text("Test message")
        message = builder.build()
        assert isinstance(message, Message)

    def test_build_sets_user_role(self):
        """build() sets role to user."""
        builder = MessageBuilder()
        builder.add_text("Test")
        message = builder.build()
        assert message.role == Role.user

    def test_build_generates_message_id(self):
        """build() generates a unique message ID."""
        builder1 = MessageBuilder()
        builder1.add_text("Test 1")
        message1 = builder1.build()

        builder2 = MessageBuilder()
        builder2.add_text("Test 2")
        message2 = builder2.build()

        assert message1.message_id is not None
        assert message2.message_id is not None
        assert message1.message_id != message2.message_id

    def test_build_empty_raises_error(self):
        """build() raises error when no parts added."""
        builder = MessageBuilder()
        with pytest.raises(ValueError, match="must have at least one part"):
            builder.build()

    def test_method_chaining(self):
        """Builder methods return self for chaining."""
        message = (
            MessageBuilder()
            .add_text("Hello")
            .add_data({"key": "value"})
            .with_task_id("task-123")
            .with_context_id("ctx-456")
            .with_metadata({"source": "test"})
            .build()
        )
        assert len(message.parts) == 2
        assert message.task_id == "task-123"
        assert message.context_id == "ctx-456"


class TestCreateTextMessage:
    """Tests for create_text_message function."""

    def test_creates_simple_message(self):
        """create_text_message creates a basic text message."""
        message = create_text_message("Hello, agent!")
        assert isinstance(message, Message)
        assert len(message.parts) == 1
        assert isinstance(message.parts[0].root, TextPart)
        assert message.parts[0].root.text == "Hello, agent!"

    def test_with_task_id(self):
        """create_text_message accepts task_id."""
        message = create_text_message("Continue", task_id="task-789")
        assert message.task_id == "task-789"

    def test_with_context_id(self):
        """create_text_message accepts context_id."""
        message = create_text_message("Test", context_id="ctx-abc")
        assert message.context_id == "ctx-abc"

    def test_with_both_ids(self):
        """create_text_message accepts both IDs."""
        message = create_text_message(
            "Continue conversation",
            task_id="task-123",
            context_id="ctx-456",
        )
        assert message.task_id == "task-123"
        assert message.context_id == "ctx-456"


class TestCreateDataMessage:
    """Tests for create_data_message function."""

    def test_creates_data_message(self):
        """create_data_message creates a data message."""
        data = {"query": "test", "filters": {"active": True}}
        message = create_data_message(data)
        assert isinstance(message, Message)
        assert len(message.parts) == 1
        assert isinstance(message.parts[0].root, DataPart)
        assert message.parts[0].root.data == data

    def test_with_task_id(self):
        """create_data_message accepts task_id."""
        message = create_data_message({"key": "value"}, task_id="task-xyz")
        assert message.task_id == "task-xyz"

    def test_with_context_id(self):
        """create_data_message accepts context_id."""
        message = create_data_message({"key": "value"}, context_id="ctx-xyz")
        assert message.context_id == "ctx-xyz"
