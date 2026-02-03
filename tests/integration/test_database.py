"""Integration tests for database engine and setup.

Tests the DbEngine class for connection lifecycle, session management,
and transaction handling with mocked database connections.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from tenacity import wait_none

from my_agentic_serviceservice_order_specialist.platform.database.engine import DbEngine


@pytest.fixture(autouse=True)
def disable_tenacity_wait():
    """Disable tenacity wait times to speed up retry tests.

    Tenacity decorators capture wait strategy at import time, so we need
    to modify the retry object directly on the decorated methods.
    """
    # Store original wait strategy
    original_wait = DbEngine.connect.retry.wait  # type: ignore[attr-defined]

    # Set wait to zero
    DbEngine.connect.retry.wait = wait_none()  # type: ignore[attr-defined]

    yield

    # Restore original wait strategy
    DbEngine.connect.retry.wait = original_wait  # type: ignore[attr-defined]


class TestDbEngineInit:
    """Tests for DbEngine initialization."""

    def test_init_with_defaults(self):
        """DbEngine initializes with default values."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        assert engine.instance_name == "test"
        assert engine.app_name == "test-app"
        assert engine.use_psycopg_pool is True
        assert engine.pool_size == 10
        assert engine.pool_min_size == 1

    def test_init_with_custom_pool_settings(self):
        """DbEngine accepts custom pool settings."""
        engine = DbEngine(
            instance_name="test",
            app_name="test-app",
            pool_size=20,
            pool_min_size=5,
            max_overflow=10,
        )
        assert engine.pool_size == 20
        assert engine.pool_min_size == 5
        assert engine.max_overflow == 10

    def test_init_no_pool_mode(self):
        """DbEngine can be created in no-pool mode."""
        engine = DbEngine(
            instance_name="replica",
            app_name="test-app",
            use_psycopg_pool=False,
        )
        assert engine.use_psycopg_pool is False

    def test_init_engine_not_connected(self):
        """DbEngine starts with no connection."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        assert engine._engine is None
        assert engine._pool is None


class TestDbEngineConnect:
    """Tests for DbEngine.connect() method."""

    @pytest.fixture
    def stub_pool(self):
        """Create a stub connection pool with canned responses."""
        pool = AsyncMock()
        pool.open = AsyncMock()
        pool.getconn = AsyncMock()
        return pool

    @pytest.fixture
    def stub_engine(self):
        """Create a stub SQLAlchemy async engine with canned responses."""
        engine = MagicMock()
        # Stub the async context manager for begin()
        conn_stub = AsyncMock()
        engine.begin = MagicMock(return_value=conn_stub)
        conn_stub.__aenter__ = AsyncMock(return_value=conn_stub)
        conn_stub.__aexit__ = AsyncMock(return_value=None)
        return engine

    async def test_connect_pool_mode_creates_pool(self, stub_pool, stub_engine):
        """connect() in pool mode creates AsyncConnectionPool."""
        engine = DbEngine(
            instance_name="test",
            app_name="test-app",
            use_psycopg_pool=True,
        )

        with (
            patch(
                "my_agentic_serviceservice_order_specialist.platform.database.engine.AsyncConnectionPool",
                return_value=stub_pool,
            ),
            patch(
                "my_agentic_serviceservice_order_specialist.platform.database.engine.create_async_engine",
                return_value=stub_engine,
            ),
        ):
            await engine.connect(
                user="testuser",
                password="testpass",
                host="localhost",
                port=5432,
                database="testdb",
            )

        assert engine._pool is stub_pool
        stub_pool.open.assert_called_once()

    async def test_connect_pool_mode_uses_null_pool(self, stub_pool, stub_engine):
        """connect() in pool mode uses NullPool for SQLAlchemy."""
        engine = DbEngine(
            instance_name="test",
            app_name="test-app",
            use_psycopg_pool=True,
        )

        with (
            patch(
                "my_agentic_serviceservice_order_specialist.platform.database.engine.AsyncConnectionPool",
                return_value=stub_pool,
            ),
            patch(
                "my_agentic_serviceservice_order_specialist.platform.database.engine.create_async_engine",
                return_value=stub_engine,
            ) as mock_create,
        ):
            await engine.connect(
                user="testuser",
                password="testpass",
                host="localhost",
                port=5432,
                database="testdb",
            )

        # Check NullPool was used
        call_kwargs = mock_create.call_args[1]
        from sqlalchemy.pool import NullPool

        assert call_kwargs["poolclass"] is NullPool

    async def test_connect_no_pool_mode(self, stub_engine):
        """connect() in no-pool mode uses SQLAlchemy pooling."""
        engine = DbEngine(
            instance_name="replica",
            app_name="test-app",
            use_psycopg_pool=False,
        )

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.database.engine.create_async_engine",
            return_value=stub_engine,
        ) as mock_create:
            await engine.connect(
                user="testuser",
                password="testpass",
                host="localhost",
                port=5432,
                database="testdb",
            )

        # Check NullPool was NOT used (no poolclass kwarg or different)
        call_kwargs = mock_create.call_args[1]
        assert "poolclass" not in call_kwargs or call_kwargs.get("poolclass") is None

    async def test_connect_returns_engine(self, stub_pool, stub_engine):
        """connect() returns the SQLAlchemy engine."""
        engine = DbEngine(
            instance_name="test",
            app_name="test-app",
            use_psycopg_pool=True,
        )

        with (
            patch(
                "my_agentic_serviceservice_order_specialist.platform.database.engine.AsyncConnectionPool",
                return_value=stub_pool,
            ),
            patch(
                "my_agentic_serviceservice_order_specialist.platform.database.engine.create_async_engine",
                return_value=stub_engine,
            ),
        ):
            result = await engine.connect(
                user="testuser",
                password="testpass",
                host="localhost",
                port=5432,
                database="testdb",
            )

        assert result is stub_engine

    async def test_connect_idempotent(self, stub_pool, stub_engine):
        """connect() is idempotent - returns existing engine if already connected."""
        engine = DbEngine(
            instance_name="test",
            app_name="test-app",
            use_psycopg_pool=True,
        )

        with (
            patch(
                "my_agentic_serviceservice_order_specialist.platform.database.engine.AsyncConnectionPool",
                return_value=stub_pool,
            ),
            patch(
                "my_agentic_serviceservice_order_specialist.platform.database.engine.create_async_engine",
                return_value=stub_engine,
            ) as mock_create,
        ):
            # Connect twice
            await engine.connect(
                user="testuser",
                password="testpass",
                host="localhost",
                port=5432,
                database="testdb",
            )
            await engine.connect(
                user="testuser",
                password="testpass",
                host="localhost",
                port=5432,
                database="testdb",
            )

        # Should only create engine once
        mock_create.assert_called_once()


class TestDbEngineDisconnect:
    """Tests for DbEngine.disconnect() method."""

    async def test_disconnect_disposes_engine(self):
        """disconnect() disposes the SQLAlchemy engine."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        stub_engine = AsyncMock()
        engine._engine = stub_engine

        await engine.disconnect()

        stub_engine.dispose.assert_called_once()
        assert engine._engine is None

    async def test_disconnect_closes_pool(self):
        """disconnect() closes the connection pool."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        stub_pool = AsyncMock()
        engine._pool = stub_pool
        engine._engine = AsyncMock()

        await engine.disconnect()

        stub_pool.close.assert_called_once()
        assert engine._pool is None

    async def test_disconnect_when_not_connected(self):
        """disconnect() is safe to call when not connected."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        # Should not raise
        await engine.disconnect()
        assert engine._engine is None


