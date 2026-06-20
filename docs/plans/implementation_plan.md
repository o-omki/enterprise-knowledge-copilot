# Phase 9: Observability and Reliability

> Make the system inspectable and operationally mature.

## Background

Phases 1–8 built a complete RAG pipeline: ingestion → hybrid retrieval → reranking → multi-agent query planning → generation → safety guardrails → evaluation harness → UI → LLM serving optimization. The system already has:

- **Minimal tracing**: [tracing.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/observability/tracing.py) sets up an OTLP span exporter → Jaeger and auto-instruments FastAPI. The [orchestrator](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/agents/orchestrator.py) creates manual spans for query routing, search, aggregation, and synthesis.
- **Partial metrics**: [metrics.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/llm_serving/metrics.py) and [cost_tracker.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/llm_serving/cost_tracker.py) define OTEL counters/histograms for LLM requests — but there is **no metrics exporter configured**, so these counters are silently dropped.
- **Ad-hoc logging**: Every module uses `logging.basicConfig(level=logging.INFO)` or `logging.getLogger(__name__)` with unstructured `f"..."` messages. There is no structured JSON format, no `request_id` / `session_id` correlation, no centralized configuration.
- **No Prometheus, Grafana, dashboards, or alerts**.

Phase 9 closes all of these gaps.

---

## Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| Monitoring stack | **Prometheus + Grafana** | Industry-standard OSS stack, consistent with roadmap |
| Structured logging library | **`structlog`** | Python industry standard; auto context binding, stdlib integration |
| Alert architecture | **Multi-tier (Warning + Critical)** | Prevents alert fatigue; Warning for triage, Critical for SLA breach |
| Jaeger persistence | **Deferred to Phase 10** | In-memory `all-in-one` sufficient for dev; Badger/ES in Phase 10 |
| Log aggregation backend | **Loki in Phase 10** | Structured JSON → stdout is sufficient for local dev now |
| `/metrics` endpoint auth | **Unauthenticated** for Docker Compose dev | Network-isolate or auth-gate in production (Phase 10) |

> [!NOTE]
> **Loki vs Jaeger clarification**: Loki is a log aggregation system (collects structured log output). Jaeger is a distributed tracing backend (collects spans/traces). They are complementary, not interchangeable. Phase 10 will add **Loki for log aggregation** and **Badger/ES for Jaeger persistent trace storage** together.

---

## Proposed Changes

### Epic 1: Structured Logging Overhaul

Replace all unstructured `f"..."` logging with `structlog` JSON-formatted output. Add automatic context propagation for `request_id`, `session_id`, `trace_id`, `query_type`, and `model_name`.

#### [NEW] `packages/observability/logging.py`
- Central logging configuration module:
  - Configure `structlog` with JSON renderer for production, colored console renderer for development (controlled by `LOG_FORMAT` env var: `json` | `console`)
  - Create `configure_logging(service_name, log_level)` called once at app startup
  - Add `structlog` context processors: timestamp (ISO 8601), log level, logger name, stack info, OpenTelemetry trace/span ID injection
  - Add a `bind_request_context(request_id, session_id, ...)` helper for middleware to call per-request

#### [NEW] `apps/api/app/middleware/request_context.py`
- New middleware that runs first (outermost) in the middleware stack:
  - Generates `request_id` (UUID) if not present in `X-Request-ID` header
  - Extracts `session_id` from request body (for `/ask` endpoint) or sets `"none"`
  - Binds `request_id`, `session_id`, `path`, `method` to `structlog` thread-local context
  - Sets `request_id` on `request.state` for downstream use
  - Logs `request.started` and `request.completed` events with latency

#### [MODIFY] [main.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/api/app/main.py)
- Replace `logging.basicConfig(level=logging.INFO)` with `configure_logging("api", settings.log_level)`
- Add `RequestContextMiddleware` as outermost middleware
- Replace all `logger.info(f"...")` calls with structured `logger.info("event_name", param=value)` format

