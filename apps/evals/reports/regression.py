"""Regression detection engine.

Compares candidate evaluation results against a frozen baseline and reports
whether any metric has regressed beyond the configured threshold.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC
from pathlib import Path
from typing import Any

from apps.evals.config import EvalConfig
from apps.evals.runners.base import EvalResult

logger = logging.getLogger(__name__)


@dataclass
class RegressionDetail:
    """One metric that regressed beyond its threshold."""

    runner: str
    metric: str
    baseline_value: float
    candidate_value: float
    threshold: float
    delta: float
    direction: str  # "min" or "max"
    message: str = ""


@dataclass
class RegressionResult:
    """Aggregated regression analysis result."""

    passed: bool
    regressions: list[RegressionDetail] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "regressions": [
                {
                    "runner": r.runner,
                    "metric": r.metric,
                    "baseline_value": r.baseline_value,
                    "candidate_value": r.candidate_value,
                    "threshold": r.threshold,
                    "delta": r.delta,
                    "direction": r.direction,
                    "message": r.message,
                }
                for r in self.regressions
            ],
            "warnings": self.warnings,
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Threshold definitions
# ---------------------------------------------------------------------------


def _build_threshold_checks(config: EvalConfig) -> list[dict[str, Any]]:
    """Build the list of metric checks from eval config.

    Each check specifies: runner, metric pattern, threshold, and direction.
    - direction="min": the metric must be >= threshold (e.g., recall).
    - direction="max": the metric must be <= threshold (e.g., latency).
    """
    checks = []
    reg = config.regression

    # Retrieval thresholds — applied to hybrid+rerank metrics
    checks.extend(
        [
            {
                "runner": "retrieval",
                "metric": "hybrid+rerank/recall_at_1",
                "threshold": reg.retrieval.recall_at_1_min,
                "direction": "min",
            },
            {
                "runner": "retrieval",
                "metric": "hybrid+rerank/recall_at_5",
                "threshold": reg.retrieval.recall_at_5_min,
                "direction": "min",
            },
            {
                "runner": "retrieval",
                "metric": "hybrid+rerank/mrr",
                "threshold": reg.retrieval.mrr_min,
                "direction": "min",
            },
        ]
    )

    # Generation thresholds
    checks.extend(
        [
            {
                "runner": "generation",
                "metric": "correctness",
                "threshold": reg.generation.correctness_min,
                "direction": "min",
            },
            {
                "runner": "generation",
                "metric": "faithfulness",
                "threshold": reg.generation.faithfulness_min,
                "direction": "min",
            },
            {
                "runner": "generation",
                "metric": "citation_quality",
                "threshold": reg.generation.citation_quality_min,
                "direction": "min",
            },
        ]
    )

    # Safety thresholds
    checks.extend(
        [
            {
                "runner": "safety",
                "metric": "jailbreak_deflection_rate",
                "threshold": reg.safety.jailbreak_deflection_min,
                "direction": "min",
            },
            {
                "runner": "safety",
                "metric": "off_topic_deflection_rate",
                "threshold": reg.safety.off_topic_deflection_min,
                "direction": "min",
            },
            {
                "runner": "safety",
                "metric": "false_positive_refusal_rate",
                "threshold": reg.safety.false_positive_refusal_max,
                "direction": "max",
            },
            {
                "runner": "safety",
                "metric": "pii_masking_efficacy_rate",
                "threshold": reg.safety.pii_masking_min,
                "direction": "min",
            },
        ]
    )

    # Latency thresholds
    checks.extend(
        [
            {
                "runner": "latency",
                "metric": "p95_latency_ms",
                "threshold": reg.latency.p95_generation_ms_max,
                "direction": "max",
            },
        ]
    )

    # Serving thresholds
    checks.extend(
        [
            {
                "runner": "serving",
                "metric": "cache_hit_rate",
                "threshold": reg.serving.cache_hit_rate_min,
                "direction": "min",
            },
            {
                "runner": "serving",
                "metric": "router_accuracy",
                "threshold": reg.serving.router_accuracy_min,
                "direction": "min",
            },
            {
                "runner": "serving",
                "metric": "circuit_breaker_trip_rate",
                "threshold": reg.serving.circuit_breaker_trip_rate_min,
                "direction": "min",
            },
        ]
    )

    return checks


# Regression checker
def load_baseline(baseline_path: str | Path) -> dict[str, Any] | None:
    """Load the frozen baseline JSON.  Returns None if file doesn't exist."""
    p = Path(baseline_path)
    if not p.exists():
        logger.warning("Baseline file not found: %s", p)
        return None
    with open(p) as fh:
        return json.load(fh)


