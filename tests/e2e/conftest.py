"""End-to-end test fixtures using real PostgreSQL via testcontainers.

These fixtures provide a real PostgreSQL database for true end-to-end tests
that verify full-stack behavior including database operations.

Run with: pytest tests/e2e/ -m e2e
Skip with: pytest -m "not e2e"
"""

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from testcontainers.postgres import PostgresContainer

from my_agentic_serviceservice_order_specialist.platform.database.engine import DbEngine


def _is_ci_mode() -> bool:
    """Check if running in CI with pre-provisioned database."""
    return os.environ.get("TEST_DB_HOST") is not None


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer | None]:
    """Start a PostgreSQL container for the test session.

    In CI mode (when TEST_DB_HOST is set), this yields None since
    the database is already provisioned via docker-compose.

    Yields:
        PostgresContainer with connection details, or None in CI mode.
    """
    if _is_ci_mode():
        yield None
    else:
        with PostgresContainer("postgres:14") as container:
            yield container


@pytest.fixture(scope="session")
def postgres_connection_info(
    postgres_container: PostgresContainer | None,
) -> dict[str, str | int]:
    """Extract connection parameters from the PostgreSQL container or CI environment.

    Returns:
        Dictionary with keys: host, port, user, password, database
    """
    if _is_ci_mode():
        return {
            "host": os.environ["TEST_DB_HOST"],
            "port": int(os.environ.get("TEST_DB_PORT", "5432")),
            "user": os.environ.get("TEST_DB_USER", "postgres"),
            "password": os.environ.get("TEST_DB_PASSWORD", "postgres"),
            "database": os.environ.get("TEST_DB_DATABASE", "my_agentic_serviceservice_order_specialist"),
        }
    assert postgres_container is not None
    return {
        "host": postgres_container.get_container_host_ip(),
        "port": int(postgres_container.get_exposed_port(5432)),
        "user": postgres_container.username,
        "password": postgres_container.password,
        "database": postgres_container.dbname,
    }


@pytest.fixture
async def postgres_db(
    postgres_connection_info: dict[str, str | int],
) -> AsyncIterator[DbEngine]:
    """Create a DbEngine connected to the PostgreSQL instance.

    Yields:
        Connected DbEngine instance
    """
    db = DbEngine(
        instance_name="test-postgres",
        app_name="test-suite",
        use_psycopg_pool=True,
        pool_size=5,
        pool_min_size=1,
    )

    await db.connect(
        host=str(postgres_connection_info["host"]),
        port=int(postgres_connection_info["port"]),
        user=str(postgres_connection_info["user"]),
        password=str(postgres_connection_info["password"]),
        database=str(postgres_connection_info["database"]),
    )

    yield db

    await db.disconnect()