#### [MODIFY] [orchestrator.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/agents/orchestrator.py)
- Replace `logging.getLogger` with `structlog.get_logger`
- Add structured event names: `orchestrator.query.started`, `orchestrator.routing.completed`, `orchestrator.search.completed`, `orchestrator.synthesis.completed`
- Bind `query_type`, `sub_query_count`, `chunks_retrieved`, `model_name` as structured fields

#### [MODIFY] [search.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/rag/search.py)
- Replace logger with structlog
- Log `retrieval.started`, `retrieval.completed` with `method`, `domain`, `doc_type`, `result_count`, `latency_ms`

#### [MODIFY] [reranker.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/rag/reranker.py)
- Replace logger with structlog
- Log `reranking.started`, `reranking.completed` with `candidate_count`, `top_k`, `latency_ms`

#### [MODIFY] [generation.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/rag/generation.py)
- Replace logger with structlog
- Log `generation.started`, `generation.completed`, `generation.failed` with `model`, `prompt_tokens`, `context_length`

#### [MODIFY] [client.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/llm_serving/client.py)
- Replace logger references with structlog
- Log `llm.request.started`, `llm.request.completed`, `llm.request.cached`, `llm.request.failed` with `model`, `backend`, `latency_s`, `token_count`

#### [MODIFY] [circuit_breaker.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/llm_serving/circuit_breaker.py)
- Replace logger with structlog
- Log `circuit_breaker.state_change` with `from_state`, `to_state`, `failure_count`

#### [MODIFY] [ingestion.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/rag/ingestion.py)
- Replace logger with structlog
- Log `ingestion.batch.started`, `ingestion.batch.completed`, `ingestion.collection.initialized` with `collection`, `batch_size`, `chunk_count`

#### [MODIFY] [tasks.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/worker/tasks.py)
- Replace logger with structlog
- Log `worker.ingest.started`, `worker.ingest.completed`, `worker.ingest.failed` with `file_path`, `chunks_indexed`, `retry_count`

#### [MODIFY] [guardrails main.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/guardrails/main.py)
- Replace logger with structlog
- Add `configure_logging("guardrails", ...)` at startup
- Log `guardrails.input.validated`, `guardrails.output.validated`, `guardrails.blocked` with `is_safe`, `is_off_topic`, `is_grounded`

#### [MODIFY] [safety middleware](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/api/app/middleware/safety.py)
- Replace logger with structlog
- Log `safety.input.checked`, `safety.output.checked`, `safety.blocked` with `reason`, `latency_ms`

#### [MODIFY] [auth middleware](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/api/app/middleware/auth.py)
- Replace logger with structlog
- Log `auth.authenticated`, `auth.rejected` with `auth_type`, `user_id`, `api_key_id`

#### [MODIFY] [rate_limiter middleware](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/api/app/middleware/rate_limiter.py)
- Replace logger with structlog
- Log `rate_limiter.allowed`, `rate_limiter.throttled` with `key`, `limit`, `remaining`

---

### Epic 2: Distributed Tracing Instrumentation

Extend tracing coverage from the orchestrator to every pipeline stage. Ensure end-to-end trace continuity from API request → safety → routing → retrieval → reranking → generation → response.

#### [MODIFY] [tracing.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/observability/tracing.py)
- Add `service.version` and `deployment.environment` resource attributes
- Add `SpanProcessor` configuration for sampling (always-on for dev, probabilistic for production via `OTEL_TRACES_SAMPLER` env var)
- Export the `meter` setup here too (see Epic 3) so both traces and metrics share the same `Resource`

#### [MODIFY] [__init__.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/observability/__init__.py)
- Re-export new symbols: `configure_logging`, `bind_request_context`, `get_meter`

#### [MODIFY] [search.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/rag/search.py)
- Add spans: `retrieval.embed_query`, `retrieval.qdrant_query`
- Set span attributes: `retrieval.method`, `retrieval.result_count`, `retrieval.latency_ms`, `retrieval.collection`

#### [MODIFY] [reranker.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/rag/reranker.py)
- Add span: `reranking.score`
- Set span attributes: `reranking.candidate_count`, `reranking.top_k`, `reranking.latency_ms`, `reranking.model`

