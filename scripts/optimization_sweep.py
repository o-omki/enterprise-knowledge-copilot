"""Script to perform an optimization sweep over configurations."""

import asyncio
import datetime
import json
import logging
from pathlib import Path

from apps.evals.config import load_eval_config
from apps.evals.runners.generation_runner import GenerationRunner
from packages.llm_serving.client import LLMClient
from packages.rag.generation import GenerationConfig, GenerationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Limits the number of concurrent Vertex AI evaluations to prevent queueing/CPU spikes
SEMAPHORE = asyncio.Semaphore(3)


async def evaluate_single_config(config, prompt_version, top_k):
    """Evaluates a single configuration."""
    logger.info("=" * 60)
    logger.info(f"Evaluating config: prompt_version={prompt_version}, top_k={top_k}")
    logger.info("=" * 60)

    llm_client = LLMClient()

    gen_config = GenerationConfig(prompt_version=prompt_version)
    gen_service = GenerationService(llm_client=llm_client, config=gen_config)

    runner = GenerationRunner(config=config, generation_service=gen_service)

    result = await runner.run()

    return {
        "prompt_version": prompt_version,
        "top_k": top_k,
        "metrics": result.metrics,
        "runner_result": result,
    }


async def main():
    config = load_eval_config()
    sweep_config = config.sweep
    top_ks = sweep_config.top_k
    prompt_versions = sweep_config.prompt_versions
    output_dir = Path(sweep_config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    sweep_report_path = output_dir / f"sweep_{timestamp}.json"

    all_results = []

    # Run sequentially over the sweep grid
    for prompt_version in prompt_versions:
        for k in top_ks:
            current_config = load_eval_config()
            current_config.top_k = k

            res = await evaluate_single_config(current_config, prompt_version, k)

            # Save minimal summary
            summary = {
                "prompt_version": res["prompt_version"],
                "top_k": res["top_k"],
                "metrics": res["metrics"],
            }
            all_results.append(summary)

            with open(sweep_report_path, "w") as f:
                json.dump(all_results, f, indent=2)

            logger.info(
                f"Finished: prompt={prompt_version}, top_k={k}. "
                f"Score: {res['metrics'].get('correctness')}"
            )

    logger.info(f"Sweep complete. Results saved to {sweep_report_path}")


if __name__ == "__main__":
    asyncio.run(main())
