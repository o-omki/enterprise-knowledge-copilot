import uuid
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Literal, cast

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.rag.generation import Citation
from packages.shared.models import ChatMessage
from packages.shared.orm_models import Message as ORMMessage
from packages.shared.orm_models import Session as ORMSession


class SessionManager:
    """Manages chat sessions and conversation history using Redis and PostgreSQL."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None

    @property
    def redis(self) -> Redis:
        """Lazy loader for Redis async client."""
        if self._redis is None:
            self._redis = Redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def _get_redis_key(self, session_id: str) -> str:
        return f"session:{session_id}:messages"

    async def create_session(self, db: AsyncSession, api_key_id: str | None = None) -> str:
        """Creates a new session in PostgreSQL."""
        session_id = str(uuid.uuid4())
        orm_session = ORMSession(
            id=session_id,
            api_key_id=api_key_id,
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
        )
        db.add(orm_session)
        await db.commit()
        return session_id

    async def get_active_history(
        self, db: AsyncSession, session_id: str, limit: int = 10
    ) -> list[ChatMessage]:
        """Reads the last N messages from Redis. Fallbacks to PG if cache is empty (cache-aside)."""
        redis_key = self._get_redis_key(session_id)

        # Check if cache exists in Redis
        list_len = await cast(Awaitable[int], self.redis.llen(redis_key))
        if list_len > 0:
            # Fetch last N items
            raw_msgs = await self.redis.lrange(redis_key, -limit, -1)
            messages = []
            for m in raw_msgs:
                messages.append(ChatMessage.model_validate_json(m))
            return messages

        # Cache miss: load from PostgreSQL
        messages = await self.get_full_history(db, session_id)
        if messages:
            # Populate Redis cache sequentially
            pipeline = self.redis.pipeline()
            for msg in messages:
                pipeline.rpush(redis_key, msg.model_dump_json())
            pipeline.expire(redis_key, 86400)  # 24 hours TTL
            await pipeline.execute()

            return messages[-limit:]

        return []

    async def append_message(
        self,
        db: AsyncSession,
        session_id: str,
        role: Literal["user", "assistant"],
        content: str,
        citations: list[Citation] | None = None,
        trace_id: str | None = None,
    ) -> ChatMessage:
        """Appends a new message to the active session cache and persists to DB."""
        message_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        dto = ChatMessage(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            citations=citations,
            trace_id=trace_id,
            created_at=now,
        )

        # Push to Redis active history
        redis_key = self._get_redis_key(session_id)
        await self.redis.rpush(redis_key, dto.model_dump_json())
        await self.redis.expire(redis_key, 86400)  # Reset sliding 24 hours TTL

        # Persist to PostgreSQL
        citations_data = [c.model_dump() for c in citations] if citations else None
        orm_message = ORMMessage(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            citations_json=citations_data,
            trace_id=trace_id,
            created_at=now,
        )
        db.add(orm_message)

        # Update parent session activity timestamp
        query = select(ORMSession).where(ORMSession.id == session_id)
        result = await db.execute(query)
        orm_session = result.scalar_one_or_none()
        if orm_session:
            orm_session.last_active = now

        await db.commit()
        return dto

    async def get_full_history(self, db: AsyncSession, session_id: str) -> list[ChatMessage]:
        """Retrieves full conversation history from PostgreSQL."""
        query = (
            select(ORMMessage)
            .where(ORMMessage.session_id == session_id)
            .order_by(ORMMessage.created_at.asc())
        )
        result = await db.execute(query)
        orm_messages = result.scalars().all()

        messages = []
        for om in orm_messages:
            cits = None
            if om.citations_json:
                cits = [Citation(**c) for c in om.citations_json]

            created_at_tz = om.created_at
            if created_at_tz.tzinfo is None:
                created_at_tz = created_at_tz.replace(tzinfo=UTC)

            messages.append(
                ChatMessage(
                    id=om.id,
                    session_id=om.session_id,
                    role=om.role,
                    content=om.content,
                    citations=cits,
                    trace_id=om.trace_id,
                    created_at=created_at_tz,
                )
            )
        return messages

    async def archive_session(self, session_id: str):
        """Removes the session from fast Redis storage. PG history remains untouched."""
        redis_key = self._get_redis_key(session_id)
        await self.redis.delete(redis_key)