#### [MODIFY] [generation.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/rag/generation.py)
- Add spans: `generation.build_prompt`, `generation.llm_call`
- Set span attributes: `generation.model`, `generation.context_passages`, `generation.prompt_length`

#### [MODIFY] [client.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/llm_serving/client.py)
- Add span: `llm.generate` wrapping the full `generate()` call
- Set span attributes: `llm.model`, `llm.backend`, `llm.cached`, `llm.tokens.total`, `llm.latency_s`
- Record span status ERROR on exceptions

#### [MODIFY] [safety middleware](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/api/app/middleware/safety.py)
- Add spans: `safety.input_validation`, `safety.output_validation`
- Set span attributes: `safety.is_safe`, `safety.is_grounded`, `safety.blocked`, `safety.latency_ms`

#### [MODIFY] [ingestion.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/rag/ingestion.py)
- Add spans: `ingestion.load_documents`, `ingestion.chunk_documents`, `ingestion.embed_batch`, `ingestion.upsert_batch`
- Set span attributes: `ingestion.doc_count`, `ingestion.chunk_count`, `ingestion.batch_index`

#### [MODIFY] [guardrails main.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/guardrails/main.py)
- Call `setup_tracing(app, service_name="guardrails")` in lifespan
- Add spans to `validate_input` and `validate_output` endpoints

---

### Epic 3: Prometheus Metrics Exporter & Custom Application Counters

Wire up an OTEL metrics exporter to Prometheus. Define domain-specific counters, histograms, and gauges that cover every signal listed in [observability.md](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/docs/observability.md).

#### [NEW] `packages/observability/metrics.py`
Central metrics module defining all application metrics using the OpenTelemetry Metrics API:

**Request metrics:**
- `http.server.request.duration` (histogram, seconds) — from FastAPI auto-instrumentation
- `http.server.request.total` (counter) — by endpoint, method, status_code
- `http.server.active_requests` (up/down counter) — concurrent request gauge

**Retrieval metrics:**
- `retrieval.request.duration` (histogram, seconds) — by method (dense/sparse/hybrid)
- `retrieval.request.total` (counter) — by method, domain
- `retrieval.result.count` (histogram) — distribution of result set sizes
- `retrieval.hit.quality` (histogram) — top-1 score distribution

**Reranking metrics:**
- `reranking.request.duration` (histogram, seconds)
- `reranking.request.total` (counter)
- `reranking.candidate.count` (histogram)

**Generation metrics:**
- `generation.request.duration` (histogram, seconds)
- `generation.request.total` (counter) — by model, status
- `generation.token.count` (histogram) — prompt + completion tokens

**Safety metrics:**
- `safety.check.duration` (histogram, seconds) — by check_type (input/output)
- `safety.check.total` (counter) — by check_type, result (allowed/blocked)
- `safety.block.total` (counter) — by reason (jailbreak/off_topic/hallucination/pii)

**Ingestion metrics:**
- `ingestion.task.duration` (histogram, seconds)
- `ingestion.task.total` (counter) — by status (completed/failed)
- `ingestion.chunk.count` (counter) — total chunks indexed

**LLM serving metrics (enhance existing):**
- Keep existing `llm.requests.total`, `llm.request.duration`, `llm.tokens.total`, `llm.requests.errors`
- Add `llm.cache.hit.total` (counter) — cache hit/miss ratio
- Add `llm.circuit_breaker.state` (gauge: 0=closed, 1=half_open, 2=open)
- Add `llm.cost.total_usd` — already exists in cost_tracker

**System metrics:**
- `system.uptime_seconds` (gauge) — process uptime

#### [MODIFY] [tracing.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/observability/tracing.py)
- Add `PrometheusMetricReader` setup:
  - Configure `opentelemetry-exporter-prometheus` to serve via a WSGI app
  - Create a shared `MeterProvider` with the same `Resource` as the `TracerProvider`
- Keep `setup_tracing()` name but extend it to also configure the metrics pipeline

#### [NEW] Route or mount for `/metrics` endpoint
- Mount `prometheus_client` WSGI app on FastAPI at `/metrics` so it shares the same port (no separate port, unauthenticated for dev)

