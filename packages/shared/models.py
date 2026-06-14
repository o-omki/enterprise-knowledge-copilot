from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from packages.rag.generation import Citation


class ChatMessage(BaseModel):
    """Pydantic model representing a chat message with serializable structures."""

    id: str
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    citations: list[Citation] | None = None
    trace_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionInfo(BaseModel):
    """Pydantic model representing session metadata."""

    id: str
    api_key_id: str | None = None
    created_at: datetime
    last_active: datetime

    model_config = ConfigDict(from_attributes=True)
