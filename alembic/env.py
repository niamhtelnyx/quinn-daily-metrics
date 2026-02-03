from logging.config import fileConfig
from os import getenv

from alembic.script import ScriptDirectory
from sqlalchemy import engine_from_config, pool

from alembic import context
from my_agentic_serviceservice_order_specialist.platform.database.tables import db_metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = db_metadata

postgres_host = getenv("PRIMARY_DB__HOST", default="127.0.0.1")
postgres_port = getenv("PRIMARY_DB__PORT", default=5432)
postgres_user = getenv("PRIMARY_DB__USER", default="postgres")
postgres_password = getenv("PRIMARY_DB__PASSWORD", default="postgres")
postgres_database = getenv("PRIMARY_DB__DATABASE", default="my_agentic_serviceservice_order_specialist")

url = f"postgresql+psycopg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_database}"
config.set_main_option("sqlalchemy.url", url)


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object, name, type_, reflected, compare_to):
    """
    Skip langgraph checkpoint tables from being created
    """
    if type_ == "table" and name and (name.startswith("checkpoint") or name.startswith("a2a")):
        return False
    return True


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


def process_revision_directives(context, revision, directives):
    """
    The following code was adapted from an answer to the stack overflow question "Is
    there any way to generate sequential Revision IDs in Alembic?" in the post found
    here:
        - https://stackoverflow.com/q/53303778/8134518

    The source code was written by Dima Boger, whose profile can be found at:
        - https://stackoverflow.com/users/8324474/dima-boger

    Please note that modifications have been to the author's code; the original
    version can be found in the author's response here:
        - https://stackoverflow.com/a/67398484/8134518
    """
    scripts = ScriptDirectory.from_config(context.config)
    if (head := scripts.get_current_head()) is None:
        next_rev_id = 1
    else:
        next_rev_id = int(head) + 1
    target = directives[0]
    target.rev_id = f"{next_rev_id:04}"


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
