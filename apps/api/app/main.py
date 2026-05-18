import asyncio
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from packages.agents import DecomposerAgent, QueryRouter, QueryType
from packages.observability import setup_tracing
from packages.rag.generation import AnswerResponse, GenerationService
from packages.rag.reranker import RerankerService
from packages.rag.search import SearchService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Enterprise Knowledge Copilot API", version="0.3.0")

# Set up tracing (auto-instruments FastAPI)
setup_tracing(app)

search_service = SearchService()
generation_service = GenerationService()
reranker_service = RerankerService()
query_router = QueryRouter()
decomposer = DecomposerAgent()


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

        # Step 1: Route the query
        routing_decision = await query_router.route(query=q)
        logger.info(
            f"Routing decision: {routing_decision.query_type.value} | "
            f"Reasoning: {routing_decision.reasoning}"
        )

        sub_queries = [q]
        if routing_decision.query_type in [
            QueryType.MULTI_HOP_SYNTHESIS,
            QueryType.COMPARATIVE_QUERY,
        ]:
            decomp_result = await decomposer.decompose(query=q)
            sub_queries = decomp_result.sub_queries
            logger.info(f"Decomposed into {len(sub_queries)} sub-queries: {sub_queries}")

        # Step 2: Parallel retrieval for all sub-queries
        fetch_limit = limit * 2 if rerank else limit

        async def fetch_and_rank(sq: str):
            logger.info(f"Searching for sub-query: {sq}")
            res = await search_service.search(
                query=sq, limit=fetch_limit, domain=domain, doc_type=doc_type, method=method
            )
            if rerank:
                res = await reranker_service.arerank(query=sq, results=res, top_k=limit)
            return res

        search_tasks = [fetch_and_rank(sq) for sq in sub_queries]
        all_results_nested = await asyncio.gather(*search_tasks)

        aggregated_results = []
        seen_texts = set()
        for res_list in all_results_nested:
            for res in res_list:
                res_text = getattr(res, "text", None) or res.model_dump().get("text")
                if res_text and res_text not in seen_texts:
                    seen_texts.add(res_text)
                    aggregated_results.append(res)

        capped_results = aggregated_results[: limit * 2]
        logger.info(f"Aggregated {len(capped_results)} unique chunks to send to Generation.")

        response = await generation_service.generate_answer(query=q, search_results=capped_results)
        return response

    except Exception as e:
        logger.error(f"Error in ask endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
