"""Conversation repository for accessing checkpoint data.

This module provides a clean abstraction over the LangGraph checkpoint tables,
enabling efficient querying of conversation history for debugging and analytics.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy import text

from my_agentic_serviceservice_order_specialist.platform.database.engine import DbEngine


@dataclass(frozen=True)
class Pagination:
    """Pagination parameters."""

    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True)
class ConversationFilters:
    """Filters for conversation queries."""

    start_date: datetime | None = None
    end_date: datetime | None = None
    agent_slug: str | None = None


@dataclass(frozen=True)
class ConversationSummary:
    """Summary of a conversation for list views."""

    thread_id: str
    agent_slug: str | None
    created_at: str
    updated_at: str
    first_user_message: str | None
    message_count: int


@dataclass(frozen=True)
class PaginatedResult:
    """Paginated query result."""

    items: list[ConversationSummary]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class ConversationRepository:
    """Repository for accessing conversation data from LangGraph checkpoints.

    Provides an abstraction over the checkpoint tables, handling query
    optimization and data transformation.
    """

    # Base namespace filter - empty string is the main graph namespace
    _BASE_FILTER = "checkpoint_ns = ''"

    def __init__(
        self, db_engine: DbEngine, checkpointer: BaseCheckpointSaver | None = None
    ) -> None:
        self._db = db_engine
        self._checkpointer = checkpointer

    async def list_conversations(
        self,
        filters: ConversationFilters,
        pagination: Pagination,
    ) -> PaginatedResult:
        """List conversations with filtering and pagination.

        Uses DISTINCT ON for efficient retrieval of latest checkpoint per thread.
        Message data is fetched via checkpointer since LangGraph stores messages
        as binary blobs in a separate table.

        Args:
            filters: Optional filters for date range and agent
            pagination: Page number and size

        Returns:
            Paginated list of conversation summaries
        """
        where_clause, params = self._build_where_clause(filters)
        params["limit"] = pagination.page_size
        params["offset"] = pagination.offset

        # Get thread metadata from checkpoints table
        query = text(f"""
            WITH latest AS (
                SELECT DISTINCT ON (thread_id)
                    thread_id,
                    checkpoint->>'ts' as updated_at
                FROM checkpoints
                WHERE {self._BASE_FILTER}
                ORDER BY thread_id, checkpoint->>'ts' DESC
            ),
            first_ts AS (
                SELECT DISTINCT ON (thread_id)
                    thread_id,
                    checkpoint->>'ts' as created_at
                FROM checkpoints
                WHERE {self._BASE_FILTER}
                ORDER BY thread_id, checkpoint->>'ts' ASC
            ),
            combined AS (
                SELECT
                    l.thread_id,
                    f.created_at,
                    l.updated_at
                FROM latest l
                JOIN first_ts f ON l.thread_id = f.thread_id
                WHERE {where_clause}
            )
            SELECT * FROM combined
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
        """)

        count_query = text(f"""
            WITH latest AS (
                SELECT DISTINCT ON (thread_id)
                    thread_id,
                    checkpoint->>'ts' as updated_at
                FROM checkpoints
                WHERE {self._BASE_FILTER}
                ORDER BY thread_id, checkpoint->>'ts' DESC
            )
            SELECT COUNT(*) FROM latest WHERE {where_clause}
        """)

        async with self._db.get_session() as session:
            result = await session.execute(query, params)
            rows = result.fetchall()

            count_result = await session.execute(count_query, params)
            total = count_result.scalar() or 0

        # Enrich with message data from checkpointer
        items = await self._enrich_with_messages(rows)

        # Apply agent_slug filter if specified (filter after enrichment)
        if filters.agent_slug:
            items = [i for i in items if i.agent_slug == filters.agent_slug]

        return PaginatedResult(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def _enrich_with_messages(self, rows: Sequence[Any]) -> list[ConversationSummary]:
        """Enrich thread metadata with message data from checkpointer.

        LangGraph stores messages as msgpack blobs in checkpoint_blobs table,
        so we use the checkpointer's proper deserialization to get message data.

        Args:
            rows: Database rows with thread_id, created_at, updated_at

        Returns:
            List of ConversationSummary with message data populated
        """
        if not self._checkpointer:
            # Without checkpointer, return basic info without message data
            return [
                ConversationSummary(
                    thread_id=row.thread_id,
                    agent_slug=None,
                    created_at=row.created_at or "",
                    updated_at=row.updated_at or "",
                    first_user_message=None,
                    message_count=0,
                )
                for row in rows
            ]

        items = []
        for row in rows:
            config: RunnableConfig = {"configurable": {"thread_id": row.thread_id}}
            checkpoint_tuple = await self._checkpointer.aget_tuple(config)

            if checkpoint_tuple is None:
                items.append(
                    ConversationSummary(
                        thread_id=row.thread_id,
                        agent_slug=None,
                        created_at=row.created_at or "",
                        updated_at=row.updated_at or "",
                        first_user_message=None,
                        message_count=0,
                    )
                )
                continue

            state = checkpoint_tuple.checkpoint.get("channel_values", {})
            messages = state.get("messages", [])

            items.append(
                ConversationSummary(
                    thread_id=row.thread_id,
                    agent_slug=state.get("agent_slug"),
                    created_at=row.created_at or "",
                    updated_at=row.updated_at or "",
                    first_user_message=self._extract_first_user_message(messages),
                    message_count=len(messages),
                )
            )

        return items

    def _build_where_clause(self, filters: ConversationFilters) -> tuple[str, dict[str, Any]]:
        """Build WHERE clause and parameters from filters.

        Note: agent_slug filter is applied after enrichment since it requires
        fetching from checkpointer. Only date filters are applied in SQL.

        Returns:
            Tuple of (where_clause_sql, params_dict)
        """
        conditions = ["1=1"]
        params: dict[str, Any] = {}

        if filters.start_date:
            conditions.append("updated_at::timestamptz >= :start_date")
            params["start_date"] = filters.start_date

        if filters.end_date:
            conditions.append("updated_at::timestamptz <= :end_date")
            params["end_date"] = filters.end_date

        # Note: agent_slug is filtered after enrichment, not in SQL

        return " AND ".join(conditions), params

    @staticmethod
    def _extract_first_user_message(messages: list[Any], max_length: int = 200) -> str | None:
        """Extract and truncate the first user message.

        Args:
            messages: List of LangChain message objects
            max_length: Maximum length before truncation

        Returns:
            First user message truncated, or None if not found
        """
        for msg in messages:
            # Handle LangChain message objects
            if hasattr(msg, "type") and msg.type == "human":
                content = getattr(msg, "content", "")
                if isinstance(content, str) and content:
                    if len(content) > max_length:
                        return content[:max_length] + "..."
                    return content
            # Handle dict format (fallback)
            elif isinstance(msg, dict) and msg.get("type") == "human":
                content = msg.get("content", "")
                if isinstance(content, str) and content:
                    if len(content) > max_length:
                        return content[:max_length] + "..."
                    return content
        return None
