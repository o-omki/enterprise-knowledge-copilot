"""Reranking evaluation runner.

Isolates the reranking stage to measure:
- Top-k relevance improvement (before vs after rerank)
- Latency overhead per query
- Score distribution shift analysis
"""

from __future__ import annotations

import logging
import time

from apps.evals.config import EvalConfig
from apps.evals.runners.base import BaseRunner, EvalResult
from packages.rag.reranker import RerankerService
from packages.rag.search import SearchConfig, SearchService

logger = logging.getLogger(__name__)


class RerankingRunner(BaseRunner):
    """Evaluates the isolated impact of cross-encoder reranking.

    For each query, compares the rank of the expected source before and after
    reranking to quantify the lift. Also measures reranking latency overhead.
    """

    name = "reranking"

    def __init__(
        self,
        config: EvalConfig,
        search_service: SearchService | None = None,
        reranker_service: RerankerService | None = None,
    ) -> None:
        super().__init__(config)
        self.search_service = search_service or SearchService(SearchConfig())
        self.reranker_service = reranker_service or RerankerService()

    async def run(self) -> EvalResult:
        dataset = self.load_dataset(self.config.datasets.retrieval)
        k = self.config.top_k
        multiplier = self.config.candidate_multiplier

        rank_improvements = 0
        rank_regressions = 0
        rank_unchanged = 0
        total_rerank_ms = 0.0
        per_query: list[dict] = []

        pre_hits_at_1 = 0
        post_hits_at_1 = 0
        pre_rr_sum = 0.0
        post_rr_sum = 0.0

        import asyncio

        semaphore = asyncio.Semaphore(10)

        async def _process_item(item):
            async with semaphore:
                query = item["question"]
                expected = item["expected_source"]

                try:
                    # Retrieve broad candidate set using hybrid
                    results = await self.search_service.search(
                        query=query,
                        limit=k * multiplier,
                        method="hybrid",
                    )

                    # Rank before reranking (capped to top_k)
                    pre_rank = None
                    for i, res in enumerate(results[:k]):
                        if expected in res.source:
                            pre_rank = i + 1
                            break

                    # Rerank
                    t0 = time.perf_counter()
                    reranked = await self.reranker_service.arerank(
                        query=query,
                        results=results,
                        top_k=k,
                    )
                    rerank_ms = (time.perf_counter() - t0) * 1000

                    # Rank after reranking
                    post_rank = None
                    for i, res in enumerate(reranked):
                        if expected in res.source:
                            post_rank = i + 1
                            break

                    # Collect rerank scores for distribution analysis
                    rerank_scores = [r.diagnostics.get("rerank_score", 0.0) for r in reranked]

                    return {
                        "query": query,
                        "expected_source": expected,
                        "pre_rank": pre_rank,
                        "post_rank": post_rank,
                        "rank_delta": ((pre_rank or k + 1) - (post_rank or k + 1)),
                        "rerank_ms": round(rerank_ms, 2),
                        "top_rerank_score": round(max(rerank_scores), 4) if rerank_scores else 0,
                        "min_rerank_score": round(min(rerank_scores), 4) if rerank_scores else 0,
                        "status": "ok",
                    }

                except Exception as e:
                    logger.error("Reranking eval failed for query '%s': %s", query[:50], e)
                    return {
                        "query": query,
                        "expected_source": expected,
                        "status": "error",
                        "error": str(e),
                        "pre_rank": None,
                        "post_rank": None,
                        "rerank_ms": 0.0,
                    }

        tasks = [_process_item(item) for item in dataset]
        results = await asyncio.gather(*tasks)

        for res in results:
            pre_rank = res.get("pre_rank")
            post_rank = res.get("post_rank")

            if res.get("status") == "ok":
                # Track improvements
                if pre_rank is not None and post_rank is not None:
                    if post_rank < pre_rank:
                        rank_improvements += 1
                    elif post_rank > pre_rank:
                        rank_regressions += 1
                    else:
                        rank_unchanged += 1
                elif pre_rank is None and post_rank is not None:
                    rank_improvements += 1
                elif pre_rank is not None and post_rank is None:
                    rank_regressions += 1

                if pre_rank is not None:
                    pre_rr_sum += 1.0 / pre_rank
                    if pre_rank == 1:
                        pre_hits_at_1 += 1

                if post_rank is not None:
                    post_rr_sum += 1.0 / post_rank
                    if post_rank == 1:
                        post_hits_at_1 += 1

            total_rerank_ms += res.get("rerank_ms", 0.0)

            per_query.append(res)

        n = len(dataset)
        metrics = {
            "pre_rerank_recall_at_1": round(pre_hits_at_1 / n, 4) if n else 0,
            "post_rerank_recall_at_1": round(post_hits_at_1 / n, 4) if n else 0,
            "recall_at_1_lift": round((post_hits_at_1 - pre_hits_at_1) / n, 4) if n else 0,
            "pre_rerank_mrr": round(pre_rr_sum / n, 4) if n else 0,
            "post_rerank_mrr": round(post_rr_sum / n, 4) if n else 0,
            "mrr_lift": round((post_rr_sum - pre_rr_sum) / n, 4) if n else 0,
            "rank_improvements": rank_improvements,
            "rank_regressions": rank_regressions,
            "rank_unchanged": rank_unchanged,
            "avg_rerank_ms": round(total_rerank_ms / n, 1) if n else 0,
        }

        return EvalResult(
            runner_name=self.name,
            timestamp=self.now_iso(),
            dataset_path=self.config.datasets.retrieval,
            config_snapshot={
                "top_k": k,
                "candidate_multiplier": multiplier,
                "seed": self.config.seed,
            },
            metrics=metrics,
            per_query=per_query,
            timings={"total_rerank_ms": round(total_rerank_ms, 1)},
            metadata=self.capture_metadata(),
        )
