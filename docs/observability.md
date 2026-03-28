# Observability

## Goal
Make the system debuggable, measurable, and production-like.

## Signals to Capture
- request volume
- response latency
- retrieval latency
- reranking latency
- generation latency
- token counts
- cost estimates
- planner path decisions
- failure counts
- timeout counts
- retrieval hit quality
- citation coverage

## Logs
Use structured logs with:
- request_id
- session_id
- query_type
- retriever mode
- reranker enabled
- model name
- latency breakdown
- error category

## Traces
Instrument:
- ingestion pipeline
- retrieval
- fusion
- reranking
- planning
- generation
- safety checks

## Metrics
Publish metrics for dashboards and alerts:
- P50/P95/P99 latency
- retrieval recall on periodic evals
- error rate
- retry rate
- throughput
- cost per request

## Dashboards
Create dashboards for:
- request health
- retrieval performance
- generation performance
- serving performance
- system failures

## Alerts
Examples:
- high P95 latency
- rising timeout rate
- ingestion failure spike
- vector DB connectivity issues
- model serving degradation