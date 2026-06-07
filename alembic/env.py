import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Import our ORM Base metadata for autogenerate support
from packages.shared.orm_models import Base

target_metadata = Base.metadata

# Retrieve configuration object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Dynamically construct database URL from environment
postgres_dsn = os.getenv(
    "POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/knowledge_copilot"
)
if postgres_dsn.startswith("postgresql://") and not postgres_dsn.startswith(
    "postgresql+asyncpg://"
):
    postgres_dsn = postgres_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

config.set_main_option("sqlalchemy.url", postgres_dsn)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_async_engine(
        postgres_dsn,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
