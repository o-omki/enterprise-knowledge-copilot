"""Script to perform A/B comparison of two configurations."""

import argparse
import json


def load_metrics(report_path: str) -> dict:
    with open(report_path, encoding="utf-8") as f:
        data = json.load(f)
        # Handle format: [{'metrics': {...}}, ...] or a single result dict
        if isinstance(data, list):
            # If it's a sweep result, grab the first one or we can require single result JSONs.
            # But normally apps.evals.cli outputs a dict with runner names as keys.
            if "metrics" in data[0]:
                return data[0]["metrics"]

            # Evall cli returns list of results
            for result in data:
                if result.get("runner_name") == "generation":
                    return result["metrics"]
            raise ValueError("No generation metrics found in report.")
        elif isinstance(data, dict):
            # Check if it's the direct output format
            if "metrics" in data:
                return data["metrics"]

            if "generation" in data:
                return data["generation"]["metrics"]

        return data


def format_delta(baseline: float, candidate: float, is_lower_better: bool = False) -> str:
    if baseline == 0:
        return "N/A"
    delta = candidate - baseline
    pct = (delta / baseline) * 100

    if is_lower_better:
        if delta < 0:
            return f"{candidate:.4f} (⬇ {abs(pct):.1f}% 🎉)"
        elif delta > 0:
            return f"{candidate:.4f} (⬆ {abs(pct):.1f}% ⚠️)"
        return f"{candidate:.4f} (no change)"
    else:
        if delta > 0:
            return f"{candidate:.4f} (⬆ {abs(pct):.1f}% 🎉)"
        elif delta < 0:
            return f"{candidate:.4f} (⬇ {abs(pct):.1f}% ⚠️)"
        return f"{candidate:.4f} (no change)"


def compare(baseline_path: str, candidate_path: str):
    print("# A/B Evaluation Comparison\n")
    print(f"**Baseline (A):** `{baseline_path}`")
    print(f"**Candidate (B):** `{candidate_path}`\n")

    base_metrics = load_metrics(baseline_path)
    cand_metrics = load_metrics(candidate_path)

    # Trust Gates
    base_faith = base_metrics.get("faithfulness", 0)
    cand_faith = cand_metrics.get("faithfulness", 0)
    base_cite = base_metrics.get("citation_quality", 0)
    cand_cite = cand_metrics.get("citation_quality", 0)

    trust_gate_passed = cand_faith >= (base_faith - 0.02) and cand_cite >= (base_cite - 0.02)

    # Value Gate
    base_corr = base_metrics.get("correctness", 0)
    cand_corr = cand_metrics.get("correctness", 0)

    value_gate_passed = cand_corr >= base_corr

    # Efficiency Optimizers
    base_lat = base_metrics.get("avg_latency_ms", 0)
    cand_lat = cand_metrics.get("avg_latency_ms", 0)
    base_cost = base_metrics.get("estimated_cost_usd", 0)
    cand_cost = cand_metrics.get("estimated_cost_usd", 0)

    print("## Tier 1: The Trust Gates (Pass / Fail)")
    print("Non-negotiable. Hallucinations destroy enterprise utility.\n")
    print("| Metric | Baseline (A) | Candidate (B) | Delta |")
    print("|---|---|---|---|")
    print(
        f"| Faithfulness | {base_faith:.4f} | "
        f"{cand_faith:.4f} | {format_delta(base_faith, cand_faith)} |"
    )
    print(
        f"| Citation Quality | {base_cite:.4f} | "
        f"{cand_cite:.4f} | {format_delta(base_cite, cand_cite)} |"
    )

    trust_status = (
        "✅ PASSED" if trust_gate_passed else "❌ FAILED (Significant drop in trust metrics)"
    )
    print(f"\n**Status:** {trust_status}\n")

    print("## Tier 2: The Value Gate (Core Utility)")
    print("Does the new configuration answer the user's question more accurately?\n")
    print("| Metric | Baseline (A) | Candidate (B) | Delta |")
    print("|---|---|---|---|")
    print(
        f"| Correctness | {base_corr:.4f} | "
        f"{cand_corr:.4f} | {format_delta(base_corr, cand_corr)} |"
    )

    value_status = "✅ IMPROVED/TIED" if value_gate_passed else "❌ DEGRADED"
    print(f"\n**Status:** {value_status}\n")

    print("## Tier 3: The Efficiency Optimizers")
    print("Trade-off tie-breakers (Lower is better).\n")
    print("| Metric | Baseline (A) | Candidate (B) | Delta |")
    print("|---|---|---|---|")
    print(
        f"| Avg Latency (ms) | {base_lat:.1f} | "
        f"{cand_lat:.1f} | {format_delta(base_lat, cand_lat, True)} |"
    )
    print(
        f"| Cost (USD) | {base_cost:.6f} | "
        f"{cand_cost:.6f} | {format_delta(base_cost, cand_cost, True)} |"
    )
    print("\n")

    print("## Final Conclusion")
    if not trust_gate_passed:
        print(
            "Candidate B is a **REJECT**. It failed the Tier 1 Trust Gate "
            "due to an unacceptable drop in Faithfulness or Citation Quality."
        )
    elif not value_gate_passed:
        print(
            "Candidate B is a **REJECT**. It failed the Tier 2 Value Gate "
            "due to a drop in Semantic Correctness."
        )
    else:
        lat_improved = cand_lat < base_lat
        cost_improved = cand_cost < base_cost

        if cand_corr > base_corr + 0.02:
            print(
                "Candidate B is a **CLEAR WIN**. It maintained trust metrics and "
                "achieved a meaningful increase in Correctness."
            )
        elif lat_improved or cost_improved:
            print(
                "Candidate B is an **EFFICIENCY WIN**. It maintained Trust and "
                "Value metrics while improving Efficiency (Latency/Cost)."
            )
        else:
            print(
                "Candidate B is a **TIE**. It offers no significant improvement in "
                "correctness, latency, or cost over Baseline A."
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A/B Comparison for Eval Runs")
    parser.add_argument(
        "--baseline", type=str, required=True, help="Path to baseline evaluation JSON"
    )
    parser.add_argument(
        "--candidate", type=str, required=True, help="Path to candidate evaluation JSON"
    )
    args = parser.parse_args()

    compare(args.baseline, args.candidate)
