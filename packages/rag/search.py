import time

import structlog
from fastembed import SparseTextEmbedding
from google import genai
from google.genai import types
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from packages.observability import get_tracer
from packages.observability.metrics import (
    retrieval_duration,
    retrieval_hit_quality,
    retrieval_result_count,
    retrieval_total,
)

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


class SearchConfig(BaseSettings):
    qdrant_url: str = "http://localhost:6333"
    vector_size: int = 768

    project_id: str = Field(alias="GCP_PROJECT_ID", default="")
    location: str = Field(alias="GCP_LOCATION", default="global")
    embedding_model_name: str = Field(alias="GCP_EMBEDDING_MODEL", default="gemini-embedding-2")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class SearchResult(BaseSettings):
    text: str
    source: str
    score: float
    diagnostics: dict = Field(default_factory=dict)
    model_config = SettingsConfigDict(arbitrary_types_allowed=True)


class SearchService:
    def __init__(self, config: SearchConfig | None = None):
        self.config = config or SearchConfig()
        self.client = AsyncQdrantClient(url=self.config.qdrant_url)
        self._genai_client = None
        self._sparse_model = None

    @property
    def sparse_model(self):
        """Lazy loader for the fastembed sparse model."""
        if self._sparse_model is None:
            self._sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        return self._sparse_model

    @property
    def genai_client(self):
        """Lazy loader for the genai client."""
        if self._genai_client is None:
            self._genai_client = genai.Client(
                vertexai=True,
                project=self.config.project_id,
                location=self.config.location,
            )
        return self._genai_client

    async def get_query_embedding(self, query: str) -> list[float]:
        """Converts user query to a vector using Vertex AI via google-genai."""
        with tracer.start_as_current_span("retrieval.embed_query") as span:
            span.set_attribute("retrieval.embedding_model", self.config.embedding_model_name)
            content = f"query: {query}"

            response = await self.genai_client.aio.models.embed_content(
                model=self.config.embedding_model_name,
                contents=content,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY", output_dimensionality=self.config.vector_size
                ),
            )
            return response.embeddings[0].values

    async def search(
        self,
        query: str,
        limit: int = 5,
        domain: str | None = None,
        doc_type: str | None = None,
        method: str = "dense",
    ) -> list[SearchResult]:
        """Performs vector search in the global collection with optional payload filtering."""
        search_start_time = time.perf_counter()
        retrieval_total.add(1, {"method": method, "domain": domain or "unknown"})
        logger.info("retrieval.started", method=method, domain=domain, doc_type=doc_type)

        collection_name = "enterprise_knowledge"

        query_vector = None
        using = None
        prefetch = None

        if method == "dense":
            query_vector = await self.get_query_embedding(query)
        elif method == "sparse":
            sparse_res = list(self.sparse_model.embed([query]))[0]
            query_vector = models.SparseVector(
                indices=sparse_res.indices.tolist(), values=sparse_res.values.tolist()
            )
            using = "sparse"
        elif method == "hybrid":
            # For hybrid, we use Qdrant's Reciprocal Rank Fusion via prefetch
            dense_vector = await self.get_query_embedding(query)
            sparse_res = list(self.sparse_model.embed([query]))[0]
            sparse_vector = models.SparseVector(
                indices=sparse_res.indices.tolist(), values=sparse_res.values.tolist()
            )
            query_vector = models.FusionQuery(fusion=models.Fusion.RRF)
            prefetch = [
                models.Prefetch(query=dense_vector, using="", limit=limit * 2),
                models.Prefetch(query=sparse_vector, using="sparse", limit=limit * 2),
            ]
        else:
            raise ValueError("Method must be 'dense', 'sparse', or 'hybrid'")

        must_conditions = []
        if domain:
            must_conditions.append(
                models.FieldCondition(key="domain", match=models.MatchValue(value=domain.lower()))
            )
        if doc_type:
            must_conditions.append(
                models.FieldCondition(
                    key="doc_type", match=models.MatchValue(value=doc_type.lower())
                )
            )

        query_filter = models.Filter(must=must_conditions) if must_conditions else None

        if method == "hybrid" and prefetch:
            for p in prefetch:
                p.filter = query_filter

        start_time = time.perf_counter()

        with tracer.start_as_current_span("retrieval.qdrant_query") as span:
            span.set_attribute("retrieval.collection", collection_name)
            span.set_attribute("retrieval.method", method)

            results = await self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                prefetch=prefetch,
                using=using,
                limit=limit,
                with_payload=True,
                query_filter=query_filter,
            )

            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            span.set_attribute("retrieval.result_count", len(results.points))
            span.set_attribute("retrieval.latency_ms", latency_ms)

        logger.info(
            "retrieval.completed",
            method=method,
            domain=domain,
            doc_type=doc_type,
            result_count=len(results.points),
            latency_ms=latency_ms,
        )

        search_duration_sec = time.perf_counter() - search_start_time
        retrieval_duration.record(search_duration_sec, {"method": method})
        retrieval_result_count.record(len(results.points), {"method": method})
        if results.points:
            retrieval_hit_quality.record(results.points[0].score, {"method": method})

        return [
            SearchResult(
                text=hit.payload.get("parent_text") or hit.payload.get("text", ""),
                source=hit.payload.get("source", "unknown"),
                score=hit.score,
                diagnostics={
                    "latency_ms": latency_ms,
                    "method": method,
                    "is_parent": bool(hit.payload.get("parent_text")),
                },
            )
            for hit in results.points
            if hit.payload
        ]