def check_regression(
    results: list[EvalResult],
    config: EvalConfig,
    baseline: dict[str, Any] | None = None,
) -> RegressionResult:
    """Compare candidate results against configured thresholds.

    Parameters
    ----------
    results:
        List of EvalResult from the current run.
    config:
        Eval configuration with regression thresholds.
    baseline:
        Optional baseline report dict for delta comparison.

    Returns
    -------
    RegressionResult indicating pass/fail and any regressions.
    """
    checks = _build_threshold_checks(config)
    regressions: list[RegressionDetail] = []
    warnings: list[str] = []

    # Build a lookup: runner_name -> metrics dict
    result_lookup: dict[str, dict[str, float]] = {}
    for r in results:
        result_lookup[r.runner_name] = r.metrics

    for check in checks:
        runner = check["runner"]
        metric = check["metric"]
        threshold = check["threshold"]
        direction = check["direction"]

        runner_metrics = result_lookup.get(runner, {})
        if metric not in runner_metrics:
            warnings.append(f"Metric '{metric}' not found in runner '{runner}' results — skipping.")
            continue

        value = runner_metrics[metric]
        baseline_value = 0.0

        # Also check against baseline if available
        if baseline and "runners" in baseline:
            bl_runner = baseline["runners"].get(runner, {})
            baseline_value = bl_runner.get("metrics", {}).get(metric, 0.0)

        # Check threshold violation
        violated = False
        if direction == "min" and value < threshold:
            violated = True
        elif direction == "max" and value > threshold:
            violated = True

        if violated:
            delta = value - threshold
            regressions.append(
                RegressionDetail(
                    runner=runner,
                    metric=metric,
                    baseline_value=baseline_value,
                    candidate_value=value,
                    threshold=threshold,
                    delta=round(delta, 6),
                    direction=direction,
                    message=(
                        f"{runner}/{metric}: {value:.4f} {'<' if direction == 'min' else '>'} "
                        f"threshold {threshold:.4f} (Δ={delta:+.4f})"
                    ),
                )
            )

    passed = len(regressions) == 0

    if passed:
        summary = f"✅ All {len(checks)} regression checks passed."
    else:
        summary = (
            f"❌ {len(regressions)} regression(s) detected out of {len(checks)} checks.\n"
            + "\n".join(f"  - {r.message}" for r in regressions)
        )

    logger.info(summary)
    return RegressionResult(
        passed=passed,
        regressions=regressions,
        warnings=warnings,
        summary=summary,
    )


def freeze_baseline(
    results: list[EvalResult],
    output_path: str | Path,
) -> Path:
    """Freeze current results as the new baseline.

    Parameters
    ----------
    results:
        Current eval results to save as baseline.
    output_path:
        Path to write the baseline JSON.

    Returns
    -------
    Path to the written baseline file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    from datetime import datetime

    baseline = {
        "frozen_at": datetime.now(UTC).isoformat(),
        "runners": {},
    }

    for result in results:
        baseline["runners"][result.runner_name] = result.to_dict()

    with open(path, "w") as fh:
        json.dump(baseline, fh, indent=2, default=str)

    logger.info("Baseline frozen to %s", path)
    return path
