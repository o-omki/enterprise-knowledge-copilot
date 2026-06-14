import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.database import Base


class User(Base):
    """Registered users capable of logging into the UI via JWT."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )


class ApiKey(Base):
    """API Keys for clients accessing the enterprise knowledge copilot."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="api_key", cascade="all, delete-orphan"
    )


class Session(Base):
    """Chat sessions tracking conversations and active histories."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    api_key: Mapped[Optional["ApiKey"]] = relationship("ApiKey", back_populates="sessions")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    feedback: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    """Messages exchanged within a chat session."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    session: Mapped["Session"] = relationship("Session", back_populates="messages")
    feedback: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="message", cascade="all, delete-orphan"
    )


class Feedback(Base):
    """User feedback (thumbs up/down and optional comments) on generated messages."""

    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[str] = mapped_column(String(10), nullable=False)  # "up" or "down"
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    session: Mapped["Session"] = relationship("Session", back_populates="feedback")
    message: Mapped["Message"] = relationship("Message", back_populates="feedback")
