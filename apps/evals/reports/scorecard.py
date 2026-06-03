"""Scorecard generation — JSON and Markdown reports from EvalResults.

Consumes one or more :class:`EvalResult` objects and produces:
1. A machine-readable JSON report (version-controlled).
2. A human-readable Markdown scorecard with comparison tables.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.evals.runners.base import EvalResult

logger = logging.getLogger(__name__)


def _timestamp_slug() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------


def generate_json_report(
    results: list[EvalResult],
    output_dir: str | Path,
    baseline: dict[str, Any] | None = None,
) -> Path:
    """Write a combined JSON report for all runner results.

    Returns the path to the written file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "runners": {},
    }

    for result in results:
        report["runners"][result.runner_name] = result.to_dict()

    if baseline:
        report["baseline"] = baseline

    path = output_dir / f"eval_{_timestamp_slug()}.json"
    with open(path, "w") as fh:
        json.dump(report, fh, indent=2, default=str)

    logger.info("JSON report written to %s", path)
    return path


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def _format_metric(value: Any) -> str:
    """Format a metric value for display."""
    if isinstance(value, float):
        if abs(value) < 0.01 and value != 0:
            return f"{value:.6f}"
        return f"{value:.4f}"
    return str(value)


def _delta_indicator(current: float, baseline_val: float, higher_is_better: bool = True) -> str:
    """Produce a Δ value with ↑/↓ indicators."""
    delta = current - baseline_val
    if abs(delta) < 0.0001:
        return "—"
    arrow = "↑" if (delta > 0) == higher_is_better else "↓"
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.4f} {arrow}"


def generate_markdown_report(
    results: list[EvalResult],
    output_dir: str | Path,
    baseline: dict[str, Any] | None = None,
) -> Path:
    """Write a Markdown scorecard for all runner results.

    Returns the path to the written file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []
    lines.append(f"# Evaluation Scorecard — {ts}")
    lines.append("")

    # Metadata from first result
    if results:
        meta = results[0].metadata
        lines.append(f"**Git SHA**: `{meta.get('git_sha', 'unknown')}`")
        lines.append(f"**Python**: `{meta.get('python_version', 'unknown').split()[0]}`")
        lines.append("")

    # ---- Per-runner sections ----
    for result in results:
        lines.append(f"## {result.runner_name.title()} Evaluation")
        lines.append("")
        lines.append(f"- **Dataset**: `{result.dataset_path}`")
        lines.append(f"- **Timestamp**: {result.timestamp}")
        lines.append("")

        # Metrics table
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")

        # Get baseline metrics for this runner if available
        baseline_metrics: dict[str, float] = {}
        if baseline and "runners" in baseline:
            runner_baseline = baseline["runners"].get(result.runner_name, {})
            baseline_metrics = runner_baseline.get("metrics", {})

        for metric_name, value in sorted(result.metrics.items()):
            formatted = _format_metric(value)
            if metric_name in baseline_metrics:
                # Determine if higher is better
                higher_is_better = not any(
                    neg in metric_name
                    for neg in [
                        "latency",
                        "cost",
                        "failure",
                        "timeout",
                        "refusal",
                        "false_positive",
                    ]
                )
                delta = _delta_indicator(value, baseline_metrics[metric_name], higher_is_better)
                lines.append(f"| `{metric_name}` | {formatted} ({delta}) |")
            else:
                lines.append(f"| `{metric_name}` | {formatted} |")

        lines.append("")

        # Timing summary
        if result.timings:
            lines.append("### Timing Summary")
            lines.append("")
            lines.append("| Stage | Duration |")
            lines.append("|-------|----------|")
            for stage, duration in result.timings.items():
                lines.append(f"| `{stage}` | {_format_metric(duration)} ms |")
            lines.append("")

        # Failure analysis — show worst 5 queries
        failures = [q for q in result.per_query if q.get("status") in ("miss", "error", "fail")]
        if failures:
            lines.append("### Notable Failures")
            lines.append("")
            for fail in failures[:5]:
                query_text = fail.get("query", "?")[:80]
                status = fail.get("status", "?")
                error = fail.get("error", "")
                lines.append(f"- **{status}**: `{query_text}` {error}")
            if len(failures) > 5:
                lines.append(f"- ... and {len(failures) - 5} more")
            lines.append("")

        lines.append("---")
        lines.append("")

    # ---- Baseline comparison table (if baseline exists) ----
    if baseline and "runners" in baseline:
        lines.append("## Baseline Comparison Summary")
        lines.append("")
        lines.append("| Runner | Metric | Baseline | Current | Δ |")
        lines.append("|--------|--------|----------|---------|---|")

        for result in results:
            runner_baseline = baseline["runners"].get(result.runner_name, {})
            bl_metrics = runner_baseline.get("metrics", {})
            for metric_name in sorted(result.metrics):
                if metric_name in bl_metrics:
                    bl_val = bl_metrics[metric_name]
                    cur_val = result.metrics[metric_name]
                    higher_is_better = not any(
                        neg in metric_name
                        for neg in [
                            "latency",
                            "cost",
                            "failure",
                            "timeout",
                            "refusal",
                            "false_positive",
                        ]
                    )
                    delta = _delta_indicator(cur_val, bl_val, higher_is_better)
                    lines.append(
                        f"| {result.runner_name} | `{metric_name}` | "
                        f"{_format_metric(bl_val)} | {_format_metric(cur_val)} | {delta} |"
                    )

        lines.append("")

    path = output_dir / f"eval_{_timestamp_slug()}.md"
    with open(path, "w") as fh:
        fh.write("\n".join(lines))

    logger.info("Markdown scorecard written to %s", path)
    return path
