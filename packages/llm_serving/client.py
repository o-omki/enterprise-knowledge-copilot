import time
from collections.abc import AsyncGenerator

import redis.asyncio as redis
import structlog

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

logger = structlog.get_logger(__name__)


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
        logger.info("llm.request.started", model=request.model, backend=self.config.default_backend)
        request_counter.add(1, {"model": request.model, "backend": self.config.default_backend})

        cached_response = await self.cache.get(request)
        if cached_response:
            logger.info(
                "llm.request.cached", model=request.model, backend=self.config.default_backend
            )
            return cached_response

        start_time = time.time()
        try:
            response = await self.circuit_breaker.execute(self.backend.generate, request)
            latency = time.time() - start_time
            latency_histogram.record(latency, {"model": request.model})

            token_count = response.usage.total_tokens if response.usage else 0
            if response.usage:
                token_counter.add(response.usage.total_tokens, {"model": request.model})
                if self.cost_tracker:
                    self.cost_tracker.calculate_cost(request.model, response.usage)

            logger.info(
                "llm.request.completed",
                model=request.model,
                backend=self.config.default_backend,
                latency_s=latency,
                token_count=token_count,
            )
            await self.cache.set(request, response)
            return response
        except Exception as e:
            latency = time.time() - start_time
            logger.error(
                "llm.request.failed",
                model=request.model,
                backend=self.config.default_backend,
                error=str(e),
                latency_s=latency,
                exc_info=True,
            )
            error_counter.add(1, {"model": request.model, "error_type": type(e).__name__})
            raise e

    async def generate_stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        logger.info(
            "llm.request.started",
            model=request.model,
            backend=self.config.default_backend,
            stream=True,
        )
        request_counter.add(
            1, {"model": request.model, "backend": self.config.default_backend, "stream": True}
        )

        start_time = time.time()
        try:
            stream = self.circuit_breaker.execute_stream(self.backend.generate_stream, request)
            total_tokens = 0
            async for chunk in stream:
                if chunk.usage:
                    total_tokens += chunk.usage.total_tokens
                    token_counter.add(chunk.usage.total_tokens, {"model": request.model})
                    if self.cost_tracker:
                        self.cost_tracker.calculate_cost(request.model, chunk.usage)
                yield chunk
            latency = time.time() - start_time
            logger.info(
                "llm.request.completed",
                model=request.model,
                backend=self.config.default_backend,
                latency_s=latency,
                token_count=total_tokens,
                stream=True,
            )
            latency_histogram.record(latency, {"model": request.model})
        except Exception as e:
            latency = time.time() - start_time
            logger.error(
                "llm.request.failed",
                model=request.model,
                backend=self.config.default_backend,
                error=str(e),
                latency_s=latency,
                stream=True,
                exc_info=True,
            )
            error_counter.add(1, {"model": request.model, "error_type": type(e).__name__})
            raise e