#### [MODIFY] pipeline modules
Instrument each module to record the metrics defined above at the appropriate call sites:
- [search.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/rag/search.py) — record `retrieval.*` metrics
- [reranker.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/rag/reranker.py) — record `reranking.*` metrics
- [generation.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/rag/generation.py) — record `generation.*` metrics
- [client.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/llm_serving/client.py) — record `llm.cache.*` metrics
- [safety middleware](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/api/app/middleware/safety.py) — record `safety.*` metrics
- [tasks.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/worker/tasks.py) — record `ingestion.*` metrics

---

### Epic 4: Grafana Dashboards

Provision pre-built Grafana dashboards via JSON provisioning files and Docker Compose.

#### [NEW] `infra/monitoring/prometheus/prometheus.yml`
Prometheus scrape configuration:
- Scrape API service at `api:8000/metrics` every 15s
- Scrape guardrails service at `guardrails:8001/metrics` every 15s
- Job labels: `api`, `guardrails`

#### [NEW] `infra/monitoring/grafana/provisioning/datasources/prometheus.yml`
Auto-provision Prometheus as a Grafana datasource pointing to `http://prometheus:9090`.

#### [NEW] `infra/monitoring/grafana/provisioning/dashboards/dashboard.yml`
Dashboard provisioning config pointing to the JSON files below.

#### [NEW] `infra/monitoring/grafana/dashboards/01-request-health.json`
**Request Health Dashboard** — panels:
- Request rate (RPM) by endpoint
- P50/P95/P99 latency by endpoint
- Error rate (4xx, 5xx) by endpoint
- Active concurrent requests gauge
- Request duration heatmap

#### [NEW] `infra/monitoring/grafana/dashboards/02-retrieval-performance.json`
**Retrieval Performance Dashboard** — panels:
- Retrieval latency by method (dense/sparse/hybrid)
- Retrieval result count distribution
- Top-1 score distribution
- Retrieval request rate by domain
- Reranking latency overlay

#### [NEW] `infra/monitoring/grafana/dashboards/03-generation-performance.json`
**Generation Performance Dashboard** — panels:
- LLM request latency (P50/P95/P99) by model
- Token count distribution (prompt vs completion)
- LLM error rate by error type
- Cache hit rate (%)
- Circuit breaker state timeline
- Estimated cost per hour (USD)

#### [NEW] `infra/monitoring/grafana/dashboards/04-safety.json`
**Safety Dashboard** — panels:
- Safety check latency (input vs output)
- Block rate by reason (jailbreak/off-topic/hallucination/PII)
- False positive tracking (manual annotation point)
- Safety check throughput

#### [NEW] `infra/monitoring/grafana/dashboards/05-system-failures.json`
**System Failures Dashboard** — panels:
- Error count by service and error_type
- Timeout rate timeline
- Circuit breaker state changes
- Ingestion failure rate
- Worker task retry rate
- Service uptime

#### [MODIFY] [docker-compose.yml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/docker-compose.yml)
Add 2 new services:
```yaml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./infra/monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    - ./infra/monitoring/prometheus/alert_rules.yml:/etc/prometheus/alert_rules.yml:ro
  ports:
    - "9090:9090"
  depends_on:
    - api

grafana:
  image: grafana/grafana:latest
  volumes:
    - ./infra/monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
    - ./infra/monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
  ports:
    - "3001:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
    - GF_AUTH_ANONYMOUS_ENABLED=true
    - GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer
  depends_on:
    - prometheus
```

---

### Epic 5: Failure Rate & Timeout Pattern Tracking

Add explicit tracking for failure modes and timeout patterns across all services.

#### [NEW] `packages/observability/failure_tracker.py`
- `FailureTracker` class with methods:
  - `record_failure(component, error_type, details)` — increments error counter and logs structured error event
  - `record_timeout(component, operation, timeout_sec, elapsed_sec)` — increments timeout counter
  - `record_retry(component, operation, attempt, max_retries)` — increments retry counter
