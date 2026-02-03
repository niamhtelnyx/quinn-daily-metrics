"""Integration tests for ConversationRepository.

Tests the conversation repository with mocked database session and checkpointer.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from my_agentic_serviceservice_order_specialist.platform.database.repositories.conversations import (
    ConversationFilters,
    ConversationRepository,
    PaginatedResult,
    Pagination,
)


class TestPagination:
    """Tests for Pagination dataclass."""

    @pytest.mark.parametrize(
        ("page", "page_size", "expected_offset"),
        [
            (1, 20, 0),  # Page 1 has offset 0
            (2, 20, 20),  # Page 2 offset = page_size
            (3, 10, 20),  # Page 3 offset = 2 * page_size
            (5, 25, 100),  # Page 5 offset = 4 * 25
        ],
    )
    def test_offset_calculation(self, page: int, page_size: int, expected_offset: int):
        """Offset is calculated as (page - 1) * page_size."""
        pagination = Pagination(page=page, page_size=page_size)
        assert pagination.offset == expected_offset

    def test_default_values(self):
        """Default pagination is page 1, size 20."""
        pagination = Pagination()
        assert pagination.page == 1
        assert pagination.page_size == 20


class TestPaginatedResult:
    """Tests for PaginatedResult dataclass."""

    @pytest.mark.parametrize(
        ("total", "page_size", "expected_pages"),
        [
            (0, 20, 0),  # Zero items = zero pages
            (40, 20, 2),  # Exact fit
            (45, 20, 3),  # Partial last page rounds up
            (1, 20, 1),  # One item = one page
            (100, 10, 10),  # Larger numbers
        ],
    )
    def test_total_pages_calculation(self, total: int, page_size: int, expected_pages: int):
        """Total pages is ceil(total / page_size)."""
        result = PaginatedResult(items=[], total=total, page=1, page_size=page_size)
        assert result.total_pages == expected_pages


class TestConversationRepositoryInit:
    """Tests for ConversationRepository initialization."""

    def test_init_stores_db_engine(self):
        """Repository stores db engine."""
        mock_db = Mock()
        repo = ConversationRepository(db_engine=mock_db)
        assert repo._db is mock_db

    def test_init_stores_checkpointer(self):
        """Repository stores optional checkpointer."""
        mock_db = Mock()
        mock_checkpointer = Mock()
        repo = ConversationRepository(db_engine=mock_db, checkpointer=mock_checkpointer)
        assert repo._checkpointer is mock_checkpointer

    def test_init_checkpointer_defaults_none(self):
        """Checkpointer defaults to None."""
        mock_db = Mock()
        repo = ConversationRepository(db_engine=mock_db)
        assert repo._checkpointer is None


class TestBuildWhereClause:
    """Tests for _build_where_clause method."""

    def test_no_filters(self):
        """No filters returns base condition."""
        mock_db = Mock()
        repo = ConversationRepository(db_engine=mock_db)
        filters = ConversationFilters()

        clause, params = repo._build_where_clause(filters)

        assert clause == "1=1"
        assert params == {}

    def test_start_date_filter(self):
        """Start date filter adds condition."""
        mock_db = Mock()
        repo = ConversationRepository(db_engine=mock_db)
        start = datetime(2025, 1, 1, tzinfo=UTC)
        filters = ConversationFilters(start_date=start)

        clause, params = repo._build_where_clause(filters)

        assert "updated_at::timestamptz >= :start_date" in clause
        assert params["start_date"] == start

    def test_end_date_filter(self):
        """End date filter adds condition."""
        mock_db = Mock()
        repo = ConversationRepository(db_engine=mock_db)
        end = datetime(2025, 12, 31, tzinfo=UTC)
        filters = ConversationFilters(end_date=end)

        clause, params = repo._build_where_clause(filters)

        assert "updated_at::timestamptz <= :end_date" in clause
        assert params["end_date"] == end

    def test_both_date_filters(self):
        """Both date filters add both conditions."""
        mock_db = Mock()
        repo = ConversationRepository(db_engine=mock_db)
        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 12, 31, tzinfo=UTC)
        filters = ConversationFilters(start_date=start, end_date=end)

        clause, params = repo._build_where_clause(filters)

        assert "updated_at::timestamptz >= :start_date" in clause
        assert "updated_at::timestamptz <= :end_date" in clause
        assert params["start_date"] == start
        assert params["end_date"] == end


class TestExtractFirstUserMessage:
    """Tests for _extract_first_user_message static method."""

    def test_extract_from_langchain_message(self):
        """Extracts content from LangChain message object."""
        mock_msg = Mock()
        mock_msg.type = "human"
        mock_msg.content = "Hello, how are you?"

        result = ConversationRepository._extract_first_user_message([mock_msg])

        assert result == "Hello, how are you?"

    def test_extract_from_dict_message(self):
        """Extracts content from dict format message."""
        msg = {"type": "human", "content": "Hello world"}

        result = ConversationRepository._extract_first_user_message([msg])

        assert result == "Hello world"

    def test_skips_non_human_messages(self):
        """Skips AI messages to find first human."""
        ai_msg = Mock()
        ai_msg.type = "ai"
        ai_msg.content = "I am AI"

        human_msg = Mock()
        human_msg.type = "human"
        human_msg.content = "Hello"

        result = ConversationRepository._extract_first_user_message([ai_msg, human_msg])

        assert result == "Hello"

    def test_truncates_long_messages(self):
        """Long messages are truncated with ellipsis."""
        long_content = "x" * 300
        mock_msg = Mock()
        mock_msg.type = "human"
        mock_msg.content = long_content

        result = ConversationRepository._extract_first_user_message([mock_msg])

        assert result is not None
        assert len(result) == 203  # 200 chars + "..."
        assert result.endswith("...")

    def test_custom_max_length(self):
        """Can specify custom max length."""
        mock_msg = Mock()
        mock_msg.type = "human"
        mock_msg.content = "Hello, this is a test message"

        result = ConversationRepository._extract_first_user_message([mock_msg], max_length=10)

        assert result == "Hello, thi..."

    def test_empty_messages_list(self):
        """Empty list returns None."""
        result = ConversationRepository._extract_first_user_message([])
        assert result is None

    def test_no_human_messages(self):
        """No human messages returns None."""
        ai_msg = Mock()
        ai_msg.type = "ai"
        ai_msg.content = "I am AI"

        result = ConversationRepository._extract_first_user_message([ai_msg])

        assert result is None

    def test_empty_content(self):
        """Empty content returns None."""
        mock_msg = Mock()
        mock_msg.type = "human"
        mock_msg.content = ""

        result = ConversationRepository._extract_first_user_message([mock_msg])

        assert result is None


class TestEnrichWithMessages:
    """Tests for _enrich_with_messages method."""

    async def test_without_checkpointer_returns_basic_info(self):
        """Without checkpointer, returns basic info without messages."""
        mock_db = Mock()
        repo = ConversationRepository(db_engine=mock_db, checkpointer=None)

        row = Mock()
        row.thread_id = "thread-123"
        row.created_at = "2025-01-01T00:00:00"
        row.updated_at = "2025-01-01T12:00:00"

        result = await repo._enrich_with_messages([row])

        assert len(result) == 1
        assert result[0].thread_id == "thread-123"
        assert result[0].first_user_message is None
        assert result[0].message_count == 0

    async def test_with_checkpointer_enriches_messages(self):
        """With checkpointer, enriches with message data."""
        mock_db = Mock()
        mock_checkpointer = AsyncMock()

        # Mock checkpoint tuple with messages
        mock_msg = Mock()
        mock_msg.type = "human"
        mock_msg.content = "Hello"

        mock_tuple = Mock()
        mock_tuple.checkpoint = {
            "channel_values": {
                "messages": [mock_msg],
                "agent_slug": "knowledge",
            }
        }
        mock_checkpointer.aget_tuple = AsyncMock(return_value=mock_tuple)

        repo = ConversationRepository(db_engine=mock_db, checkpointer=mock_checkpointer)

        row = Mock()
        row.thread_id = "thread-123"
        row.created_at = "2025-01-01T00:00:00"
        row.updated_at = "2025-01-01T12:00:00"

        result = await repo._enrich_with_messages([row])

        assert len(result) == 1
        assert result[0].thread_id == "thread-123"
        assert result[0].agent_slug == "knowledge"
        assert result[0].first_user_message == "Hello"
        assert result[0].message_count == 1

    async def test_with_checkpointer_handles_missing_checkpoint(self):
        """Handles case where checkpoint doesn't exist for thread."""
        mock_db = Mock()
        mock_checkpointer = AsyncMock()
        mock_checkpointer.aget_tuple = AsyncMock(return_value=None)

        repo = ConversationRepository(db_engine=mock_db, checkpointer=mock_checkpointer)

        row = Mock()
        row.thread_id = "thread-missing"
        row.created_at = "2025-01-01T00:00:00"
        row.updated_at = "2025-01-01T12:00:00"

        result = await repo._enrich_with_messages([row])

        assert len(result) == 1
        assert result[0].thread_id == "thread-missing"
        assert result[0].first_user_message is None
        assert result[0].message_count == 0


