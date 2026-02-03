"""Database engine management.

This module provides the DbEngine class for managing async PostgreSQL connections
with optional psycopg connection pooling for LangGraph checkpointer integration.
"""

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, ClassVar, Protocol, TypeVar, cast

import sqlalchemy as sa
import tenacity
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncResult,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.sql.selectable import TypedReturnsRows

logger = logging.getLogger(__name__)

_T = TypeVar("_T", bound=Any)
AsyncSessionMaker = Callable[[], AsyncSession]


class DbSession(Protocol):
    async def execute(
        self,
        query: TypedReturnsRows | sa.Delete | sa.Update | sa.TextClause,
        *args,
        **kwargs,
    ) -> sa.Result[_T]: ...

    async def stream(
        self,
        query: TypedReturnsRows | sa.Delete | sa.Update | sa.TextClause,
        *args,
        **kwargs,
    ) -> AsyncResult[_T]: ...


@dataclass
class DbEngine:
    """Database engine with optional psycopg pool for LangGraph integration.

    Two modes:
    - Pool mode (use_psycopg_pool=True): Creates AsyncConnectionPool, SQLAlchemy
      uses NullPool with pool's getconn. Required for LangGraph checkpointer.
    - No-pool mode (use_psycopg_pool=False): No pool, SQLAlchemy uses its own
      pooling. Suitable for read-only replicas.
    """

    instance_name: str
    app_name: str
    use_psycopg_pool: bool = True
    pool_size: int = 10
    pool_min_size: int = 1
    max_overflow: int = 5
    timeout: int = 60
    _engine: AsyncEngine | None = field(init=False, default=None)
    _pool: AsyncConnectionPool | None = field(init=False, default=None)

    SCHEMA: ClassVar[str] = "postgresql+psycopg"

    @tenacity.retry(
        wait=tenacity.wait_fixed(2),
        stop=(tenacity.stop_after_attempt(3) | tenacity.stop_after_delay(10)),
        retry=tenacity.retry_if_not_exception_type(RuntimeError),
        reraise=True,
    )
    async def connect(
        self,
        *,
        user: str,
        password: str,
        host: str,
        port: int,
        database: str,
        echo: bool = False,
    ) -> AsyncEngine:
        if self._engine is not None:
            return self._engine

        if self.use_psycopg_pool:
            # Pool mode: psycopg_pool + NullPool (for LangGraph)
            conninfo = f"postgresql://{user}:{password}@{host}:{port}/{database}"

            self._pool = AsyncConnectionPool(
                conninfo,
                min_size=self.pool_min_size,
                max_size=self.pool_size,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "application_name": self.app_name,
                },
                open=False,
                close_returns=True,  # Return to pool instead of closing
            )
            await self._pool.open()

            self._engine = create_async_engine(
                f"{self.SCHEMA}://",
                poolclass=NullPool,
                async_creator=self._pool.getconn,
                echo=echo,
            )
        else:
            # No-pool mode: SQLAlchemy pooling (for replicas)
            db_uri = f"{self.SCHEMA}://{user}:{password}@{host}:{port}/{database}"
            self._engine = create_async_engine(
                db_uri,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_use_lifo=True,
                pool_pre_ping=True,
                pool_recycle=120,
                pool_timeout=self.timeout,
                echo=echo,
                connect_args={
                    "prepare_threshold": None,
                    "application_name": self.app_name,
                },
            )

        # Test initial connection
        async with self._engine.begin():
            pass

        logger.info(
            f"Database '{self.instance_name}' connected (pool_mode={self.use_psycopg_pool})"
        )
        return self._engine

    async def disconnect(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None

        if self._pool is not None:
            await self._pool.close()
            self._pool = None

        logger.info(f"Database '{self.instance_name}' disconnected")

    def get_engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError(f"{self.instance_name} database is not connected")
        return self._engine

    def get_pool(self) -> AsyncConnectionPool:
        """Get the raw connection pool for LangGraph integration.

        Raises:
            RuntimeError: If pool is not available (no-pool mode or not connected)
        """
        if self._pool is None:
            if not self.use_psycopg_pool:
                raise RuntimeError(f"{self.instance_name}: Pool not available in no-pool mode")
            raise RuntimeError(f"{self.instance_name}: Database not connected")
        return self._pool

    def is_connected(self) -> bool:
        """Check if the database is currently connected."""
        return self._engine is not None

    def get_session_maker(self) -> AsyncSessionMaker:
        return async_sessionmaker(self._engine, expire_on_commit=False)

    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[DbSession]:
        session_maker = self.get_session_maker()
        async with session_maker() as db_session:  # type: ignore
            try:
                yield cast(DbSession, db_session)
                await db_session.commit()  # type: ignore
            except Exception:
                await db_session.rollback()  # type: ignore
                raise

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[DbSession]:
        engine = self.get_engine()
        async with engine.begin() as conn:
            yield cast(DbSession, conn)