- Metrics defined:
  - `system.failure.total` (counter) — by `component`, `error_type`
  - `system.timeout.total` (counter) — by `component`, `operation`
  - `system.retry.total` (counter) — by `component`, `operation`, `attempt`

#### [MODIFY] [circuit_breaker.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/llm_serving/circuit_breaker.py)
- Emit `system.failure.total` and `system.timeout.total` events when failures occur
- Record span events for state transitions

#### [MODIFY] [client.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/packages/llm_serving/client.py)
- Use `FailureTracker` to record LLM failures with detailed error type classification

#### [MODIFY] [safety middleware](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/api/app/middleware/safety.py)
- Track timeout patterns when guardrails service is slow/unavailable
- Record fallback-to-local events

#### [MODIFY] [tasks.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/worker/tasks.py)
- Use `FailureTracker` to record ingestion failures and retries with structured context

---

### Epic 6: Alerting Rules & Runbooks

Define Prometheus alerting rules using a **multi-tier architecture** (Warning + Critical) and operational runbooks for key failure scenarios.

> [!IMPORTANT]
> **Multi-tier alert rationale**: Using flat thresholds introduces alert fatigue. Warning alerts use wider evaluation windows (5m) to smooth transient anomalies for business-hours triage. Critical alerts use tight windows (2–3m) because sustained violations signal an active incident requiring immediate intervention.

#### [NEW] `infra/monitoring/prometheus/alert_rules.yml`

```yaml
groups:
  - name: rag_latency_alerts
    rules:
      # --- Latency ---
      - alert: HighP95LatencyWarning
        expr: >
          histogram_quantile(0.95,
            sum(rate(http_server_request_duration_seconds_bucket[5m])) by (le)
          ) > 6.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency is degrading (Currently > 6s)"
          description: >
            Pipeline latency is creeping up. Check if Vertex AI is throttling
            token budgets or if Qdrant disk I/O is saturated.
          runbook: "docs/runbooks/high_p95_latency.md"

      - alert: CriticalP95LatencyBreach
        expr: >
          histogram_quantile(0.95,
            sum(rate(http_server_request_duration_seconds_bucket[3m])) by (le)
          ) > 8.0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Critical P95 SLA Breach (Currently > 8s)"
          description: >
            The system is actively failing user product requirements.
            Immediate intervention required.
          runbook: "docs/runbooks/high_p95_latency.md"

  - name: rag_error_alerts
    rules:
      # --- Error Rate ---
      - alert: HighErrorRateWarning
        expr: >
          rate(http_server_request_total{status=~"5.."}[5m])
          / rate(http_server_request_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "5xx error rate exceeding 5%"

      - alert: CriticalErrorRate
        expr: >
          rate(http_server_request_total{status=~"5.."}[3m])
          / rate(http_server_request_total[3m]) > 0.10
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "5xx error rate exceeding 10% — active incident"

  - name: rag_infrastructure_alerts
    rules:
      # --- Timeouts ---
      - alert: RisingTimeoutRate
        expr: rate(system_timeout_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Timeout rate is increasing across services"

      # --- Ingestion ---
      - alert: IngestionFailureSpike
        expr: rate(ingestion_task_total{status="failed"}[10m]) > 0.3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Ingestion failure rate is spiking"
          runbook: "docs/runbooks/ingestion_failures.md"

      # --- Circuit Breaker ---
      - alert: ModelServingDegraded
        expr: llm_circuit_breaker_state > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "LLM circuit breaker is OPEN or HALF_OPEN"
          runbook: "docs/runbooks/circuit_breaker_open.md"

      # --- Vector DB ---
      - alert: VectorDBConnectivity
        expr: >
          rate(system_failure_total{component="retrieval",
            error_type="connection_error"}[5m]) > 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Qdrant vector DB connectivity failure detected"
          runbook: "docs/runbooks/vector_db_connectivity.md"

  - name: rag_safety_alerts
    rules:
      # --- Safety ---
      - alert: HighSafetyBlockRate
        expr: rate(safety_block_total[5m]) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Safety block rate unusually high — possible attack or false positive spike"
          runbook: "docs/runbooks/safety_block_spike.md"

      # --- Cache ---
      - alert: CacheHitRateDrop
        expr: >
          rate(llm_cache_hit_total{hit="true"}[10m])
          / rate(llm_cache_hit_total[10m]) < 0.10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "LLM response cache hit rate dropped below 10%"
```