class TestListConversations:
    """Tests for list_conversations method."""

    @pytest.fixture
    def mock_db_engine(self):
        """Create mock DB engine with session context manager."""
        mock_session = AsyncMock()
        mock_db = Mock()

        # Create async context manager for session
        mock_db.get_session = Mock()
        mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.get_session.return_value.__aexit__ = AsyncMock()

        return mock_db, mock_session

    async def test_list_conversations_empty_result(self, mock_db_engine):
        """List returns empty result when no conversations."""
        mock_db, mock_session = mock_db_engine

        # Mock empty result
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        repo = ConversationRepository(db_engine=mock_db)
        result = await repo.list_conversations(
            filters=ConversationFilters(),
            pagination=Pagination(),
        )

        assert result.total == 0
        assert result.items == []
        assert result.page == 1
        assert result.page_size == 20

    async def test_list_conversations_with_results(self, mock_db_engine):
        """List returns conversation summaries."""
        mock_db, mock_session = mock_db_engine

        # Mock result with one row
        row = Mock()
        row.thread_id = "thread-123"
        row.created_at = "2025-01-01T00:00:00"
        row.updated_at = "2025-01-01T12:00:00"

        mock_result = Mock()
        mock_result.fetchall.return_value = [row]
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        repo = ConversationRepository(db_engine=mock_db)
        result = await repo.list_conversations(
            filters=ConversationFilters(),
            pagination=Pagination(),
        )

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].thread_id == "thread-123"

    async def test_list_conversations_with_agent_filter(self, mock_db_engine):
        """Agent filter is applied after enrichment."""
        mock_db, mock_session = mock_db_engine

        # Mock results with different agent_slugs
        row1 = Mock()
        row1.thread_id = "thread-1"
        row1.created_at = "2025-01-01T00:00:00"
        row1.updated_at = "2025-01-01T12:00:00"

        row2 = Mock()
        row2.thread_id = "thread-2"
        row2.created_at = "2025-01-01T00:00:00"
        row2.updated_at = "2025-01-01T12:00:00"

        mock_result = Mock()
        mock_result.fetchall.return_value = [row1, row2]
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 2
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        # Mock checkpointer to return different agent_slugs
        mock_checkpointer = AsyncMock()

        async def get_tuple(config):
            thread_id = config["configurable"]["thread_id"]
            mock_tuple = Mock()
            if thread_id == "thread-1":
                mock_tuple.checkpoint = {
                    "channel_values": {"agent_slug": "knowledge", "messages": []}
                }
            else:
                mock_tuple.checkpoint = {"channel_values": {"agent_slug": "other", "messages": []}}
            return mock_tuple

        mock_checkpointer.aget_tuple = get_tuple

        repo = ConversationRepository(db_engine=mock_db, checkpointer=mock_checkpointer)
        result = await repo.list_conversations(
            filters=ConversationFilters(agent_slug="knowledge"),
            pagination=Pagination(),
        )

        # Only thread-1 should match the agent_slug filter
        assert len(result.items) == 1
        assert result.items[0].thread_id == "thread-1"

    async def test_list_conversations_pagination(self, mock_db_engine):
        """Pagination parameters are passed to query."""
        mock_db, mock_session = mock_db_engine

        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])

        repo = ConversationRepository(db_engine=mock_db)
        result = await repo.list_conversations(
            filters=ConversationFilters(),
            pagination=Pagination(page=3, page_size=10),
        )

        # Verify pagination is reflected in result
        assert result.page == 3
        assert result.page_size == 10

        # Verify execute was called with pagination params
        calls = mock_session.execute.call_args_list
        # First call is the main query
        main_query_params = calls[0][0][1]
        assert main_query_params["limit"] == 10
        assert main_query_params["offset"] == 20  # (3-1) * 10
