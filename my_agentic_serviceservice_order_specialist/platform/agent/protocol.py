"""Agent protocol definitions.

This module defines the framework-agnostic Agent protocol that all agent
implementations must satisfy, enabling interchangeable agent backends.
"""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Protocol

from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentIdentity
from my_agentic_serviceservice_order_specialist.platform.agent.messages import ExecutionResult, StreamEvent


class Agent(Protocol):
    """Protocol for an agent."""

    @property
    def identity(self) -> AgentIdentity:
        """The identity of the agent."""
        ...

    @property
    def name(self) -> str:
        """The name of the agent."""
        ...

    @property
    def description(self) -> str:
        """The description of the agent."""
        ...

    @property
    def slug(self) -> str:
        """The slug of the agent."""
        ...

    async def run(
        self,
        message: str,
        thread_id: str,
        utc_now: datetime | None = None,
    ) -> ExecutionResult:
        """Execute the agent with a user message and return the execution result.

        Args:
            message: User's input message
            thread_id: Thread ID for conversation persistence, if None, a new thread will be created
            utc_now: Optional UTC now time, if None, the current time will be used
        """
        ...

    def run_stream(
        self,
        message: str,
        thread_id: str,
        utc_now: datetime | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Execute the agent with a user message and return the stream of events.

        Args:
            message: User's input message
            thread_id: Thread ID for conversation persistence, if None, a new thread will be created
            utc_now: Optional UTC now time, if None, the current time will be used
        Yields:
            StreamEvent objects containing incremental execution updates
        """
        ...