#### [NEW] `docs/runbooks/high_p95_latency.md`
Runbook covering:
- Step 1: Open the **Request Health** Grafana dashboard → identify which endpoint is slow
- Step 2: Open the **Retrieval Performance** dashboard → check if retrieval latency spiked (Qdrant I/O, embedding API throttling)
- Step 3: Open the **Generation Performance** dashboard → check LLM latency (Vertex AI quotas, model warmup)
- Step 4: Check Jaeger traces for the slowest recent requests → identify the bottleneck span
- Step 5: Check Prometheus for `system.timeout.total` → rule out network timeouts
- Step 6: Mitigation options (scale Qdrant, switch to lighter model via router, reduce `top_k`)

#### [NEW] `docs/runbooks/circuit_breaker_open.md`
Runbook covering:
- Check LLM backend health (Vertex AI status, vLLM container)
- Review structured error logs filtered by `llm.request.failed`
- Check failure count and recovery timeout configuration
- Mitigation: manual circuit breaker reset, model routing failover, cache warm-up

#### [NEW] `docs/runbooks/ingestion_failures.md`
Runbook covering:
- Check Celery worker logs for task errors
- Check Qdrant connectivity and disk space
- Check embedding API quotas (Vertex AI)
- Check file format and encoding issues
- Mitigation: retry failed tasks, re-ingest from source

#### [NEW] `docs/runbooks/vector_db_connectivity.md`
Runbook covering:
- Check Docker container status (`docker compose ps qdrant`)
- Check Qdrant logs and disk utilization
- Restart procedure and data recovery
- Verify collection health post-recovery

#### [NEW] `docs/runbooks/safety_block_spike.md`
Runbook covering:
- Review blocked queries in structured logs (`safety.blocked` events)
- Distinguish attack patterns vs. false positives (legitimate queries blocked)
- Check if NeMo Guardrails engine is erroring (triggering false blocks)
- Tune thresholds in Colang config if false positive rate is elevated

---

### Epic 7: Dependencies, Configuration, and Documentation

#### [MODIFY] [pyproject.toml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/pyproject.toml)
Add new dependencies:
```
"structlog>=24.1.0",
"opentelemetry-exporter-prometheus>=0.45b0",
"opentelemetry-instrumentation-redis>=0.45b0",
"opentelemetry-instrumentation-sqlalchemy>=0.45b0",
"opentelemetry-instrumentation-celery>=0.45b0",
"opentelemetry-instrumentation-httpx>=0.45b0",
"prometheus-client>=0.20.0",
```

#### [MODIFY] [.env.example](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/.env.example)
Add new environment variables:
```
# Observability
LOG_FORMAT=json          # json | console
LOG_LEVEL=INFO
OTEL_SERVICE_NAME=enterprise-knowledge-copilot
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_EXPORTER_OTLP_INSECURE=true
OTEL_TRACES_SAMPLER=always_on
METRICS_ENABLED=true
```

#### [MODIFY] [docker-compose.yml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/docker-compose.yml)
- Add `prometheus` and `grafana` services (detailed in Epic 4)
- Add `OTEL_*` and `LOG_FORMAT` env vars to `api`, `guardrails`, and `worker` services

#### [MODIFY] [Makefile](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/Makefile)
Add targets:
```makefile
dashboards:
	@echo "Grafana: http://localhost:3001 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo "Jaeger: http://localhost:16686"

observability-check:
	@echo "Checking observability stack health..."
	curl -sf http://localhost:9090/-/healthy && echo "Prometheus: OK" || echo "Prometheus: FAIL"
	curl -sf http://localhost:3001/api/health && echo "Grafana: OK" || echo "Grafana: FAIL"
	curl -sf http://localhost:16686/ && echo "Jaeger: OK" || echo "Jaeger: FAIL"
```

