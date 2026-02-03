"""E2E tests for PostgreSQL database connectivity.

These tests verify that the postgres_db fixture works correctly and
demonstrate patterns for testing with a real PostgreSQL database.

Run with: pytest tests/e2e/ -m e2e
Skip with: pytest -m "not e2e"
"""

import uuid

import pytest
from sqlalchemy import text

from my_agentic_serviceservice_order_specialist.platform.database.engine import DbEngine


@pytest.mark.e2e
async def test_postgres_connection(postgres_db: DbEngine):
    """Verify basic PostgreSQL connectivity."""
    async with postgres_db.get_session() as session:
        result = await session.execute(text("SELECT 1 AS value"))
        row = result.fetchone()
        assert row is not None
        assert row.value == 1


@pytest.mark.e2e
async def test_postgres_version(postgres_db: DbEngine):
    """Verify we're connected to PostgreSQL 14."""
    async with postgres_db.get_session() as session:
        result = await session.execute(text("SELECT version()"))
        row = result.fetchone()
        assert row is not None
        assert "PostgreSQL 14" in row[0]


@pytest.mark.e2e
async def test_postgres_uuid_type(postgres_db: DbEngine):
    """Verify PostgreSQL native UUID type works correctly."""
    test_uuid = uuid.uuid4()

    async with postgres_db.transaction() as conn:
        # Create temp table with UUID column
        await conn.execute(text("CREATE TEMP TABLE test_uuids (id UUID PRIMARY KEY)"))

        # Insert UUID
        await conn.execute(
            text("INSERT INTO test_uuids (id) VALUES (:id)"),
            {"id": str(test_uuid)},
        )

        # Query back
        result = await conn.execute(
            text("SELECT id FROM test_uuids WHERE id = :id"),
            {"id": str(test_uuid)},
        )
        row = result.fetchone()

        assert row is not None
        assert str(row.id) == str(test_uuid)


@pytest.mark.e2e
async def test_postgres_jsonb_type(postgres_db: DbEngine):
    """Verify PostgreSQL JSONB type and operators work correctly."""
    async with postgres_db.transaction() as conn:
        # Create temp table with JSONB column
        await conn.execute(text("CREATE TEMP TABLE test_jsonb (id SERIAL PRIMARY KEY, data JSONB)"))

        # Insert JSONB data (use CAST to avoid :: syntax conflict with SQLAlchemy params)
        await conn.execute(
            text("INSERT INTO test_jsonb (data) VALUES (CAST(:data AS JSONB))"),
            {"data": '{"name": "test", "tags": ["a", "b"]}'},
        )

        # Query using JSONB operator
        result = await conn.execute(
            text("SELECT data->>'name' AS name FROM test_jsonb WHERE data ? 'tags'")
        )
        row = result.fetchone()

        assert row is not None
        assert row.name == "test"


@pytest.mark.e2e
async def test_postgres_array_type(postgres_db: DbEngine):
    """Verify PostgreSQL ARRAY type works correctly."""
    async with postgres_db.transaction() as conn:
        # Create temp table with array column
        await conn.execute(
            text("CREATE TEMP TABLE test_arrays (id SERIAL PRIMARY KEY, tags TEXT[])")
        )

        # Insert array data
        await conn.execute(
            text("INSERT INTO test_arrays (tags) VALUES (:tags)"),
            {"tags": ["python", "postgres", "testing"]},
        )

        # Query using array operator
        result = await conn.execute(text("SELECT tags FROM test_arrays WHERE 'python' = ANY(tags)"))
        row = result.fetchone()

        assert row is not None
        assert "python" in row.tags
