# Load Test Performance Report

Generated from Locust stats: `data/eval/reports/load_test_stats.csv`

## Performance Metrics Summary

| Endpoint | Requests | Failures | Avg Latency (ms) | P50 (ms) | P95 (ms) | P99 (ms) | QPS |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `/api/v1/ask` | 11 | 0 | 8058.2 | 7100.0 | 12000.0 | 12000.0 | 0.38 |
| `/api/v1/search` | 4 | 0 | 1078.4 | 820.0 | 2000.0 | 2000.0 | 0.14 |
| `/health` | 1 | 0 | 2.8 | 3.0 | 3.0 | 3.0 | 0.03 |

**Aggregated Throughput:** 0.55 QPS (Total: 16 requests, 0 failures)

## Service Level Objective (SLO) Status

* **RAG /ask P95 Latency SLO:** ❌ FAILED (12000.0ms / target <= 5000.0ms)
* **Search /search P95 Latency SLO:** ❌ FAILED (2000.0ms / target <= 1000.0ms)