#### [NEW] `docs/adr/0018-observability-stack.md`
ADR documenting the observability stack choices:
- Structured logging: `structlog` with JSON output → stdout (Loki aggregation in Phase 10)
- Tracing: OpenTelemetry SDK → OTLP → Jaeger in-memory (persistent Badger/ES in Phase 10)
- Metrics: OpenTelemetry SDK → Prometheus exporter
- Dashboards: Grafana with auto-provisioned dashboards
- Alerting: Prometheus alert rules with multi-tier Warning/Critical severity
- Alertmanager integration: out of scope for local dev (Phase 10)

#### [MODIFY] [docs/observability.md](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/docs/observability.md)
Expand with:
- Architecture diagram of the observability stack
- Links to Grafana dashboards with descriptions
- Guide to reading traces in Jaeger
- Guide to querying Prometheus
- Link to runbook index
- Phase 10 roadmap (Loki log aggregation, Jaeger persistence, Alertmanager)

#### [MODIFY] [docs/milestones.md](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/docs/milestones.md)
Add Phase 9 epic checklist and sign-off section.

#### [MODIFY] [project_structure.md](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/project_structure.md)
Add the new `infra/monitoring/` directory tree.

#### Bump version in [pyproject.toml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/pyproject.toml) and [main.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/api/app/main.py) from `0.6.0` → `0.9.0`.

---

## File Change Summary

### New Files (19)

| File | Purpose |
|---|---|
| `packages/observability/logging.py` | Structured logging configuration with structlog |
| `packages/observability/metrics.py` | Central application metrics definitions |
| `packages/observability/failure_tracker.py` | Failure/timeout/retry pattern tracking |
| `apps/api/app/middleware/request_context.py` | Request context binding middleware |
| `infra/monitoring/prometheus/prometheus.yml` | Prometheus scrape config |
| `infra/monitoring/prometheus/alert_rules.yml` | Multi-tier alerting rules |
| `infra/monitoring/grafana/provisioning/datasources/prometheus.yml` | Grafana datasource provisioning |
| `infra/monitoring/grafana/provisioning/dashboards/dashboard.yml` | Grafana dashboard provisioning |
| `infra/monitoring/grafana/dashboards/01-request-health.json` | Request health dashboard |
| `infra/monitoring/grafana/dashboards/02-retrieval-performance.json` | Retrieval performance dashboard |
| `infra/monitoring/grafana/dashboards/03-generation-performance.json` | Generation/LLM dashboard |
| `infra/monitoring/grafana/dashboards/04-safety.json` | Safety dashboard |
| `infra/monitoring/grafana/dashboards/05-system-failures.json` | System failures dashboard |
| `docs/adr/0018-observability-stack.md` | Architecture Decision Record |
| `docs/runbooks/high_p95_latency.md` | Latency runbook |
| `docs/runbooks/circuit_breaker_open.md` | Circuit breaker runbook |
| `docs/runbooks/ingestion_failures.md` | Ingestion failure runbook |
| `docs/runbooks/vector_db_connectivity.md` | Vector DB connectivity runbook |
| `docs/runbooks/safety_block_spike.md` | Safety block spike runbook |

### Modified Files (22)

| File | Nature of Change |
|---|---|
| `packages/observability/__init__.py` | Re-export new symbols |
| `packages/observability/tracing.py` | Add metrics exporter, resource attributes, Prometheus reader |
| `apps/api/app/main.py` | Structured logging, request context middleware, metrics endpoint, version bump |
| `apps/guardrails/main.py` | Structured logging, tracing setup, span instrumentation |
| `packages/agents/orchestrator.py` | Structured logging |
| `packages/rag/search.py` | Structured logging, tracing spans, metrics recording |
| `packages/rag/reranker.py` | Structured logging, tracing spans, metrics recording |
| `packages/rag/generation.py` | Structured logging, tracing spans, metrics recording |
| `packages/rag/ingestion.py` | Structured logging, tracing spans, metrics recording |
| `packages/llm_serving/client.py` | Structured logging, tracing spans, cache metrics |
| `packages/llm_serving/circuit_breaker.py` | Structured logging, failure tracking |
| `apps/api/app/middleware/safety.py` | Structured logging, tracing spans, safety metrics |
| `apps/api/app/middleware/auth.py` | Structured logging |
| `apps/api/app/middleware/rate_limiter.py` | Structured logging |
| `apps/worker/tasks.py` | Structured logging, failure tracking |
| `docker-compose.yml` | Add Prometheus, Grafana, env vars |
| `pyproject.toml` | Add dependencies, bump version |
| `.env.example` | Add observability env vars |
| `Makefile` | Add observability targets |
| `docs/observability.md` | Expand documentation |
| `docs/milestones.md` | Add Phase 9 checklist |
| `project_structure.md` | Add infra/monitoring tree |

