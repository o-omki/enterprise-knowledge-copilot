from collections.abc import AsyncGenerator

from google import genai
from google.genai import types as genai_types

from packages.llm_serving.backends.base import BaseLLMBackend
from packages.llm_serving.config import LLMServingConfig
from packages.llm_serving.types import (
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    UsageMetadata,
)


class VertexAIBackend(BaseLLMBackend):
    def __init__(self, config: LLMServingConfig):
        self.config = config
        self._client = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=self.config.project_id,
                location=self.config.location,
            )
        return self._client

    def _prepare_config(self, request: LLMRequest) -> dict:
        config_dict = {
            "temperature": request.temperature,
            "max_output_tokens": request.max_tokens,
        }
        if request.system_instruction:
            config_dict["system_instruction"] = request.system_instruction
        if request.response_mime_type:
            config_dict["response_mime_type"] = request.response_mime_type
        if request.response_schema:
            config_dict["response_schema"] = request.response_schema
        return config_dict

    def _prepare_contents(self, request: LLMRequest) -> list:
        contents = []
        for msg in request.messages:
            role = "model" if msg.role == "assistant" else "user"
            contents.append(
                genai_types.Content(
                    role=role,
                    parts=[genai_types.Part.from_text(text=msg.content)],
                )
            )
        return contents

    async def generate(self, request: LLMRequest) -> LLMResponse:
        response = await self.client.aio.models.generate_content(
            model=request.model,
            contents=self._prepare_contents(request),
            config=self._prepare_config(request),
        )

        usage = UsageMetadata()
        if response.usage_metadata:
            usage.prompt_tokens = response.usage_metadata.prompt_token_count or 0
            usage.completion_tokens = response.usage_metadata.candidates_token_count or 0
            usage.total_tokens = response.usage_metadata.total_token_count or 0

        return LLMResponse(
            text=response.text or "",
            usage=usage,
            parsed=getattr(response, "parsed", None),
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        response_stream = await self.client.aio.models.generate_content_stream(
            model=request.model,
            contents=self._prepare_contents(request),
            config=self._prepare_config(request),
        )
        async for chunk in response_stream:
            usage = None
            if chunk.usage_metadata:
                usage = UsageMetadata(
                    prompt_tokens=chunk.usage_metadata.prompt_token_count or 0,
                    completion_tokens=chunk.usage_metadata.candidates_token_count or 0,
                    total_tokens=chunk.usage_metadata.total_token_count or 0,
                )
            yield LLMStreamChunk(text=chunk.text or "", usage=usage)
