import asyncio
import logging
import sys
from os import getenv

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine

postgres_host = getenv("PRIMARY_DB__HOST", default="127.0.0.1")
postgres_port = getenv("PRIMARY_DB__PORT", default=5432)
postgres_user = getenv("PRIMARY_DB__USER", default="postgres")
postgres_password = getenv("PRIMARY_DB__PASSWORD", default="postgres")
postgres_database = getenv("PRIMARY_DB__DATABASE", default="my_agentic_serviceservice_order_specialist")

CONNECTION_DSN = """postgresql+psycopg_async://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"""

CREATE_DATABASE = """
CREATE DATABASE {postgres_db};
""".strip()


async def execute_command(cursor, command):
    try:
        await cursor.execute(command)
    except Exception as e:
        logging.error(e)


async def create_database():
    dsn = CONNECTION_DSN.format(
        postgres_user=postgres_user,
        postgres_password=postgres_password,
        postgres_db="postgres",
        postgres_host=postgres_host,
        postgres_port=postgres_port,
    )

    engine = create_async_engine(
        dsn, isolation_level="AUTOCOMMIT"
    )  # to disable autobegin transaction

    async with engine.connect() as conn:
        try:
            await conn.execute(
                text(CREATE_DATABASE.format(postgres_db=postgres_database)),
            )
        except ProgrammingError as e:
            print("There was an error creating the database: ", e)

    await engine.dispose()


def main():
    loop = asyncio.get_event_loop()
    task = loop.create_task(create_database())
    loop.run_until_complete(task)


if __name__ == "__main__":
    sys.exit(main())
