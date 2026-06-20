"""
Cross-encoder reranker for Phase 3.

Takes the top-k candidates from the retrieval stage and re-scores each
(query, passage) pair using a cross-encoder model. This is a two-stage
retrieval pattern:
  1. Retrieve a broad candidate set (e.g., top 20) for high recall.
  2. Rerank to promote the most relevant result to the top of the list.

The model runs synchronously on CPU. The public `arerank()` method wraps
the blocking call in `asyncio.to_thread` so it is safe to await from an
async FastAPI handler without blocking the event loop.
"""

import asyncio
import time

import structlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sentence_transformers import CrossEncoder

from packages.observability import get_tracer
from packages.observability.metrics import (
    reranking_candidate_count,
    reranking_duration,
    reranking_total,
)
from packages.rag.search import SearchResult

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


class RerankerConfig(BaseSettings):
    """Configuration for the cross-encoder reranker.

    Controlled via environment variables or the .env file.

    - RERANKER_MODEL: HuggingFace model id (default: ms-marco MiniLM, CPU-friendly).
    - RERANKER_ENABLED: Set to "false" to disable reranking globally.
    """

    model_name: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L6-v2",
        alias="RERANKER_MODEL",
    )
    enabled: bool = Field(default=True, alias="RERANKER_ENABLED")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class RerankerService:
    """Wraps a cross-encoder model and exposes sync and async rerank methods.

    The cross-encoder model is loaded lazily on first use to avoid slowing
    down application startup when reranking is disabled.
    """

    def __init__(self, config: RerankerConfig | None = None) -> None:
        self.config = config or RerankerConfig()
        self._model: CrossEncoder | None = None
        self._semaphore = asyncio.Semaphore(4)

    @property
    def model(self) -> CrossEncoder:
        """Lazy-load the cross-encoder model (downloaded once, then cached)."""
        if self._model is None:
            logger.info("reranker.loading_model", model_name=self.config.model_name)
            self._model = CrossEncoder(self.config.model_name)
            logger.info("reranker.model_loaded", model_name=self.config.model_name)
        return self._model

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """Re-score `results` against `query` and return the top `top_k` by score.

        Args:
            query: The original user query.
            results: Candidate search results from the retrieval stage.
            top_k: How many results to return after reranking.

        Returns:
            Up to `top_k` results sorted by descending cross-encoder score.
            Each result's `diagnostics` dict gains a `rerank_score` key.
        """

        model_name = self.config.model_name
        reranking_total.add(1, {"model": model_name})
        reranking_candidate_count.record(len(results), {"model": model_name})
        start_time = time.perf_counter()

        with tracer.start_as_current_span("reranking.score") as span:
            span.set_attribute("reranking.candidate_count", len(results))
            span.set_attribute("reranking.top_k", top_k)
            span.set_attribute("reranking.model", model_name)

            logger.info("reranking.started", candidate_count=len(results), top_k=top_k)
            pairs = [(query, r.text) for r in results]

            start = time.perf_counter()
            scores: list[float] = list(self.model.predict(pairs))
            latency_ms = round((time.perf_counter() - start) * 1000, 2)

            span.set_attribute("reranking.latency_ms", latency_ms)

        logger.info(
            "reranking.completed",
            candidate_count=len(results),
            top_k=top_k,
            latency_ms=latency_ms,
        )

        duration_sec = time.perf_counter() - start_time
        reranking_duration.record(duration_sec, {"model": model_name})

        for result, score in zip(results, scores):
            result.diagnostics["rerank_score"] = round(float(score), 4)
            result.diagnostics["rerank_latency_ms"] = latency_ms

        ranked = sorted(
            zip(scores, results),
            key=lambda pair: pair[0],
            reverse=True,
        )
        return [r for _, r in ranked[:top_k]]

    async def arerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """Async wrapper around `rerank()`.

        Runs the blocking cross-encoder inference in a thread pool so it does
        not stall the FastAPI event loop.
        """
        if not self.config.enabled:
            logger.info(
                "reranking.disabled",
                top_k=top_k,
                candidate_count=len(results),
            )
            return results[:top_k]

        async with self._semaphore:
            return await asyncio.to_thread(self.rerank, query, results, top_k)
