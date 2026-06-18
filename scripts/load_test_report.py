import csv
import sys
from pathlib import Path


def parse_csv_stats(stats_path: Path) -> list[dict]:
    """Parses the Locust stats.csv file."""
    results = []
    with open(stats_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    return results


def main():
    csv_path = Path("data/eval/reports/load_test_stats.csv")
    if not csv_path.exists():
        print(f"Error: Load test stats CSV not found at {csv_path}", file=sys.stderr)
        print("Please run the load test first to generate stats.", file=sys.stderr)
        sys.exit(1)

    print("Parsing load test results...")
    rows = parse_csv_stats(csv_path)

    # Set up SLO thresholds
    max_ask_p95_ms = 5000.0
    max_search_p95_ms = 1000.0

    md_lines = [
        "# Load Test Performance Report\n",
        f"Generated from Locust stats: `{csv_path}`\n",
        "## Performance Metrics Summary\n",
        (
            "| Endpoint | Requests | Failures | Avg Latency (ms) | P50 (ms) "
            "| P95 (ms) | P99 (ms) | QPS |"
        ),
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    ask_p95 = None
    search_p95 = None

    for row in rows:
        name = row.get("Name", "")
        # Skip total line from table formatting (will detail it separately)
        if name == "Aggregated":
            continue

        req_count = row.get("Request Count", "0")
        fail_count = row.get("Failure Count", "0")
        avg_lat = round(float(row.get("Average Response Time", "0")), 1)
        p50 = round(float(row.get("50%", "0")), 1)
        p95 = round(float(row.get("95%", "0")), 1)
        p99 = round(float(row.get("99%", "0")), 1)
        qps = round(float(row.get("Requests/s", "0")), 2)

        md_lines.append(
            f"| `{name}` | {req_count} | {fail_count} | {avg_lat} | {p50} | {p95} | {p99} | {qps} |"
        )

        if "/api/v1/ask" in name:
            ask_p95 = p95
        elif "/api/v1/search" in name:
            search_p95 = p95

    # Append total summary
    agg_row = next((r for r in rows if r.get("Name") == "Aggregated"), None)
    if agg_row:
        total_reqs = agg_row.get("Request Count", "0")
        total_fails = agg_row.get("Failure Count", "0")
        avg_qps = round(float(agg_row.get("Requests/s", "0")), 2)
        md_lines.append(
            f"\n**Aggregated Throughput:** {avg_qps} QPS "
            f"(Total: {total_reqs} requests, {total_fails} failures)\n"
        )

    # Perform SLO validations
    md_lines.append("## Service Level Objective (SLO) Status\n")
    slo_passed = True

    if ask_p95 is not None:
        passed = ask_p95 <= max_ask_p95_ms
        status = "✅ PASSED" if passed else "❌ FAILED"
        md_lines.append(
            f"* **RAG /ask P95 Latency SLO:** {status} ({ask_p95}ms / target <= {max_ask_p95_ms}ms)"
        )
        if not passed:
            slo_passed = False
    else:
        md_lines.append(
            "* **RAG /ask P95 Latency SLO:** ⚠️ NOT TESTED (no requests made to `/api/v1/ask`)"
        )

    if search_p95 is not None:
        passed = search_p95 <= max_search_p95_ms
        status = "✅ PASSED" if passed else "❌ FAILED"
        md_lines.append(
            f"* **Search /search P95 Latency SLO:** {status} "
            f"({search_p95}ms / target <= {max_search_p95_ms}ms)"
        )
        if not passed:
            slo_passed = False
    else:
        md_lines.append(
            "* **Search /search P95 Latency SLO:** ⚠️ NOT TESTED "
            "(no requests made to `/api/v1/search`)"
        )

    report_content = "\n".join(md_lines)
    print("\n" + "=" * 50)
    print(report_content)
    print("=" * 50)

    report_md_path = Path("data/eval/reports/load_test_report.md")
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"\nWritten Markdown report to {report_md_path}")

    if not slo_passed:
        print("\n❌ Load Test failed one or more SLO latency gates.")
        sys.exit(1)
    else:
        print("\n✅ Load Test PASSED all SLO latency gates.")
        sys.exit(0)


if __name__ == "__main__":
    main()
