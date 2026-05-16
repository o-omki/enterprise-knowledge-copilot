from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from packages.rag.generation import AnswerResponse, GenerationService
from packages.rag.reranker import RerankerService
from packages.rag.search import SearchService

app = FastAPI(title="Enterprise Knowledge Copilot API", version="0.2.0")

search_service = SearchService()
generation_service = GenerationService()
reranker_service = RerankerService()


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

    When `rerank=true`, applies cross-encoder reranking on a broader candidate
    set before passing evidence to the generation step.
    """
    try:
        fetch_limit = limit * 2 if rerank else limit
        results = await search_service.search(
            query=q, limit=fetch_limit, domain=domain, doc_type=doc_type, method=method
        )
        if rerank:
            results = await reranker_service.arerank(query=q, results=results, top_k=limit)
        response = await generation_service.generate_answer(query=q, search_results=results)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
