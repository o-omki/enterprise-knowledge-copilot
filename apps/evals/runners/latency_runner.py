"""Systems-level latency and cost evaluation runner.

Runs a configurable set of queries through the full pipeline and records
per-stage timing breakdowns, throughput, token estimates, and cost projections.
"""

from __future__ import annotations

import logging
import statistics
import time

from apps.evals.config import EvalConfig
from apps.evals.runners.base import BaseRunner, EvalResult
from packages.agents.orchestrator import QueryOrchestrator
from packages.rag.generation import GenerationService
from packages.rag.reranker import RerankerService
from packages.rag.search import SearchConfig, SearchService

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class LatencyRunner(BaseRunner):
    """Evaluates system-level performance characteristics.

    Metrics computed:
    - P50, P95, P99 end-to-end latency
    - Throughput (queries/sec)
    - Failure and timeout rates
    - Estimated token usage and cost per query
    """

    name = "latency"

    def __init__(
        self,
        config: EvalConfig,
        search_service: SearchService | None = None,
        generation_service: GenerationService | None = None,
        reranker_service: RerankerService | None = None,
    ) -> None:
        super().__init__(config)
        self.search_service = search_service or SearchService(SearchConfig())
        self.generation_service = generation_service or GenerationService()
        self.reranker_service = reranker_service or RerankerService()
        self.orchestrator = QueryOrchestrator(
            search_service=self.search_service,
            generation_service=self.generation_service,
            reranker_service=self.reranker_service,
        )

    async def run(self) -> EvalResult:
        # Use the retrieval dataset for latency testing — it's the largest set
        dataset = self.load_dataset(self.config.datasets.retrieval)
        k = self.config.top_k

        latencies: list[float] = []
        failures = 0
        timeouts = 0
        total_input_tokens = 0
        total_output_tokens = 0
        per_query: list[dict] = []

        overall_start = time.perf_counter()

        for idx, item in enumerate(dataset):
            query = item["question"]

            try:
                t0 = time.perf_counter()
                response = await self.orchestrator.answer_query(
                    query=query,
                    limit=k,
                    method="hybrid",
                    rerank=True,
                )
                query_ms = (time.perf_counter() - t0) * 1000
                latencies.append(query_ms)

                input_tokens = _estimate_tokens(query)
                output_tokens = _estimate_tokens(response.answer)
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens

                per_query.append(
                    {
                        "query": query[:80],
                        "latency_ms": round(query_ms, 1),
                        "input_tokens_est": input_tokens,
                        "output_tokens_est": output_tokens,
                        "status": "ok",
                    }
                )

                if idx % 20 == 0:
                    logger.info(
                        "[%d/%d] Latency: %.1fms",
                        idx + 1,
                        len(dataset),
                        query_ms,
                    )

            except TimeoutError:
                timeouts += 1
                per_query.append(
                    {
                        "query": query[:80],
                        "status": "timeout",
                    }
                )
            except Exception as e:
                failures += 1
                per_query.append(
                    {
                        "query": query[:80],
                        "status": "error",
                        "error": str(e),
                    }
                )

        overall_elapsed_s = time.perf_counter() - overall_start

        # Compute percentiles
        if latencies:
            sorted_lat = sorted(latencies)
            p50 = sorted_lat[int(len(sorted_lat) * 0.50)]
            p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
            p99 = sorted_lat[min(int(len(sorted_lat) * 0.99), len(sorted_lat) - 1)]
            avg = statistics.mean(latencies)
            stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0.0
        else:
            p50 = p95 = p99 = avg = stdev = 0.0

        n = len(dataset)
        throughput = n / overall_elapsed_s if overall_elapsed_s > 0 else 0.0

        cost_config = self.config.cost
        total_cost = (total_input_tokens / 1_000_000) * cost_config.input_rate_per_million + (
            total_output_tokens / 1_000_000
        ) * cost_config.output_rate_per_million

        metrics = {
            "p50_latency_ms": round(p50, 1),
            "p95_latency_ms": round(p95, 1),
            "p99_latency_ms": round(p99, 1),
            "avg_latency_ms": round(avg, 1),
            "stdev_latency_ms": round(stdev, 1),
            "throughput_qps": round(throughput, 2),
            "failure_rate": round(failures / n * 100, 2) if n else 0,
            "timeout_rate": round(timeouts / n * 100, 2) if n else 0,
            "total_queries": n,
            "total_input_tokens_est": total_input_tokens,
            "total_output_tokens_est": total_output_tokens,
            "estimated_cost_usd": round(total_cost, 6),
            "cost_per_query_usd": round(total_cost / n, 8) if n else 0,
        }

        return EvalResult(
            runner_name=self.name,
            timestamp=self.now_iso(),
            dataset_path=self.config.datasets.retrieval,
            config_snapshot={
                "top_k": k,
                "method": "hybrid",
                "rerank": True,
                "seed": self.config.seed,
            },
            metrics=metrics,
            per_query=per_query,
            timings={
                "total_elapsed_s": round(overall_elapsed_s, 2),
                "p50_ms": round(p50, 1),
                "p95_ms": round(p95, 1),
                "p99_ms": round(p99, 1),
            },
            metadata=self.capture_metadata(),
        )
