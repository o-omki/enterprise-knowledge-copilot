"""Retrieval evaluation runner.

Migrated from ``benchmarks/retrieval/eval_retrieval.py`` and enhanced with:
- nDCG@k computation
- Per-query timing breakdown (retrieval_ms, rerank_ms)
- Structured ``EvalResult`` output
- Configuration from ``configs/evals.yaml``
"""

from __future__ import annotations

import logging
import math
import time

from apps.evals.config import EvalConfig
from apps.evals.runners.base import BaseRunner, EvalResult
from packages.rag.reranker import RerankerService
from packages.rag.search import SearchConfig, SearchService

logger = logging.getLogger(__name__)


def _dcg(relevances: list[float], k: int) -> float:
    """Compute Discounted Cumulative Gain at rank k."""
    score = 0.0
    for i, rel in enumerate(relevances[:k]):
        score += rel / math.log2(i + 2)  # i+2 because log2(1) = 0
    return score


def _ndcg_at_k(relevances: list[float], k: int) -> float:
    """Compute normalized DCG at rank k."""
    dcg = _dcg(relevances, k)
    ideal = _dcg(sorted(relevances, reverse=True), k)
    if ideal == 0:
        return 0.0
    return dcg / ideal


class RetrievalRunner(BaseRunner):
    """Evaluates retrieval quality across dense, sparse, hybrid, and hybrid+rerank methods.

    Metrics computed per method:
    - Recall@1, Recall@5
    - MRR (Mean Reciprocal Rank)
    - nDCG@5
    - Average latency (retrieval + rerank breakdown)
    """

    name = "retrieval"

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
        methods = self.config.methods

        all_metrics: dict[str, dict[str, float]] = {}
        all_per_query: list[dict] = []

        import asyncio

        semaphore = asyncio.Semaphore(10)

        for method in methods:
            logger.info("--- Evaluating retrieval method: %s ---", method.upper())

            retrieval_method = "hybrid" if method == "hybrid+rerank" else method
            fetch_limit = k * multiplier if method == "hybrid+rerank" else k

            async def _process_item(item):
                async with semaphore:
                    query = item["question"]
                    expected = item["expected_source"]

                    try:
                        # Retrieval phase
                        t0 = time.perf_counter()
                        results = await self.search_service.search(
                            query=query,
                            limit=fetch_limit,
                            method=retrieval_method,
                        )
                        retrieval_ms = (time.perf_counter() - t0) * 1000

                        # Rerank phase
                        rerank_ms = 0.0
                        if method == "hybrid+rerank":
                            t1 = time.perf_counter()
                            results = await self.reranker_service.arerank(
                                query=query,
                                results=results,
                                top_k=k,
                            )
                            rerank_ms = (time.perf_counter() - t1) * 1000
                    except Exception as e:
                        logger.error("Search failed for query '%s': %s", query[:50], e)
                        return {
                            "method": method,
                            "query": query,
                            "expected_source": expected,
                            "rank": None,
                            "status": "error",
                            "error": str(e),
                            "retrieval_ms": 0.0,
                            "rerank_ms": 0.0,
                            "hits_at_1": 0,
                            "hits_at_5": 0,
                            "rr": 0.0,
                            "ndcg": 0.0,
                        }

                    # Score: find rank of expected source
                    rank = None
                    relevances: list[float] = []
                    for i, res in enumerate(results):
                        if expected in res.source:
                            if rank is None:
                                rank = i + 1
                            relevances.append(1.0)
                        else:
                            relevances.append(0.0)

                    hits_at_1 = 1 if rank == 1 else 0
                    hits_at_5 = 1 if rank is not None and rank <= k else 0
                    rr = 1.0 / rank if rank is not None else 0.0
                    ndcg = _ndcg_at_k(relevances, k)

                    return {
                        "method": method,
                        "query": query,
                        "expected_source": expected,
                        "rank": rank,
                        "status": "hit" if rank is not None else "miss",
                        "retrieval_ms": round(retrieval_ms, 2),
                        "rerank_ms": round(rerank_ms, 2),
                        "hits_at_1": hits_at_1,
                        "hits_at_5": hits_at_5,
                        "rr": rr,
                        "ndcg": ndcg,
                    }

            tasks = [_process_item(item) for item in dataset]
            results = await asyncio.gather(*tasks)

            rr_sum = 0.0
            hits_at_1 = 0
            hits_at_5 = 0
            ndcg_sum = 0.0
            total_retrieval_ms = 0.0
            total_rerank_ms = 0.0

            for res in results:
                rr_sum += res.pop("rr")
                hits_at_1 += res.pop("hits_at_1")
                hits_at_5 += res.pop("hits_at_5")
                ndcg_sum += res.pop("ndcg")
                total_retrieval_ms += res["retrieval_ms"]
                total_rerank_ms += res["rerank_ms"]
                all_per_query.append(res)

            n = len(dataset)
            all_metrics[method] = {
                "recall_at_1": round(hits_at_1 / n, 4) if n else 0,
                "recall_at_5": round(hits_at_5 / n, 4) if n else 0,
                "mrr": round(rr_sum / n, 4) if n else 0,
                "ndcg_at_5": round(ndcg_sum / n, 4) if n else 0,
                "avg_retrieval_ms": round(total_retrieval_ms / n, 1) if n else 0,
                "avg_rerank_ms": round(total_rerank_ms / n, 1) if n else 0,
                "avg_total_ms": round((total_retrieval_ms + total_rerank_ms) / n, 1) if n else 0,
            }

            logger.info(
                "%s — Recall@1=%.4f  Recall@5=%.4f  MRR=%.4f  nDCG@5=%.4f  Latency=%.1fms",
                method,
                all_metrics[method]["recall_at_1"],
                all_metrics[method]["recall_at_5"],
                all_metrics[method]["mrr"],
                all_metrics[method]["ndcg_at_5"],
                all_metrics[method]["avg_total_ms"],
            )

        # Flatten metrics for the top-level EvalResult
        flat_metrics: dict[str, float] = {}
        for method, scores in all_metrics.items():
            for metric_name, value in scores.items():
                flat_metrics[f"{method}/{metric_name}"] = value

        timings: dict[str, float] = {}
        for method, scores in all_metrics.items():
            timings[f"{method}/avg_retrieval_ms"] = scores["avg_retrieval_ms"]
            timings[f"{method}/avg_rerank_ms"] = scores["avg_rerank_ms"]

        return EvalResult(
            runner_name=self.name,
            timestamp=self.now_iso(),
            dataset_path=self.config.datasets.retrieval,
            config_snapshot={
                "top_k": k,
                "candidate_multiplier": multiplier,
                "methods": methods,
                "seed": self.config.seed,
            },
            metrics=flat_metrics,
            per_query=all_per_query,
            timings=timings,
            metadata=self.capture_metadata(),
        )
