from typing import Literal

from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: str
    status: str = "queued"
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    result: dict | None = None
    error: str | None = None


class AskRequest(BaseModel):
    query: str
    domain: str | None = None
    doc_type: str | None = None
    limit: int = 5
    method: str = "dense"
    rerank: bool = False
    stream: bool = False
    session_id: str | None = None


class Citation(BaseModel):
    id: int
    source: str
    snippet: str


class QueryMetadata(BaseModel):
    trace_id: str | None = None
    processing_time_ms: int | None = None
    total_chunks_retrieved: int | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    metadata: QueryMetadata | None = None
    session_id: str | None = None
    message_id: str | None = None


class UserRegister(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str


class FeedbackRequest(BaseModel):
    session_id: str
    rating: Literal["up", "down"]
    comment: str | None = None


class FeedbackResponse(BaseModel):
    id: str
    message_id: str
    session_id: str
    rating: Literal["up", "down"]
    comment: str | None = None
    created_at: str | None = None


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: list[Citation] | None = None
    created_at: str | None = None
    feedback: FeedbackResponse | None = None


class SessionResponse(BaseModel):
    id: str
    last_active: str | None = None
    first_message: str | None = None


class SearchRequest(BaseModel):
    query: str
    domain: str | None = None
    doc_type: str | None = None
    limit: int = 5
    method: str = "dense"
    rerank: bool = False


class SearchResponse(BaseModel):
    query: str
    results: list[dict]