---

## Verification Plan

### Automated Tests

#### Unit Tests
```bash
# Test structured logging configuration
PYTHONPATH=. python -m pytest apps/api/tests/test_logging.py -v

# Test metrics definitions and recording
PYTHONPATH=. python -m pytest packages/observability/tests/test_metrics.py -v

# Test failure tracker
PYTHONPATH=. python -m pytest packages/observability/tests/test_failure_tracker.py -v

# Test request context middleware
PYTHONPATH=. python -m pytest apps/api/tests/test_request_context.py -v

# Existing test suite (regression check)
make test
```

#### Integration Tests
```bash
# Start the full stack
docker compose up -d

# Verify Prometheus is scraping targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].health'
# Expected: all "up"

# Verify Grafana datasource is provisioned
curl -s http://localhost:3001/api/datasources | jq '.[].name'
# Expected: "Prometheus"

# Verify dashboards are provisioned
curl -s http://localhost:3001/api/search?type=dash-db | jq '.[].title'
# Expected: 5 dashboard titles

# Verify /metrics endpoint returns Prometheus format
curl -s http://localhost:8000/metrics | head -20

# Fire a test query and verify trace appears in Jaeger
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key" \
  -d '{"query": "What is FastAPI?"}'

# Check Jaeger for the trace
curl -s "http://localhost:16686/api/traces?service=enterprise-knowledge-copilot&limit=1" \
  | jq '.data[0].spans | length'
# Expected: multiple spans covering the full pipeline
```

### Manual Verification
- Open Grafana at `http://localhost:3001` → verify all 5 dashboards load and show data
- Open Jaeger at `http://localhost:16686` → verify traces show full pipeline spans
- Open Prometheus at `http://localhost:9090` → verify targets are UP and metrics are queryable
- Check `docker compose logs api | head -5` → verify structured JSON log format
- Fire queries with various error modes (bad model name, Qdrant down) → verify failure metrics increment

### Lint & Type Check
```bash
make lint
make type-check
```

---

## Execution Order

1. **Epic 7 (partial)**: Add dependencies to `pyproject.toml` and install
2. **Epic 1**: Structured logging overhaul (foundation that everything else depends on)
3. **Epic 2**: Distributed tracing instrumentation
4. **Epic 3**: Prometheus metrics exporter & custom counters
5. **Epic 4**: Grafana dashboards & Docker Compose changes
6. **Epic 5**: Failure rate & timeout tracking
7. **Epic 6**: Alerting rules & runbooks
8. **Epic 7 (remaining)**: ADR, docs, milestones, version bump

---

## Phase 10 Handoff Notes

The following observability items are explicitly deferred to Phase 10 (Deployment & Cloud Infrastructure):

| Item | Phase 10 Scope |
|---|---|
| **Loki** | Deploy Grafana Loki + Promtail/Alloy to aggregate structured JSON logs from all services |
| **Jaeger persistence** | Replace in-memory storage with Badger or Elasticsearch for durable trace retention |
| **Alertmanager** | Deploy Prometheus Alertmanager with notification channels (Slack, PagerDuty, email) |
| **`/metrics` auth** | Network-isolate or add bearer token auth to Prometheus scrape endpoints |
| **Dashboard persistence** | Move Grafana from ephemeral to persistent volume for saved annotations and custom dashboards |
