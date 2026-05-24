import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from apps.api.app.middleware.safety import SafetyGuardrailsMiddleware
from packages.agents.orchestrator import QueryOrchestrator
from packages.observability import setup_tracing
from packages.rag.generation import AnswerResponse, GenerationService
from packages.rag.reranker import RerankerService
from packages.rag.search import SearchService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Enterprise Knowledge Copilot API", version="0.3.0")

setup_tracing(app)

guardrails_url = os.getenv("GUARDRAILS_SERVICE_URL", "http://guardrails:8001")
app.add_middleware(SafetyGuardrailsMiddleware, service_url=guardrails_url)

search_service = SearchService()
generation_service = GenerationService()
reranker_service = RerankerService()
orchestrator = QueryOrchestrator(
    search_service=search_service,
    generation_service=generation_service,
    reranker_service=reranker_service,
)


class QueryResponse(BaseModel):
    query: str
    results: list[dict]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/search")
async def search(
    q: str,
    domain: str | None = None,
    doc_type: str | None = None,
    limit: int = 5,
    method: str = "dense",
    rerank: bool = False,
) -> QueryResponse:
    """Global retrieval endpoint with optional payload filtering and reranking.

    When `rerank=true`, fetches `limit * 2` candidates from the retrieval
    stage and applies cross-encoder reranking before returning the top `limit`.
    """
    try:
        fetch_limit = limit * 2 if rerank else limit
        results = await search_service.search(
            query=q, limit=fetch_limit, domain=domain, doc_type=doc_type, method=method
        )
        if rerank:
            results = await reranker_service.arerank(query=q, results=results, top_k=limit)
        return QueryResponse(query=q, results=[res.model_dump() for res in results])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ask", response_model=AnswerResponse)
async def ask(
    q: str,
    domain: str | None = None,
    doc_type: str | None = None,
    limit: int = 5,
    method: str = "dense",
    rerank: bool = False,
) -> AnswerResponse:
    """Answers a question using LLM generation and knowledge base context with citations.

    Acts as an agentic orchestration endpoint capable of handling complex multi-hop queries
    by routing them through a planner, decomposing them into parallel sub-queries, and
    aggregating the results before generation.
    """
    try:
        logger.info(f"Processing query: {q}")
        response = await orchestrator.answer_query(
            query=q,
            domain=domain,
            doc_type=doc_type,
            limit=limit,
            method=method,
            rerank=rerank,
        )
        return response

    except Exception as e:
        logger.error(f"Error in ask endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
