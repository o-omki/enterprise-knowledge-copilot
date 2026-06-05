"""Unified CLI entrypoint for the evaluation harness.

Usage::

    # Run all evaluations
    python -m apps.evals.cli run-all

    # Run a specific runner
    python -m apps.evals.cli run --runner retrieval
    python -m apps.evals.cli run --runner generation

    # Compare against baseline
    python -m apps.evals.cli compare

    # Freeze current results as new baseline
    python -m apps.evals.cli freeze-baseline

    # Generate golden QA dataset
    python -m apps.evals.cli generate-dataset
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from apps.evals.config import load_eval_config
from apps.evals.reports.regression import (
    RegressionResult,
    check_regression,
    freeze_baseline,
    load_baseline,
)
from apps.evals.reports.scorecard import (
    generate_json_report,
    generate_markdown_report,
)
from apps.evals.runners.base import EvalResult

logger = logging.getLogger(__name__)


RUNNER_NAMES = ["retrieval", "reranking", "generation", "safety", "latency"]


def _get_runner(name: str, config):
    """Lazy-import and instantiate a runner by name."""
    if name == "retrieval":
        from apps.evals.runners.retrieval_runner import RetrievalRunner

        return RetrievalRunner(config)
    elif name == "reranking":
        from apps.evals.runners.reranking_runner import RerankingRunner

        return RerankingRunner(config)
    elif name == "generation":
        from apps.evals.runners.generation_runner import GenerationRunner

        return GenerationRunner(config)
    elif name == "safety":
        from apps.evals.runners.safety_runner import SafetyRunner

        return SafetyRunner(config)
    elif name == "latency":
        from apps.evals.runners.latency_runner import LatencyRunner

        return LatencyRunner(config)
    else:
        raise ValueError(f"Unknown runner: {name}. Valid: {RUNNER_NAMES}")


async def cmd_run(args, config) -> list[EvalResult]:
    """Run one or more evaluation runners."""
    runners = args.runner if hasattr(args, "runner") and args.runner else RUNNER_NAMES
    if isinstance(runners, str):
        runners = [runners]

    results: list[EvalResult] = []
    for name in runners:
        logger.info("=" * 60)
        logger.info("Running %s evaluation...", name.upper())
        logger.info("=" * 60)
        try:
            runner = _get_runner(name, config)
            result = await runner.run()
            results.append(result)
            logger.info(
                "%s evaluation complete. Metrics: %s",
                name.upper(),
                {k: v for k, v in result.metrics.items() if isinstance(v, int | float)},
            )
        except FileNotFoundError as e:
            logger.error("Skipping %s — dataset not found: %s", name, e)
        except Exception as e:
            logger.error("Runner %s failed: %s", name, e, exc_info=True)

    if not results:
        logger.error("No evaluation results produced.")
        return results

    # Generate reports
    output_dir = config.reports.output_dir
    baseline = load_baseline(config.reports.baseline_path)

    if "json" in config.reports.formats:
        json_path = generate_json_report(results, output_dir, baseline)
        logger.info("JSON report: %s", json_path)

    if "markdown" in config.reports.formats:
        md_path = generate_markdown_report(results, output_dir, baseline)
        logger.info("Markdown report: %s", md_path)

    return results


async def cmd_run_all(args, config) -> list[EvalResult]:
    """Run all evaluation runners."""
    args.runner = RUNNER_NAMES
    return await cmd_run(args, config)


async def cmd_compare(args, config) -> None:
    """Run all evaluations and check for regressions."""
    # First run all evals
    args.runner = RUNNER_NAMES
    results = await cmd_run(args, config)

    if not results:
        logger.error("No results to compare.")
        sys.exit(1)

    baseline = load_baseline(
        args.baseline
        if hasattr(args, "baseline") and args.baseline
        else config.reports.baseline_path
    )

    regression_result: RegressionResult = check_regression(
        results,
        config,
        baseline,
    )

    logger.info("\n%s", regression_result.summary)

    if regression_result.warnings:
        for w in regression_result.warnings:
            logger.warning("⚠ %s", w)

    if not regression_result.passed:
        logger.error("Regression gate FAILED.")
        sys.exit(1)
    else:
        logger.info("Regression gate PASSED. ✅")


async def cmd_freeze_baseline(args, config) -> None:
    """Run all evaluations and freeze results as the new baseline."""
    args.runner = RUNNER_NAMES
    results = await cmd_run(args, config)

    if not results:
        logger.error("No results to freeze.")
        sys.exit(1)

    output_path = (
        args.output if hasattr(args, "output") and args.output else config.reports.baseline_path
    )
    freeze_baseline(results, output_path)
    logger.info("Baseline frozen to %s", output_path)


async def cmd_generate_dataset(args, config) -> None:
    """Generate the golden QA evaluation dataset."""
    from apps.evals.datasets.generate_golden_qa import generate_golden_qa

    output = await generate_golden_qa(
        corpus_dir=args.corpus_dir if hasattr(args, "corpus_dir") else "data/raw/official_docs",
        output_path=config.datasets.generation,
        target_count=args.count if hasattr(args, "count") else 80,
        seed=config.seed,
    )
    logger.info("Dataset generated: %s", output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apps.evals.cli",
        description="Enterprise Knowledge Copilot — Unified Evaluation Harness",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to evals.yaml config file (default: configs/evals.yaml)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Evaluation commands")

    # run
    run_parser = subparsers.add_parser("run", help="Run specific evaluation runner(s)")
    run_parser.add_argument(
        "--runner",
        nargs="+",
        choices=RUNNER_NAMES,
        help=f"Runner(s) to execute. Choices: {RUNNER_NAMES}",
    )

    # run-all
    subparsers.add_parser("run-all", help="Run all evaluation runners")

    # compare
    compare_parser = subparsers.add_parser(
        "compare",
        help="Run all evals and check for regressions",
    )
    compare_parser.add_argument(
        "--baseline",
        default=None,
        help="Path to baseline JSON (default: from config)",
    )

    # freeze-baseline
    freeze_parser = subparsers.add_parser(
        "freeze-baseline",
        help="Run all evals and freeze results as new baseline",
    )
    freeze_parser.add_argument(
        "--output",
        default=None,
        help="Output path for baseline JSON (default: from config)",
    )

    # generate-dataset
    gen_parser = subparsers.add_parser(
        "generate-dataset",
        help="Generate golden QA evaluation dataset",
    )
    gen_parser.add_argument(
        "--corpus-dir",
        default="data/raw/official_docs",
        help="Path to source document corpus",
    )
    gen_parser.add_argument(
        "--count",
        type=int,
        default=80,
        help="Target number of QA pairs",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.command:
        parser.print_help()
        sys.exit(0)

    config_path = Path(args.config) if args.config else None
    config = load_eval_config(config_path)

    command_map = {
        "run": cmd_run,
        "run-all": cmd_run_all,
        "compare": cmd_compare,
        "freeze-baseline": cmd_freeze_baseline,
        "generate-dataset": cmd_generate_dataset,
    }

    handler = command_map.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    asyncio.run(handler(args, config))


if __name__ == "__main__":
    main()
