from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from packages.llm_serving.types import LLMRequest, LLMResponse, LLMStreamChunk


class BaseLLMBackend(ABC):
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        pass
        yield
