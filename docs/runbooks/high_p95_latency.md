# Runbook: High P95 Latency

## Alert Description
Triggers when the system's P95 request latency degrades beyond acceptable SLA thresholds:
- **Warning**: P95 > 6.0s over 5 minutes (indicating general performance degradation).
- **Critical**: P95 > 8.0s over 2 minutes (active SLA breach of the product requirements).

---

## Step-by-Step Diagnostic Procedure

### Step 1: Identify the Affected Endpoints
1. Open the **Request Health Dashboard** in Grafana (`http://localhost:3001`).
2. Look at the **P95/P99 latency by endpoint** panel.
3. Identify which endpoint (e.g., `/api/v1/ask` or `/api/v1/search`) is experiencing the latency spike.

### Step 2: Check Retrieval and Indexing Performance
1. Navigate to the **Retrieval Performance Dashboard** in Grafana.
2. Check the **Retrieval Latency by Method** panel.
3. Look for a spike in Qdrant query time or query embedding latency.
4. Spikes here could indicate Qdrant disk I/O saturation or external embedding API throttling.

### Step 3: Check Generation / LLM Serving Performance
1. Navigate to the **Generation Performance Dashboard** in Grafana.
2. Check the **LLM Request Latency** panel.
3. If Vertex AI or an alternative serving backend is taking unusually long, check the **LLM error rate** and quotas on the Google Cloud Console.
4. Verify if model routing has switched to a heavier model or if caching is disabled.

### Step 4: Analyze Distributed Traces in Jaeger
1. Open Jaeger UI (`http://localhost:16686`).
2. Select the `enterprise-knowledge-copilot` service.
3. Search for traces with high duration matching the affected endpoint.
4. Inspect the breakdown of spans to find the exact bottleneck:
   - `retrieval.embed_query`
   - `retrieval.qdrant_query`
   - `reranking.score`
   - `generation.llm_call`

### Step 5: Check for Connection Timeouts
1. In Prometheus (`http://localhost:9090`) or the **System Failures Dashboard**, search for `system_timeout_total`.
2. Determine if the timeouts are occurring on the embedding client, database connections, or the NeMo Guardrails microservice.

---

## Mitigation Options

1. **Adjust Model Routing Config**: If a heavy model is slowing down responses under load, modify `configs/models.yaml` to adjust the SLO tier settings or lower thresholds.
2. **Reduce Retrieval Depth**: Lower the default `top_k` / `limit` value in `/api/v1/ask` or `/api/v1/search` requests.
3. **Scale Resource Allocations**: If Qdrant search is bottlenecked, verify CPU and memory limits on the Qdrant container, and optimize vector index search parameters (e.g. `hnsw`).
4. **Enable/Warm Cache**: Ensure cache is enabled (`CACHE_ENABLED=true` in `.env`) and check Redis status.
