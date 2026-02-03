"""Database setup and teardown functions.

This module provides functions for initializing and closing database connections
during FastAPI application lifecycle, including LangGraph checkpointer setup.
"""

import asyncio
import logging

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from my_agentic_serviceservice_order_specialist.platform.constants import SERVICE_NAME

from .engine import DbEngine

logger = logging.getLogger(__name__)


async def setup_db(app: FastAPI) -> None:
    logger.info("Setting up databases...")

    db_engine = DbEngine(
        instance_name="Primary",
        app_name=SERVICE_NAME,
        pool_size=5,
        use_psycopg_pool=True,
    )
    app.state.db_engine = db_engine

    replica_db_engine = DbEngine(
        instance_name="Replica",
        app_name=SERVICE_NAME,
        pool_size=5,
        use_psycopg_pool=False,
    )
    app.state.replica_db_engine = replica_db_engine

    async with asyncio.TaskGroup() as tg:
        tg.create_task(db_engine.connect(**app.state.settings.primary_db.model_dump()))
        tg.create_task(replica_db_engine.connect(**app.state.settings.replica_db.model_dump()))

    db_checkpointer = AsyncPostgresSaver(db_engine.get_pool())  # type: ignore
    logger.info("Setting up database checkpointer...")
    await db_checkpointer.setup()
    app.state.db_checkpointer = db_checkpointer

    logger.info("Databases setup complete")


async def close_db(app: FastAPI) -> None:
    logger.info("Closing databases...")

    async with asyncio.TaskGroup() as tg:
        if app.state.db_engine:
            tg.create_task(app.state.db_engine.disconnect())
        if app.state.replica_db_engine:
            tg.create_task(app.state.replica_db_engine.disconnect())

    app.state.db_engine = None
    app.state.replica_db_engine = None

    logger.info("Databases closed")