class TestDbEngineGetEngine:
    """Tests for DbEngine.get_engine() method."""

    def test_get_engine_returns_engine(self):
        """get_engine() returns the engine when connected."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        stub_engine = Mock()
        engine._engine = stub_engine

        result = engine.get_engine()

        assert result is stub_engine

    def test_get_engine_raises_when_not_connected(self):
        """get_engine() raises RuntimeError when not connected."""
        engine = DbEngine(instance_name="test", app_name="test-app")

        with pytest.raises(RuntimeError, match="database is not connected"):
            engine.get_engine()


class TestDbEngineGetPool:
    """Tests for DbEngine.get_pool() method."""

    def test_get_pool_returns_pool(self):
        """get_pool() returns the pool when available."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        stub_pool = Mock()
        engine._pool = stub_pool

        result = engine.get_pool()

        assert result is stub_pool

    def test_get_pool_raises_when_not_connected(self):
        """get_pool() raises RuntimeError when not connected."""
        engine = DbEngine(
            instance_name="test",
            app_name="test-app",
            use_psycopg_pool=True,
        )

        with pytest.raises(RuntimeError, match="Database not connected"):
            engine.get_pool()

    def test_get_pool_raises_in_no_pool_mode(self):
        """get_pool() raises RuntimeError in no-pool mode."""
        engine = DbEngine(
            instance_name="replica",
            app_name="test-app",
            use_psycopg_pool=False,
        )

        with pytest.raises(RuntimeError, match="Pool not available in no-pool mode"):
            engine.get_pool()


