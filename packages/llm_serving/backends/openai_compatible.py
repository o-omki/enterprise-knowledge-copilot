import json
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from packages.llm_serving.backends.base import BaseLLMBackend
from packages.llm_serving.config import LLMServingConfig
from packages.llm_serving.types import (
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    UsageMetadata,
)


class OpenAICompatibleBackend(BaseLLMBackend):
    def __init__(self, config: LLMServingConfig):
        self.config = config
        self._client = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_base_url,
            )
        return self._client

    def _prepare_messages(self, request: LLMRequest) -> list[dict]:
        messages = []
        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})

        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        return messages

    async def generate(self, request: LLMRequest) -> LLMResponse:
        kwargs = {
            "model": request.model,
            "messages": self._prepare_messages(request),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        if request.response_mime_type == "application/json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        text = choice.message.content or ""

        usage = UsageMetadata()
        if response.usage:
            usage.prompt_tokens = response.usage.prompt_tokens
            usage.completion_tokens = response.usage.completion_tokens
            usage.total_tokens = response.usage.total_tokens

        parsed = None
        if request.response_schema and request.response_mime_type == "application/json":
            try:
                parsed_data = json.loads(text)
                if hasattr(request.response_schema, "model_validate"):
                    parsed = request.response_schema.model_validate(parsed_data)
                else:
                    parsed = request.response_schema(**parsed_data)
            except Exception:
                pass

        return LLMResponse(
            text=text,
            usage=usage,
            parsed=parsed,
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        kwargs = {
            "model": request.model,
            "messages": self._prepare_messages(request),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        stream = await self.client.chat.completions.create(**kwargs)
        async for chunk in stream:
            text = ""
            if chunk.choices and len(chunk.choices) > 0:
                text = chunk.choices[0].delta.content or ""

            usage = None
            if chunk.usage:
                usage = UsageMetadata(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                )

            if text or usage:
                yield LLMStreamChunk(text=text, usage=usage)
