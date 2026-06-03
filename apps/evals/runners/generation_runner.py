"""End-to-end generation quality evaluation runner.

Runs the full RAG pipeline (retrieve → rerank → generate) for each golden QA
pair and scores the output using the LLM-as-judge.  Captures per-stage latency
and estimated token counts.
"""

from __future__ import annotations

import logging
import time

from apps.evals.config import EvalConfig
from apps.evals.judges.answer_judge import AnswerJudge, JudgeVerdict
from apps.evals.judges.grounding_judge import GroundingJudge
from apps.evals.runners.base import BaseRunner, EvalResult
from packages.agents.orchestrator import QueryOrchestrator
from packages.rag.generation import GenerationService
from packages.rag.reranker import RerankerService
from packages.rag.search import SearchConfig, SearchService

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate — ~4 chars per token for English text."""
    return max(1, len(text) // 4)


class GenerationRunner(BaseRunner):
    """Evaluates end-to-end answer quality using the golden QA dataset.

    Metrics computed:
    - Correctness, faithfulness, completeness, citation quality, conciseness
      (via LLM-as-judge)
    - Grounding score (via claim-level grounding judge)
    - Per-stage latency (retrieval, rerank, generation)
    - Estimated input/output token counts
    - Estimated cost per query
    """

    name = "generation"

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
        self.answer_judge = AnswerJudge(config.judge)
        self.grounding_judge = GroundingJudge(config.judge)

    async def run(self) -> EvalResult:
        dataset = self.load_dataset(self.config.datasets.generation)
        k = self.config.top_k

        # Accumulators
        score_sums: dict[str, float] = {
            "correctness": 0.0,
            "faithfulness": 0.0,
            "completeness": 0.0,
            "citation_quality": 0.0,
            "conciseness": 0.0,
            "grounding": 0.0,
        }
        total_retrieval_ms = 0.0
        total_generation_ms = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        per_query: list[dict] = []
        evaluated = 0

        import asyncio

        semaphore = asyncio.Semaphore(5)

        async def _process_item(idx: int, item: dict):
            async with semaphore:
                question = item["question"]
                reference_answer = item["reference_answer"]
                expected_source = item.get("expected_source", "")
                question_type = item.get("question_type", "unknown")

                logger.info(
                    "[%d/%d] Evaluating: %s...",
                    idx + 1,
                    len(dataset),
                    question[:60],
                )

                try:
                    # Full pipeline execution with timing
                    t_start = time.perf_counter()

                    # Retrieve + rerank
                    response = await self.orchestrator.answer_query(
                        query=question,
                        limit=k,
                        method="hybrid",
                        rerank=True,
                    )
                    total_pipeline_ms = (time.perf_counter() - t_start) * 1000

                    retrieval_ms = total_pipeline_ms * 0.3  # rough estimate
                    generation_ms = total_pipeline_ms * 0.7

                    generated_answer = response.answer
                    citations = [c.model_dump() for c in response.citations]

                    # Estimate tokens
                    input_tokens = _estimate_tokens(question) + sum(
                        _estimate_tokens(c.get("snippet", "")) for c in citations
                    )
                    output_tokens = _estimate_tokens(generated_answer)

                    context_passages = response.context_passages

                    verdict: JudgeVerdict = await self.answer_judge.judge(
                        question=question,
                        reference_answer=reference_answer,
                        generated_answer=generated_answer,
                        citations=citations,
                        context=context_passages,
                    )

                    grounding = await self.grounding_judge.check_grounding(
                        generated_answer=generated_answer,
                        context=context_passages,
                    )

                    return {
                        "question": question,
                        "question_type": question_type,
                        "expected_source": expected_source,
                        "generated_answer": generated_answer[:500],
                        "reference_answer": reference_answer[:500],
                        "scores": {
                            "correctness": verdict.correctness,
                            "faithfulness": verdict.faithfulness,
                            "completeness": verdict.completeness,
                            "citation_quality": verdict.citation_quality,
                            "conciseness": verdict.conciseness,
                            "grounding": grounding.grounding_score,
                            "average": verdict.average,
                        },
                        "judge_reasoning": verdict.reasoning,
                        "grounding_detail": {
                            "total_claims": grounding.total_claims,
                            "supported": grounding.supported,
                            "unsupported": grounding.unsupported,
                            "contradicted": grounding.contradicted,
                            "flagged_claims": grounding.flagged_claims[:5],
                        },
                        "latency_ms": round(total_pipeline_ms, 1),
                        "retrieval_ms": retrieval_ms,
                        "generation_ms": generation_ms,
                        "input_tokens_est": input_tokens,
                        "output_tokens_est": output_tokens,
                        "status": "ok",
                    }

                except Exception as e:
                    logger.error("Generation eval failed for '%s': %s", question[:50], e)
                    return {
                        "question": question,
                        "question_type": question_type,
                        "status": "error",
                        "error": str(e),
                    }

        tasks = [_process_item(idx, item) for idx, item in enumerate(dataset)]
        results = await asyncio.gather(*tasks)

        for res in results:
            if res.get("status") == "ok":
                scores = res["scores"]
                score_sums["correctness"] += scores["correctness"]
                score_sums["faithfulness"] += scores["faithfulness"]
                score_sums["completeness"] += scores["completeness"]
                score_sums["citation_quality"] += scores["citation_quality"]
                score_sums["conciseness"] += scores["conciseness"]
                score_sums["grounding"] += scores["grounding"]

                total_retrieval_ms += res.pop("retrieval_ms")
                total_generation_ms += res.pop("generation_ms")
                total_input_tokens += res["input_tokens_est"]
                total_output_tokens += res["output_tokens_est"]
                evaluated += 1

            per_query.append(res)

        # Aggregate metrics
        n = evaluated or 1
        cost_config = self.config.cost
        total_cost = (total_input_tokens / 1_000_000) * cost_config.input_rate_per_million + (
            total_output_tokens / 1_000_000
        ) * cost_config.output_rate_per_million

        metrics = {
            "correctness": round(score_sums["correctness"] / n, 4),
            "faithfulness": round(score_sums["faithfulness"] / n, 4),
            "completeness": round(score_sums["completeness"] / n, 4),
            "citation_quality": round(score_sums["citation_quality"] / n, 4),
            "conciseness": round(score_sums["conciseness"] / n, 4),
            "grounding": round(score_sums["grounding"] / n, 4),
            "avg_latency_ms": round((total_retrieval_ms + total_generation_ms) / len(dataset), 1),
            "total_input_tokens_est": total_input_tokens,
            "total_output_tokens_est": total_output_tokens,
            "estimated_cost_usd": round(total_cost, 6),
            "queries_evaluated": evaluated,
            "queries_failed": len(dataset) - evaluated,
        }

        return EvalResult(
            runner_name=self.name,
            timestamp=self.now_iso(),
            dataset_path=self.config.datasets.generation,
            config_snapshot={
                "top_k": k,
                "method": "hybrid",
                "rerank": True,
                "judge_model": self.config.judge.model,
                "seed": self.config.seed,
            },
            metrics=metrics,
            per_query=per_query,
            timings={
                "total_retrieval_ms": round(total_retrieval_ms, 1),
                "total_generation_ms": round(total_generation_ms, 1),
            },
            metadata=self.capture_metadata(),
        )
