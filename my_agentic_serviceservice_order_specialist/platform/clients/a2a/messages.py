"""Message construction helpers for A2A protocol.

This module provides helper functions and classes for constructing
A2A protocol messages with proper structure.
"""

from typing import Any
from uuid import uuid4

from a2a.types import DataPart, Message, Part, Role, TextPart


class MessageBuilder:
    """Builder for constructing A2A protocol messages.

    Provides a fluent interface for building messages with various
    content types and metadata.
    """

    def __init__(self) -> None:
        """Initialize an empty message builder."""
        self._parts: list[Part] = []
        self._task_id: str | None = None
        self._context_id: str | None = None
        self._metadata: dict[str, Any] | None = None
        self._reference_task_ids: list[str] | None = None

    def add_text(self, text: str, metadata: dict[str, Any] | None = None) -> "MessageBuilder":
        """Add a text part to the message.

        Args:
            text: The text content to add.
            metadata: Optional metadata for this part.

        Returns:
            Self for method chaining.
        """
        self._parts.append(Part(root=TextPart(text=text, metadata=metadata)))
        return self

    def add_data(
        self,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> "MessageBuilder":
        """Add a structured data part to the message.

        Args:
            data: The structured data to add.
            metadata: Optional metadata for this part.

        Returns:
            Self for method chaining.
        """
        self._parts.append(Part(root=DataPart(data=data, metadata=metadata)))
        return self

    def with_task_id(self, task_id: str) -> "MessageBuilder":
        """Set the task ID for multi-turn conversations.

        Args:
            task_id: The task ID from a previous response.

        Returns:
            Self for method chaining.
        """
        self._task_id = task_id
        return self

    def with_context_id(self, context_id: str) -> "MessageBuilder":
        """Set the context ID for grouping related tasks.

        Args:
            context_id: The context ID for logical grouping.

        Returns:
            Self for method chaining.
        """
        self._context_id = context_id
        return self

    def with_metadata(self, metadata: dict[str, Any]) -> "MessageBuilder":
        """Set message-level metadata.

        Args:
            metadata: Metadata dictionary.

        Returns:
            Self for method chaining.
        """
        self._metadata = metadata
        return self

    def with_reference_tasks(self, task_ids: list[str]) -> "MessageBuilder":
        """Set reference task IDs for additional context.

        Args:
            task_ids: List of task IDs to reference.

        Returns:
            Self for method chaining.
        """
        self._reference_task_ids = task_ids
        return self

    def build(self) -> Message:
        """Build the final Message object.

        Returns:
            A fully constructed Message ready for sending.

        Raises:
            ValueError: If no parts have been added to the message.
        """
        if not self._parts:
            raise ValueError("Message must have at least one part")

        return Message(
            role=Role.user,
            message_id=uuid4().hex,
            parts=self._parts,
            task_id=self._task_id,
            context_id=self._context_id,
            metadata=self._metadata,
            reference_task_ids=self._reference_task_ids,
        )


def create_text_message(
    text: str,
    task_id: str | None = None,
    context_id: str | None = None,
) -> Message:
    """Create a simple text message.

    Convenience function for the most common use case.

    Args:
        text: The text content of the message.
        task_id: Optional task ID for multi-turn conversations.
        context_id: Optional context ID for grouping.

    Returns:
        A Message with a single TextPart.
    """
    builder = MessageBuilder().add_text(text)
    if task_id:
        builder.with_task_id(task_id)
    if context_id:
        builder.with_context_id(context_id)
    return builder.build()


def create_data_message(
    data: dict[str, Any],
    task_id: str | None = None,
    context_id: str | None = None,
) -> Message:
    """Create a structured data message.

    Convenience function for sending structured data.

    Args:
        data: The structured data to send.
        task_id: Optional task ID for multi-turn conversations.
        context_id: Optional context ID for grouping.

    Returns:
        A Message with a single DataPart.
    """
    builder = MessageBuilder().add_data(data)
    if task_id:
        builder.with_task_id(task_id)
    if context_id:
        builder.with_context_id(context_id)
    return builder.build()
