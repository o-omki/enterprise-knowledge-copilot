from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant"]


class LLMMessage(BaseModel):
    role: Role
    content: str


class UsageMetadata(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMRequest(BaseModel):
    messages: list[LLMMessage]
    model: str
    temperature: float = 0.2
    max_tokens: int = 2048
    system_instruction: str | None = None
    response_mime_type: str | None = None
    response_schema: Any | None = None


class LLMResponse(BaseModel):
    text: str
    usage: UsageMetadata = Field(default_factory=UsageMetadata)
    parsed: Any | None = None


class LLMStreamChunk(BaseModel):
    text: str
    usage: UsageMetadata | None = None
