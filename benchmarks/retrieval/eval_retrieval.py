import asyncio
import json
import logging
import sys
import time
from pathlib import Path

from packages.rag.reranker import RerankerService
from packages.rag.search import SearchConfig, SearchService

CANDIDATE_MULTIPLIER = 2  # Retrieve this many candidates before reranking


async def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger("eval_retrieval")

    ground_truth_path = Path("data/eval/retrieval/ground_truth.json")

    if not ground_truth_path.exists():
        logger.error(f"Ground truth file not found: {ground_truth_path}")
        sys.exit(1)

    with open(ground_truth_path) as f:
        dataset = json.load(f)

    logger.info(f"Loaded {len(dataset)} evaluation queries.")

    baseline_path = Path("data/eval/retrieval/baseline_phase3.json")
    baseline: dict = {}
    if baseline_path.exists():
        with open(baseline_path) as f:
            baseline = json.load(f)
        logger.info("Loaded Phase 3 baseline from baseline_phase3.json")
    else:
        logger.warning("baseline_phase3.json not found — skipping baseline comparison.")

    config = SearchConfig()
    try:
        search_service = SearchService(config=config)
    except Exception as e:
        logger.error(f"Failed to initialize SearchService. Did you set GCP env vars? {e}")
        sys.exit(1)

    reranker_service = RerankerService()

    K = 5
    methods = ["dense", "sparse", "hybrid", "hybrid+rerank"]
    metrics: dict[str, dict] = {
        m: {"recall_at_1": 0.0, "recall_at_5": 0.0, "mrr": 0.0, "avg_latency_ms": 0.0}
        for m in methods
    }

    for method in methods:
        logger.info(f"\n--- Running Eval for method: {method.upper()} ---")
        rr_sum = 0.0
        hits_at_1 = 0
        hits_at_5 = 0
        total_latency_ms = 0.0

        retrieval_method = "hybrid" if method == "hybrid+rerank" else method
        fetch_limit = K * CANDIDATE_MULTIPLIER if method == "hybrid+rerank" else K

        for item in dataset:
            query = item["question"]
            expected = item["expected_source"]

            try:
                t0 = time.time()
                results = await search_service.search(
                    query=query, limit=fetch_limit, method=retrieval_method
                )
                if method == "hybrid+rerank":
                    results = await reranker_service.arerank(query=query, results=results, top_k=K)
                query_latency_ms = (time.time() - t0) * 1000
                total_latency_ms += query_latency_ms
            except Exception as e:
                logger.error(f"Search failed for query '{query}': {e}")
                continue

            rank = None
            for i, res in enumerate(results):
                if expected in res.source:
                    rank = i + 1
                    break

            if rank is not None:
                rr_sum += 1.0 / rank
                if rank == 1:
                    hits_at_1 += 1
                if rank <= K:
                    hits_at_5 += 1
                logger.info(f"Query: '{query[:40]:<40}...' | Rank: {rank}")
            else:
                logger.warning(f"Query: '{query[:40]:<40}...' | FAIL (not in top {K})")

        n = len(dataset)
        metrics[method]["mrr"] = round(rr_sum / n, 4)
        metrics[method]["recall_at_1"] = round(hits_at_1 / n, 4)
        metrics[method]["recall_at_5"] = round(hits_at_5 / n, 4)
        metrics[method]["avg_latency_ms"] = round(total_latency_ms / n, 1)

    logger.info("\n" + "=" * 72)
    logger.info("EVALUATION RESULTS")
    logger.info("=" * 72)
    header = f"{'Method':<20} {'Recall@1':>10} {'Recall@5':>10} {'MRR':>8} {'Latency(ms)':>12}"
    logger.info(header)
    logger.info("-" * 72)
    for method, scores in metrics.items():
        logger.info(
            f"{method:<20} {scores['recall_at_1']:>10.2f} {scores['recall_at_5']:>10.2f}"
            f" {scores['mrr']:>8.2f} {scores['avg_latency_ms']:>12.1f}"
        )

    if baseline and "methods" in baseline:
        logger.info("\n" + "=" * 72)
        logger.info("COMPARISON vs PHASE 3 BASELINE (pre-reranking)")
        logger.info("=" * 72)
        for m in ["dense", "sparse", "hybrid"]:
            base = baseline["methods"].get(m, {})
            curr = metrics.get(m, {})
            if base and curr:
                delta_r1 = curr["recall_at_1"] - base.get("recall_at_1", 0)
                delta_r5 = curr["recall_at_5"] - base.get("recall_at_5", 0)
                delta_mrr = curr["mrr"] - base.get("mrr", 0)
                logger.info(
                    f"{m.upper():<12}  ΔRecall@1={delta_r1:+.2f}  "
                    f"ΔRecall@5={delta_r5:+.2f}  ΔMRR={delta_mrr:+.2f}"
                )

    target_r1 = 0.83  # Must match or beat dense baseline Recall@1
    if baseline and "phase3_target" in baseline:
        target_r1 = baseline["phase3_target"].get("minimum_recall_at_1_hybrid_reranked", target_r1)

    achieved_r1 = metrics["hybrid+rerank"]["recall_at_1"]
    logger.info("\n" + "=" * 72)
    logger.info("PHASE 3 GATE")
    logger.info("=" * 72)
    logger.info(f"Target : hybrid+rerank Recall@1 >= {target_r1:.2f}")
    logger.info(f"Achieved: hybrid+rerank Recall@1  = {achieved_r1:.2f}")
    if achieved_r1 >= target_r1:
        logger.info("STATUS: PASSED ✓")
    else:
        logger.info(f"STATUS: FAILED ✗  (gap: {target_r1 - achieved_r1:.2f})")

    results_path = Path("data/eval/retrieval/phase3_reranking_results.json")
    with open(results_path, "w") as f:
        json.dump(
            {
                "description": "Phase 3 reranking evaluation results",
                "dataset": str(ground_truth_path),
                "top_k": K,
                "candidate_multiplier": CANDIDATE_MULTIPLIER,
                "metrics": metrics,
                "phase3_gate": {
                    "target_recall_at_1": target_r1,
                    "achieved_recall_at_1": achieved_r1,
                    "passed": achieved_r1 >= target_r1,
                },
            },
            f,
            indent=2,
        )
    logger.info(f"\nResults written to {results_path}")


if __name__ == "__main__":
    asyncio.run(main())