class TestDbEngineIsConnected:
    """Tests for DbEngine.is_connected() method."""

    def test_is_connected_true_when_connected(self):
        """is_connected() returns True when engine exists."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        engine._engine = Mock()

        assert engine.is_connected() is True

    def test_is_connected_false_when_not_connected(self):
        """is_connected() returns False when engine is None."""
        engine = DbEngine(instance_name="test", app_name="test-app")

        assert engine.is_connected() is False


class TestDbEngineGetSessionMaker:
    """Tests for DbEngine.get_session_maker() method."""

    def test_get_session_maker_returns_callable(self):
        """get_session_maker() returns a session maker callable."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        engine._engine = Mock()

        with patch("my_agentic_serviceservice_order_specialist.platform.database.engine.async_sessionmaker") as mock_sessionmaker:
            mock_sessionmaker.return_value = Mock()
            result = engine.get_session_maker()

        assert result is not None
        mock_sessionmaker.assert_called_once()


class TestDbEngineGetSession:
    """Tests for DbEngine.get_session() context manager."""

    async def test_get_session_yields_session(self):
        """get_session() yields a database session."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        mock_session = AsyncMock()
        mock_session_maker = Mock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch.object(engine, "get_session_maker", return_value=mock_session_maker):
            async with engine.get_session() as session:
                assert session is not None

    async def test_get_session_commits_on_success(self):
        """get_session() commits the session on success."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        mock_session = AsyncMock()
        mock_session_maker = Mock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch.object(engine, "get_session_maker", return_value=mock_session_maker):
            async with engine.get_session():
                pass

        mock_session.commit.assert_called_once()

    async def test_get_session_rollbacks_on_error(self):
        """get_session() rolls back the session on error."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        mock_session = AsyncMock()
        mock_session_maker = Mock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch.object(engine, "get_session_maker", return_value=mock_session_maker):
            with pytest.raises(ValueError):
                async with engine.get_session():
                    raise ValueError("Test error")

        mock_session.rollback.assert_called_once()


class TestDbEngineTransaction:
    """Tests for DbEngine.transaction() context manager."""

    async def test_transaction_yields_connection(self):
        """transaction() yields a database connection."""
        engine = DbEngine(instance_name="test", app_name="test-app")
        stub_engine = Mock()
        mock_conn = AsyncMock()
        stub_engine.begin = Mock(return_value=mock_conn)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        engine._engine = stub_engine

        async with engine.transaction() as conn:
            assert conn is not None

    async def test_transaction_raises_when_not_connected(self):
        """transaction() raises RuntimeError when not connected."""
        engine = DbEngine(instance_name="test", app_name="test-app")

        with pytest.raises(RuntimeError, match="database is not connected"):
            async with engine.transaction():
                pass


class TestDbEngineSchemaConstant:
    """Tests for DbEngine class constants."""

    def test_schema_constant(self):
        """DbEngine has correct SCHEMA constant."""
        assert DbEngine.SCHEMA == "postgresql+psycopg"
