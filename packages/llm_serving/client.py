import time
from collections.abc import AsyncGenerator

import redis.asyncio as redis

from packages.llm_serving.backends.base import BaseLLMBackend
from packages.llm_serving.backends.openai_compatible import OpenAICompatibleBackend
from packages.llm_serving.backends.vertex_ai import VertexAIBackend
from packages.llm_serving.circuit_breaker import CircuitBreaker
from packages.llm_serving.config import LLMServingConfig
from packages.llm_serving.cost_tracker import CostTracker
from packages.llm_serving.metrics import (
    error_counter,
    latency_histogram,
    request_counter,
    token_counter,
)
from packages.llm_serving.response_cache import ResponseCache
from packages.llm_serving.types import LLMRequest, LLMResponse, LLMStreamChunk


class LLMClient:
    def __init__(
        self,
        config: LLMServingConfig | None = None,
        redis_client: redis.Redis | None = None,
        cost_tracker: CostTracker | None = None,
    ):
        self.config = config or LLMServingConfig()
        self.cost_tracker = cost_tracker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.circuit_breaker_failure_threshold,
            recovery_timeout=self.config.circuit_breaker_recovery_timeout_sec,
        )
        self.cache = ResponseCache(config=self.config, redis_client=redis_client)
        self.backend = self._init_backend()

    def _init_backend(self) -> BaseLLMBackend:
        if self.config.default_backend == "openai":
            return OpenAICompatibleBackend(self.config)
        return VertexAIBackend(self.config)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        request_counter.add(1, {"model": request.model, "backend": self.config.default_backend})

        cached_response = await self.cache.get(request)
        if cached_response:
            return cached_response

        start_time = time.time()
        try:
            response = await self.circuit_breaker.execute(self.backend.generate, request)
            latency = time.time() - start_time
            latency_histogram.record(latency, {"model": request.model})

            if response.usage:
                token_counter.add(response.usage.total_tokens, {"model": request.model})
                if self.cost_tracker:
                    self.cost_tracker.calculate_cost(request.model, response.usage)

            await self.cache.set(request, response)
            return response
        except Exception as e:
            error_counter.add(1, {"model": request.model, "error_type": type(e).__name__})
            raise e

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        request_counter.add(
            1, {"model": request.model, "backend": self.config.default_backend, "stream": True}
        )

        start_time = time.time()
        try:
            stream = self.circuit_breaker.execute_stream(self.backend.generate_stream, request)
            async for chunk in stream:
                if chunk.usage:
                    token_counter.add(chunk.usage.total_tokens, {"model": request.model})
                    if self.cost_tracker:
                        self.cost_tracker.calculate_cost(request.model, chunk.usage)
                yield chunk
            latency = time.time() - start_time
            latency_histogram.record(latency, {"model": request.model})
        except Exception as e:
            error_counter.add(1, {"model": request.model, "error_type": type(e).__name__})
            raise e
