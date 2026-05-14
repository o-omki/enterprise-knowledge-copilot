import asyncio
import json
import logging
import sys
from pathlib import Path

from packages.rag.search import SearchConfig, SearchService


async def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger("eval_retrieval")

    ground_truth_path = Path("data/eval/retrieval/fastapi_ground_truth.json")
    if not ground_truth_path.exists():
        logger.error(f"Ground truth file not found: {ground_truth_path}")
        sys.exit(1)

    with open(ground_truth_path) as f:
        dataset = json.load(f)

    logger.info(f"Loaded {len(dataset)} evaluation queries.")

    config = SearchConfig()
    try:
        search_service = SearchService(config=config)
    except Exception as e:
        logger.error(f"Failed to initialize SearchService. Did you set GCP env vars? {e}")
        sys.exit(1)

    K = 5
    metrics = {
        "dense": {"recall_at_1": 0, "recall_at_5": 0, "mrr": 0.0},
        "sparse": {"recall_at_1": 0, "recall_at_5": 0, "mrr": 0.0},
        "hybrid": {"recall_at_1": 0, "recall_at_5": 0, "mrr": 0.0},
    }

    for method in ["dense", "sparse", "hybrid"]:
        logger.info(f"\n--- Running Eval for method: {method.upper()} ---")
        rr_sum = 0.0
        hits_at_1 = 0
        hits_at_5 = 0

        for item in dataset:
            query = item["question"]
            expected = item["expected_source"]

            try:
                results = await search_service.search(query=query, limit=K, method=method)
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
                if rank <= 5:
                    hits_at_5 += 1
                logger.info(f"Query: '{query[:40]:<40}...' | Rank: {rank}")
            else:
                logger.warning(f"Query: '{query[:40]:<40}...' | FAIL (not in top {K})")

        n = len(dataset)
        metrics[method]["mrr"] = rr_sum / n
        metrics[method]["recall_at_1"] = hits_at_1 / n
        metrics[method]["recall_at_5"] = hits_at_5 / n

    logger.info("\n=== EVALUATION RESULTS ===")
    for method, scores in metrics.items():
        logger.info(f"Method: {method.upper()}")
        logger.info(f"  Recall@1: {scores['recall_at_1']:.2f}")
        logger.info(f"  Recall@5: {scores['recall_at_5']:.2f}")
        logger.info(f"  MRR:      {scores['mrr']:.2f}")

    best_recall = max(metrics["dense"]["recall_at_5"], metrics["sparse"]["recall_at_5"])

    logger.info("\n=== PHASE 1 GATE ===")
    if best_recall >= 0.85:
        logger.info(f"PASSED: Best Recall@5 ({best_recall:.2f}) >= 0.85")
    else:
        logger.info(f"FAILED: Best Recall@5 ({best_recall:.2f}) < 0.85")


if __name__ == "__main__":
    asyncio.run(main())
