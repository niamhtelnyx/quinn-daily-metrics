"""A2A protocol adapter that bridges the A2A SDK to the Agent protocol.

This module provides an adapter that implements the a2a-sdk's AgentExecutor
interface, delegating actual agent execution to any implementation of the
Agent protocol (e.g., LangGraphAgent).
"""

import structlog
from a2a.server.agent_execution import AgentExecutor as A2AAgentExecutorProtocol
from a2a.server.agent_execution import RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import TaskStore, TaskUpdater
from a2a.types import AgentCard, Part, TaskState, TextPart

from my_agentic_serviceservice_order_specialist.platform.agent.protocol import Agent

logger = structlog.get_logger(__name__)


class A2AAgentAdapter(A2AAgentExecutorProtocol):
    """Adapter that bridges the A2A protocol to the framework-agnostic Agent protocol.

    This adapter:
    - Implements the a2a-sdk AgentExecutor interface
    - Delegates to any Agent protocol implementation (e.g., LangGraphAgent)
    - Handles A2A-specific concerns (task lifecycle, event streaming)

    The underlying agent remains pure and protocol-agnostic.

    Example:
        # Build agent using the builder pattern
        agent = await LangGraphReactAgentBuilder.default_builder(
            llm_base_url="http://localhost:8000",
            llm_api_key="key",
            checkpointer=checkpointer,
        ).build()

        # Wrap in A2A adapter
        a2a_adapter = A2AAgentAdapter(agent)

        # Use with A2A SDK
        a2a_app = A2AStarletteApplication(agent_card, request_handler)
    """

    def __init__(self, agent: Agent) -> None:
        """Initialize the adapter with an Agent instance.

        Args:
            agent: A configured Agent protocol implementation to delegate execution to.
        """
        self._agent = agent

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute agent logic for an A2A request.

        Args:
            context: The request context containing the message, task ID, etc.
            event_queue: The queue to publish events to.
        """
        task_id = context.task_id
        context_id = context.context_id

        if not task_id or not context_id:
            logger.error("missing_a2a_context")
            return

        # Bind A2A context to logs for this execution
        structlog.contextvars.bind_contextvars(
            a2a_task_id=task_id,
            a2a_context_id=context_id,
        )

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task_id,
            context_id=context_id,
        )

        await updater.update_status(TaskState.working)

        try:
            # Extract user input from the message
            user_input = context.get_user_input()
            if not user_input:
                logger.error("no_user_input")
                error_message = updater.new_agent_message(
                    parts=[Part(root=TextPart(kind="text", text="No user input provided"))]
                )
                await updater.failed(error_message)
                return

            # Delegate to the Agent
            result = await self._agent.run(
                message=user_input,
                thread_id=context_id,
            )

            final_response = result.response

            parts: list[Part] = [Part(root=TextPart(kind="text", text=final_response))]
            await updater.add_artifact(
                parts=parts,
                name="response",
                last_chunk=True,
            )
            await updater.complete()

        except Exception as e:
            logger.exception("task_failed", error=str(e))
            # Return error details to client per MCP best practices
            error_message = updater.new_agent_message(
                parts=[Part(root=TextPart(kind="text", text=f"Task failed: {e!s}"))]
            )
            await updater.failed(error_message)

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle task cancellation request.

        Args:
            context: The request context containing the task ID to cancel.
            event_queue: The queue to publish the cancellation status update to.
        """
        task_id = context.task_id
        context_id = context.context_id

        if not task_id or not context_id:
            return

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task_id,
            context_id=context_id,
        )

        await updater.update_status(TaskState.canceled)


async def create_a2a_application(
    agent: Agent,
    agent_card: AgentCard,
    task_store: TaskStore,
) -> A2AStarletteApplication:
    """Create and configure the A2A SDK application.

    Args:
        agent: Pre-configured Agent instance.
        agent_card: AgentCard instance to use for the application.
        task_store: TaskStore instance to reuse.

    Returns:
        Configured A2AStarletteApplication instance
    """
    agent_adapter = A2AAgentAdapter(agent)

    request_handler = DefaultRequestHandler(
        agent_executor=agent_adapter,
        task_store=task_store,
    )

    return A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
