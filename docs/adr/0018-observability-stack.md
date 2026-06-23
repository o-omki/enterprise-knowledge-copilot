# ADR 0018: Observability and Reliability Stack

**Status:** Accepted
**Date:** 2026-06-21

## Context and Problem Statement
Our enterprise RAG copilot has grown from a simple query pipeline into a complex multi-agent system with hybrid search, reranking, safety guardrails, caching, and background workers. To run this system reliably in production, we need deep observability:
1. **JSON Structured Logs**: Enable automated log parsing and correlation across services.
2. **Distributed Tracing**: Visualize end-to-end flow of requests from the API down to retrieval, reranking, and generation.
3. **Application Metrics**: Collect counters, histograms, and gauges covering latency, errors, cache hits, queue metrics, and circuit breaker states.
4. **Alerts & Dashboards**: Provide visual health tracking and active alerts with clear mitigation procedures.

## Decision
We implemented a self-contained local observability stack using open-source, industry-standard tools:

1. **Structured Logging**: Configured `structlog` for Python services. It formats logs as JSON for stdout (ready for Loki/Fluentd aggregation) or pretty-colored text for developer console rendering. Logs inject context attributes like `request_id`, `session_id`, `trace_id`, and `span_id`.
2. **Distributed Tracing**: Set up OpenTelemetry (OTel) SDK. Spans auto-instrument FastAPI and Celery workers, and we added manual instrumentation covering core components (retrieval, reranking, generation, safety). Spans export to a local **Jaeger** instance over gRPC (OTLP).
3. **Prometheus Metrics**: Configured OpenTelemetry Metrics API and configured a `PrometheusMetricReader` to export application metrics. We mounted the Prometheus WSGI/ASGI application under `/metrics` on our FastAPI services.
4. **Scraping & Dashboards**: Configured a local **Prometheus** server in Docker Compose to scrape `/metrics` from all containers, and provisioned **Grafana** with 5 pre-built dashboards (Request Health, Retrieval, Generation/LLM, Safety, System Failures) and Prometheus alerting rules (`alert_rules.yml`).
5. **Operational Runbooks**: Created step-by-step diagnostic runbooks under `docs/runbooks/` mapped to specific alerts (e.g. latency, circuit breaker, ingestion failure, vector DB connectivity, safety block spike).

## Consequences

### Positive
- **Inspectability**: Full transparency into system execution path and performance bottlenecks via Jaeger trace timelines.
- **Continuous Monitoring**: Automatic detection of query latency degradation, high 5xx rates, low cache hits, and backend outages.
- **Runbook-Driven Operations**: Operators have instant diagnostic actions mapped to active alerts, reducing Mean Time to Resolution (MTTR).
- **Standards-Based**: Using OpenTelemetry guarantees vendor-neutral instrumentation that can seamlessly export to GCP Cloud Monitoring/Trace, Datadog, or honeycomb in production.

### Negative
- **Local Storage Overhead**: Prometheus and Jaeger run in-memory/ephemeral local storage in development. Phase 10 must configure persistent storage backends (Badger/Elasticsearch/Loki).
- **Instrumentation Maintenance**: Developers must manually record custom metrics and spans when writing new modules or changing pipeline steps.
