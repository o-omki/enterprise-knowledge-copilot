from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from packages.rag.generation import AnswerResponse, GenerationService
from packages.rag.search import SearchService

app = FastAPI(title="Enterprise Knowledge Copilot API", version="0.1.0")

search_service = SearchService()
generation_service = GenerationService()


class QueryResponse(BaseModel):
    query: str
    results: list[dict]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/search")
async def search(
    q: str, domain: str | None = None, doc_type: str | None = None, limit: int = 5
) -> QueryResponse:
    """Global retrieval endpoint with optional payload filtering for Phase 1+."""
    try:
        results = await search_service.search(
            query=q, limit=limit, domain=domain, doc_type=doc_type
        )
        return QueryResponse(query=q, results=[res.model_dump() for res in results])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ask", response_model=AnswerResponse)
async def ask(
    q: str, domain: str | None = None, doc_type: str | None = None, limit: int = 5
) -> AnswerResponse:
    """Answers a question using LLM generation and knowledge base context with citations."""
    try:
        results = await search_service.search(
            query=q, limit=limit, domain=domain, doc_type=doc_type
        )

        response = await generation_service.generate_answer(query=q, search_results=results)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
