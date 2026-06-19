import asyncio

import structlog

from packages.agents.planner import DecomposerAgent
from packages.agents.router import QueryRouter
from packages.agents.schema import QueryType
from packages.llm_serving import LLMClient
from packages.llm_serving.router import ModelRouter
from packages.llm_serving.slo import SLOConfig
from packages.observability import get_tracer
from packages.rag.generation import AnswerResponse, GenerationService
from packages.rag.reranker import RerankerService
from packages.rag.search import SearchService

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


class QueryOrchestrator:
    """Orchestrates query routing, decomposition, retrieval, and final synthesis.

    Includes distributed OpenTelemetry spans to ensure planner failures are
    observable and debuggable, showing step-by-step execution.
    """

    def __init__(
        self,
        search_service: SearchService,
        generation_service: GenerationService,
        reranker_service: RerankerService,
        llm_client: LLMClient,
        model_router: ModelRouter | None = None,
    ):
        self.search_service = search_service
        self.generation_service = generation_service
        self.reranker_service = reranker_service
        self.router = QueryRouter(llm_client=llm_client)
        self.decomposer = DecomposerAgent(llm_client=llm_client)
        self.model_router = model_router or ModelRouter()
        self.slo_config = SLOConfig()

    async def answer_query(
        self,
        query: str,
        domain: str | None = None,
        doc_type: str | None = None,
        limit: int = 5,
        method: str = "dense",
        rerank: bool = False,
        chat_history: list[dict] | None = None,
    ) -> AnswerResponse:
        """Executes the full agentic RAG loop using traces to link steps."""

        logger.info(
            "orchestrator.query.started", query=query, limit=limit, method=method, rerank=rerank
        )
        with tracer.start_as_current_span("orchestrate_query") as span:
            span.set_attribute("query", query)
            span.set_attribute("params.limit", limit)
            span.set_attribute("params.rerank", rerank)
            span.set_attribute("params.method", method)

            trace_id = format(span.get_span_context().trace_id, "032x")

            routing_decision = await self.router.route(query=query)
            logger.info(
                "orchestrator.routing.completed",
                query_type=routing_decision.query_type.value,
            )

            sub_queries = [query]
            if routing_decision.query_type in [
                QueryType.MULTI_HOP_SYNTHESIS,
                QueryType.COMPARATIVE_QUERY,
            ]:
                decomp_result = await self.decomposer.decompose(query=query)
                sub_queries = decomp_result.sub_queries
                logger.info(
                    "orchestrator.query.decomposed",
                    sub_query_count=len(sub_queries),
                    sub_queries=sub_queries,
                )

            with tracer.start_as_current_span("parallel_search_and_rerank") as agg_span:
                fetch_limit = limit * 2 if rerank else limit

                async def fetch_and_rank(sq: str):
                    with tracer.start_as_current_span("sub_query_search") as search_span:
                        search_span.set_attribute("sub_query", sq)
                        res = await self.search_service.search(
                            query=sq,
                            limit=fetch_limit,
                            domain=domain,
                            doc_type=doc_type,
                            method=method,
                        )
                        if rerank:
                            res = await self.reranker_service.arerank(
                                query=sq, results=res, top_k=limit
                            )
                        search_span.set_attribute("chunks_retrieved", len(res))
                        return res

                search_tasks = [fetch_and_rank(sq) for sq in sub_queries]
                all_results_nested = await asyncio.gather(*search_tasks)

            with tracer.start_as_current_span("aggregate_evidence") as agg_span:
                aggregated_results = []
                seen_texts = set()
                for res_list in all_results_nested:
                    for res in res_list:
                        res_text = getattr(res, "text", None) or res.model_dump().get("text")
                        if res_text and res_text not in seen_texts:
                            seen_texts.add(res_text)
                            aggregated_results.append(res)

                capped_results = aggregated_results[: limit * 2]
                agg_span.set_attribute("total_unique_chunks", len(capped_results))
                logger.info("orchestrator.search.completed", chunks_retrieved=len(capped_results))

            selected_model = self.model_router.select_model(
                routing_decision.query_type.value, self.slo_config
            )

            logger.info("orchestrator.synthesis.completed", model_name=selected_model.name)
            with tracer.start_as_current_span("synthesize_answer"):
                response = await self.generation_service.generate_answer(
                    query=query,
                    search_results=capped_results,
                    chat_history=chat_history,
                    model_override=selected_model.name,
                )

            response.metadata = {
                "trace_id": trace_id,
                "total_chunks_retrieved": len(capped_results),
            }
            return response

    async def answer_query_stream(
        self,
        query: str,
        domain: str | None = None,
        doc_type: str | None = None,
        limit: int = 5,
        method: str = "dense",
        rerank: bool = False,
    ):
        """Executes the full agentic RAG loop and streams the synthesis."""
        logger.info(
            "orchestrator.query_stream.started",
            query=query,
            limit=limit,
            method=method,
            rerank=rerank,
        )
        with tracer.start_as_current_span("orchestrate_query_stream") as span:
            span.set_attribute("query", query)
            trace_id = format(span.get_span_context().trace_id, "032x")

            routing_decision = await self.router.route(query=query)
            logger.info(
                "orchestrator.routing.completed",
                query_type=routing_decision.query_type.value,
            )

            sub_queries = [query]
            if routing_decision.query_type in [
                QueryType.MULTI_HOP_SYNTHESIS,
                QueryType.COMPARATIVE_QUERY,
            ]:
                decomp_result = await self.decomposer.decompose(query=query)
                sub_queries = decomp_result.sub_queries
                logger.info(
                    "orchestrator.query.decomposed",
                    sub_query_count=len(sub_queries),
                    sub_queries=sub_queries,
                )

            fetch_limit = limit * 2 if rerank else limit

            async def fetch_and_rank(sq: str):
                res = await self.search_service.search(
                    query=sq, limit=fetch_limit, domain=domain, doc_type=doc_type, method=method
                )
                if rerank:
                    res = await self.reranker_service.arerank(query=sq, results=res, top_k=limit)
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
            logger.info("orchestrator.search.completed", chunks_retrieved=len(capped_results))

            selected_model = self.model_router.select_model(
                routing_decision.query_type.value, self.slo_config
            )

            logger.info("orchestrator.synthesis_stream.started", model_name=selected_model.name)
            with tracer.start_as_current_span("synthesize_answer_stream"):
                async for event in self.generation_service.generate_answer_stream(
                    query=query, search_results=capped_results, model_override=selected_model.name
                ):
                    if event.get("type") == "done":
                        event["metadata"] = {
                            "trace_id": trace_id,
                            "total_chunks_retrieved": len(capped_results),
                        }
                    yield event
