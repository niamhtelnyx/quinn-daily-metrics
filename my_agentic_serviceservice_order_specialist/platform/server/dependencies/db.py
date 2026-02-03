"""Database dependencies for FastAPI routes."""

from fastapi import Depends, Request
from langgraph.checkpoint.base import BaseCheckpointSaver
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import AsyncEngine

from my_agentic_serviceservice_order_specialist.platform.database.engine import DbEngine
from my_agentic_serviceservice_order_specialist.platform.database.repositories import ConversationRepository


def get_primary_db(request: Request) -> DbEngine:
    """Get the primary database instance."""
    return request.app.state.db_engine


def get_replica_db(request: Request) -> DbEngine | None:
    """Get the replica database instance (if configured)."""
    return getattr(request.app.state, "replica_db_engine", None)


def get_db_engine(db: DbEngine = Depends(get_primary_db)) -> AsyncEngine:
    """Get SQLAlchemy AsyncEngine from primary database."""
    return db.get_engine()


def get_db_pool(db: DbEngine = Depends(get_primary_db)) -> AsyncConnectionPool:
    """Get raw AsyncConnectionPool for LangGraph checkpointing."""
    return db.get_pool()


def get_db_checkpointer(request: Request) -> BaseCheckpointSaver:
    """Get BaseCheckpointSaver for LangGraph checkpointing."""
    return request.app.state.db_checkpointer


def get_conversation_repository(
    db: DbEngine = Depends(get_primary_db),
    checkpointer: BaseCheckpointSaver = Depends(get_db_checkpointer),
) -> ConversationRepository:
    """Get ConversationRepository for querying conversation data."""
    return ConversationRepository(db, checkpointer)
