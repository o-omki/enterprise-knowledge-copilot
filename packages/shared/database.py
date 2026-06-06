import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# Retrieve PostgreSQL DSN and convert to use asyncpg driver if necessary
postgres_dsn = os.getenv(
    "POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/knowledge_copilot"
)
if postgres_dsn.startswith("postgresql://") and not postgres_dsn.startswith(
    "postgresql+asyncpg://"
):
    postgres_dsn = postgres_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async engine
engine = create_async_engine(
    postgres_dsn,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# Session factory for async sessions
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


Base = declarative_base()


# FastAPI dependency to yield database sessions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
