# Model Serving and Performance Benchmarking

This guide explains the architecture, configurations, and evaluation tools used for LLM serving, parameter tuning, and load testing.

---

## 1. Model Serving Architecture

All LLM queries in the Enterprise Knowledge Copilot pass through a unified abstraction layer:

```
[Service Call] ➔ [Model Router] ➔ [Response Cache] ➔ [Circuit Breaker] ➔ [LLM Backend]
```

### 1.1 Core Components
* **LLM Client (`LLMClient`):** The primary class utilized by RAG and agent services to execute generations. Handled in `packages/llm_serving/client.py`.
* **Model Router (`ModelRouter`):** Dynamically maps queries to the most cost-effective model that satisfies the query's capability requirements and SLO constraints (e.g. latency, cost, quality).
* **Response Cache (`ResponseCache`):** A Redis-backed cache storing query signatures to bypass LLM generation for identical repeated requests.
* **Circuit Breaker (`CircuitBreaker`):** Implements CLOSED ➔ OPEN state transitions when backend failures exceed threshold limits, preventing cascading failures.

---

## 2. Configuration Files

### 2.1 Model Profiles (`configs/models.yaml`)
Registers available serving models and metadata:
```yaml
models:
  gemini-3.1-flash-lite:
    capabilities: [routing, fast_search]
    max_input_tokens: 32768
    cost_per_1k_input: 0.00025
    cost_per_1k_output: 0.0015
    latency_tier: ultra-fast
```

### 2.2 Prompt Configurations (`configs/prompts.yaml`)
Manages systemic prompts for RAG generation variants (`baseline`, `concise`, `detailed`):
```yaml
rag:
  generation:
    concise:
      system_instruction: "Provide highly concise, direct answers based strictly on the provided documents."
```

### 2.3 Evaluation Config (`configs/evals.yaml`)
Defines dataset paths, evaluation models, parameter sweep grids, and regression thresholds.

---

## 3. Benchmark Harness CLI

We use a CLI to run isolated evaluations of retrieval, generation, safety, latency, and serving metrics.

### 3.1 Run Serving Runner
Evaluates ModelRouter mapping correctness, cache hit rate calculations, and circuit breaker trip gates:
```bash
make eval-serving
```

### 3.2 Run Sweep Matrix
Executes an offline parameter grid search across `top_k` and `prompt_versions` to locate the optimal configuration:
```bash
PYTHONPATH=. python scripts/optimization_sweep.py
```

### 3.3 A/B Compare Runs
Performs a delta analysis on two scorecard JSON reports using our **Tiered Evaluation Matrix** (Trust ➔ Value ➔ Efficiency):
```bash
PYTHONPATH=. python scripts/ab_comparison.py --baseline report_A.json --candidate report_B.json
```

---

## 4. Load Testing Infrastructure

We use Locust to simulate concurrent user traffic and measure P95 latency and QPS throughput bounds.

### 4.1 CLI Headless Run
Triggers a headless 30-second test simulating concurrent users:
```bash
make load-test
```

### 4.2 Generate Performance Report
Parses Locust stats, checks compliance against SLO targets (`/ask` P95 <= 5s, `/search` P95 <= 1s), and writes a Markdown summary:
```bash
make load-test-report
```

### 4.3 Run via Docker Compose
We can launch the interactive Locust Web UI (on port `8089`) alongside the API container:
```bash
docker-compose up locust
```
Open [http://localhost:8089](http://localhost:8089) in your browser to run interactive load tests.
