"""Conversation session management for multi-turn A2A interactions.

This module provides components for managing multi-turn conversations
with A2A agents, including context tracking and input_required handling.
"""

from dataclasses import dataclass, field
from typing import Any

from a2a.types import TaskState

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.client import A2AClientWrapper
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import A2AClientConfig
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.exceptions import (
    A2AInputRequiredError,
    A2AMaxTurnsExceededError,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.messages import create_text_message
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.base import ExecutionResult


@dataclass
class ConversationMessage:
    """A message in a conversation history.

    Attributes:
        role: The role (user or agent).
        content: The message content.
        task_id: The task ID at this point.
        state: The task state after this message.
    """

    role: str
    content: str
    task_id: str | None = None
    state: TaskState | None = None


@dataclass
class ConversationSession:
    """Manages a multi-turn conversation with an A2A agent.

    Tracks task_id and context_id across turns, handles input_required
    states, and enforces turn limits.

    Attributes:
        client: The A2A client wrapper to use.
        task_id: Current task ID (set after first message).
        context_id: Context ID for grouping related tasks.
        history: List of messages in the conversation.
        max_turns: Maximum allowed turns (from config or explicit).
        current_turn: Current turn number.
    """

    client: A2AClientWrapper
    task_id: str | None = None
    context_id: str | None = None
    history: list[ConversationMessage] = field(default_factory=list)
    max_turns: int = 10
    current_turn: int = 0
    _pending_input_required: A2AInputRequiredError | None = field(default=None, repr=False)

    @classmethod
    def create(
        cls,
        client: A2AClientWrapper,
        context_id: str | None = None,
        config: A2AClientConfig | None = None,
    ) -> "ConversationSession":
        """Create a new conversation session.

        Args:
            client: The A2A client wrapper to use.
            context_id: Optional context ID for grouping.
            config: Optional client config for max_turns setting.

        Returns:
            A new ConversationSession instance.
        """
        effective_config = config or A2AClientConfig()
        return cls(
            client=client,
            context_id=context_id,
            max_turns=effective_config.max_conversation_turns,
        )

    @property
    def is_complete(self) -> bool:
        """Check if the conversation is complete."""
        if not self.history:
            return False
        last = self.history[-1]
        return last.state in {TaskState.completed, TaskState.failed, TaskState.canceled}

    @property
    def requires_input(self) -> bool:
        """Check if the agent is waiting for user input."""
        return self._pending_input_required is not None

    @property
    def pending_question(self) -> str | None:
        """Get the pending question from the agent, if any."""
        if self._pending_input_required:
            return self._pending_input_required.agent_question
        return None

    async def send(self, text: str) -> ExecutionResult:
        """Send a message and get a response.

        Handles multi-turn conversation tracking automatically.

        Args:
            text: The text message to send.

        Returns:
            ExecutionResult with the agent's response.

        Raises:
            A2AMaxTurnsExceededError: If max turns is exceeded.
            A2AInputRequiredError: If the agent needs more input.
        """
        if self.current_turn >= self.max_turns:
            raise A2AMaxTurnsExceededError(
                max_turns=self.max_turns,
                task_id=self.task_id,
            )

        self.current_turn += 1

        self.history.append(
            ConversationMessage(
                role="user",
                content=text,
                task_id=self.task_id,
            )
        )

        message = create_text_message(
            text,
            task_id=self.task_id,
            context_id=self.context_id,
        )

        try:
            result = await self.client.send_message(message)
            self._update_from_result(result)
            self._pending_input_required = None
            return result

        except A2AInputRequiredError as e:
            self._pending_input_required = e
            self.task_id = e.task_id
            self.context_id = e.context_id

            self.history.append(
                ConversationMessage(
                    role="agent",
                    content=e.agent_question,
                    task_id=e.task_id,
                    state=TaskState.input_required,
                )
            )
            raise

    async def respond_to_input_required(self, response: str) -> ExecutionResult:
        """Respond to an input_required state.

        Use this when the agent has requested additional input.

        Args:
            response: The user's response to the agent's question.

        Returns:
            ExecutionResult with the agent's response.

        Raises:
            ValueError: If there is no pending input request.
            A2AInputRequiredError: If the agent needs more input.
        """
        if not self._pending_input_required:
            raise ValueError("No pending input request")

        return await self.send(response)

    def _update_from_result(self, result: ExecutionResult) -> None:
        """Update session state from an execution result.

        Args:
            result: The execution result.
        """
        self.task_id = result.task_id
        if result.context_id:
            self.context_id = result.context_id

        self.history.append(
            ConversationMessage(
                role="agent",
                content=result.response_text,
                task_id=result.task_id,
                state=result.state,
            )
        )

    def reset(self) -> None:
        """Reset the session for a new conversation."""
        self.task_id = None
        self.context_id = None
        self.history.clear()
        self.current_turn = 0
        self._pending_input_required = None

    def get_history_text(self) -> list[dict[str, Any]]:
        """Get the conversation history as a list of dicts.

        Returns:
            List of message dicts with role and content.
        """
        return [{"role": msg.role, "content": msg.content} for msg in self.history]
