"""Conversation history retrieval endpoints.

This module provides endpoints to list and retrieve conversation history for
debugging and reviewing agent interactions.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field

from my_agentic_serviceservice_order_specialist.platform.agent.langgraph import LangGraphMessageParser
from my_agentic_serviceservice_order_specialist.platform.agent.messages import Message
from my_agentic_serviceservice_order_specialist.platform.database.repositories import (
    ConversationFilters,
    ConversationRepository,
    Pagination,
)
from my_agentic_serviceservice_order_specialist.platform.server.dependencies.db import (
    get_conversation_repository,
    get_db_checkpointer,
)

conversations_router = APIRouter(prefix="/conversations", tags=["conversations"])

MAX_PAGE_SIZE = 100


# =============================================================================
# Response Models
# =============================================================================


class ConversationListItem(BaseModel):
    """Summary item for conversation listing."""

    thread_id: str
    agent_slug: str | None
    created_at: str
    updated_at: str
    first_user_message: str | None = Field(
        default=None, description="First user message, truncated to 200 chars"
    )
    message_count: int


class ConversationListResponse(BaseModel):
    """Paginated response for conversation listing."""

    items: list[ConversationListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class TokenUsage(BaseModel):
    """Token usage statistics for a conversation."""

    input_tokens_by_model: dict[str, int]
    output_tokens_by_model: dict[str, int]
    total_input_tokens: int
    total_output_tokens: int


class ConversationResponse(BaseModel):
    """Full conversation detail response."""

    thread_id: str
    agent_slug: str | None
    messages: list[dict[str, Any]]
    reasoning_steps: int
    updated_at: str
    total_steps: int
    token_usage: TokenUsage | None


# =============================================================================
# Endpoints
# =============================================================================


@conversations_router.get("")
async def list_conversations(
    repo: Annotated[ConversationRepository, Depends(get_conversation_repository)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Items per page")] = 20,
    start_date: Annotated[
        datetime | None, Query(description="Filter: updated after this time")
    ] = None,
    end_date: Annotated[
        datetime | None, Query(description="Filter: updated before this time")
    ] = None,
    agent_slug: Annotated[str | None, Query(description="Filter by agent type")] = None,
) -> ConversationListResponse:
    """List conversations with pagination and filtering.

    Args:
        repo: Conversation repository (injected)
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        start_date: Filter conversations updated after this datetime
        end_date: Filter conversations updated before this datetime
        agent_slug: Filter by agent type

    Returns:
        Paginated list of conversation summaries
    """
    filters = ConversationFilters(
        start_date=start_date,
        end_date=end_date,
        agent_slug=agent_slug,
    )
    pagination = Pagination(page=page, page_size=page_size)

    result = await repo.list_conversations(filters, pagination)

    return ConversationListResponse(
        items=[
            ConversationListItem(
                thread_id=item.thread_id,
                agent_slug=item.agent_slug,
                created_at=item.created_at,
                updated_at=item.updated_at,
                first_user_message=item.first_user_message,
                message_count=item.message_count,
            )
            for item in result.items
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@conversations_router.get("/{thread_id}")
async def get_conversation(
    thread_id: uuid.UUID,
    checkpointer: Annotated[BaseCheckpointSaver, Depends(get_db_checkpointer)],
) -> ConversationResponse:
    """Retrieve full conversation history for a thread.

    Args:
        thread_id: The unique identifier for the conversation thread
        checkpointer: LangGraph checkpointer (injected)

    Returns:
        Full conversation with messages and metadata

    Raises:
        HTTPException: 404 if thread not found
    """
    config: RunnableConfig = {"configurable": {"thread_id": str(thread_id)}}

    checkpoint_tuple = await checkpointer.aget_tuple(config)
    if checkpoint_tuple is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    checkpoint = checkpoint_tuple.checkpoint
    state = checkpoint.get("channel_values", {})
    if not state:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = state.get("messages", [])
    parser = LangGraphMessageParser()
    converted_messages = parser._convert_messages(messages)

    metadata = checkpoint_tuple.metadata or {}

    return ConversationResponse(
        thread_id=str(thread_id),
        agent_slug=state.get("agent_slug"),
        messages=[_message_to_dict(msg) for msg in converted_messages],
        reasoning_steps=state.get("reasoning_steps", 0),
        updated_at=checkpoint.get("ts", ""),
        total_steps=metadata.get("step", 0),
        token_usage=_build_token_usage(state),
    )


# =============================================================================
# Helpers
# =============================================================================


def _message_to_dict(msg: Message) -> dict[str, Any]:
    """Convert a Message dataclass to a dictionary for JSON serialization."""
    result: dict[str, Any] = {
        "role": msg.role,
        "content": msg.content,
    }
    if msg.tool_calls is not None:
        result["tool_calls"] = msg.tool_calls
    if msg.tool_call_id is not None:
        result["tool_call_id"] = msg.tool_call_id
    if msg.name is not None:
        result["name"] = msg.name
    return result


def _build_token_usage(state: dict[str, Any]) -> TokenUsage | None:
    """Build token usage from agent state."""
    input_by_model = state.get("input_tokens_by_model", {})
    output_by_model = state.get("output_tokens_by_model", {})

    if not input_by_model and not output_by_model:
        return None

    return TokenUsage(
        input_tokens_by_model=input_by_model,
        output_tokens_by_model=output_by_model,
        total_input_tokens=sum(input_by_model.values()),
        total_output_tokens=sum(output_by_model.values()),
    )
