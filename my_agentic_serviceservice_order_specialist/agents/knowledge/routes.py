"""Knowledge Agent HTTP endpoints.

This module provides REST API endpoints for invoking the Knowledge agent,
supporting both synchronous and streaming response modes.
"""

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from my_agentic_serviceservice_order_specialist.agents.knowledge.agent import KnowledgeAgentBuilder
from my_agentic_serviceservice_order_specialist.platform.agent.protocol import Agent
from my_agentic_serviceservice_order_specialist.platform.server.dependencies.agents import get_agent

knowledge_router = APIRouter(
    prefix=f"/{KnowledgeAgentBuilder.SLUG}",
    tags=["agents"],
)


class AgentPayload(BaseModel):
    """Request payload for agent invocation endpoints.

    Attributes:
        question: The user's question or task for the agent (1-10000 characters)
        thread_id: Conversation thread ID for persistence (auto-generated if not provided)
    """

    question: str = Field(
        min_length=1,
        max_length=10000,
        description="The user's question or task for the agent",
    )
    thread_id: uuid.UUID = Field(default_factory=uuid.uuid4)


@knowledge_router.post("/invoke")
async def invoke_handler(
    payload: AgentPayload,
    agent: Agent = Depends(get_agent(KnowledgeAgentBuilder)),
):
    """Invoke the knowledge agent synchronously.

    Processes the user's question and returns the complete agent response.

    Args:
        payload: Request containing the question and optional thread_id
        agent: Cached agent instance (injected)

    Returns:
        ExecutionResult with the agent's response and conversation metadata
    """
    return await agent.run(payload.question, thread_id=str(payload.thread_id))


@knowledge_router.post("/stream")
async def stream_handler(
    payload: AgentPayload,
    agent: Agent = Depends(get_agent(KnowledgeAgentBuilder)),
):
    """Invoke the knowledge agent with Server-Sent Events streaming.

    Processes the user's question and streams incremental updates as the
    agent reasons and executes tools.

    Args:
        payload: Request containing the question and optional thread_id
        agent: Cached agent instance (injected)

    Returns:
        StreamingResponse with SSE events containing messages and tool calls
    """
    stream_response = agent.run_stream(payload.question, thread_id=str(payload.thread_id))

    async def stream_generator():
        async for event in stream_response:
            # Handle StreamEvent based on event_type
            payload: dict[str, str] = {}

            if event.event_type == "message":
                payload["content"] = event.data.get("content", "")
            elif event.event_type == "tool_call":
                tool_calls = event.data.get("tool_calls", [])
                payload["tool_calls"] = ", ".join(
                    f"{tc.get('name', 'unknown')}: {tc.get('args', {})}" for tc in tool_calls
                )
                if event.data.get("content"):
                    payload["content"] = event.data["content"]
            elif event.event_type == "tool_result":
                tool_name = event.data.get("name", "unknown")
                payload["tool_result"] = f"{tool_name}: {event.data.get('content', '')}"
            # Skip state_update and other internal events

            if not payload:
                continue
            yield f"data: {json.dumps(payload)}\n\n"

    # Return streaming response
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
            "Access-Control-Allow-Origin": "*",  # CORS support
        },
    )
