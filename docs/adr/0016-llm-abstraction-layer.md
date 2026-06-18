# ADR 0016: Unified LLM Abstraction Layer

**Status:** Accepted
**Date:** 2026-06-16

## Context and Problem Statement
Previously, the codebase invoked LLM backends (Vertex AI, Google GenAI SDK) using hardcoded logic scattered across RAG and agent services (such as generation, routing, and planning). This direct coupling presented several structural and operational issues:
1. **Model Lock-in:** Swapping backends (e.g., from Vertex AI to an OpenAI-compatible endpoint) required code modifications in multiple files.
2. **Reliability Constraints:** The API had no protection against backend service outages, rate-limiting HTTP 429s, or transient failures.
3. **Redundant Cost and Latency:** Duplicate user queries invoked the LLM repeatedly, causing unnecessary billing costs and latency delays.

We need a clean, unified interface to manage model serving backend selection, request/response structures, fault tolerance (circuit breaking), and caching.

## Decision
We established a new shared package `packages/llm_serving` to serve as the single source of truth for all LLM interactions in the application.

1. **Backend Abstraction (`BaseLLMBackend`):** Defines a standard async interface for text generation and streaming. We implemented concrete backends for `VertexAIBackend` (default) and `OpenAICompatibleBackend`.
2. **Standardized Schema:** Unified input/output objects using Pydantic models: `LLMMessage`, `LLMRequest`, `LLMResponse`, `UsageMetadata`, and `LLMStreamChunk`.
3. **Resilience Wrapping (`CircuitBreaker`):** Integrated a circuit breaker around backend calls that trips to `OPEN` after 5 consecutive failures, immediately blocking subsequent calls to save resources, and recovers to `CLOSED` after a 60-second cooldown timeout.
4. **Caching Layer (`ResponseCache`):** Introduced a Redis-backed caching wrapper that hashes requests (model, messages, parameters) to return cached responses instantly, bypassing model invocations.

## Consequences

### Positive
- **Decoupling:** RAG generation and agent services interact only with the `LLMClient`, making the underlying model provider (Vertex AI vs. local vLLM/OpenAI compatible) completely transparent.
- **Improved Reliability:** The circuit breaker isolates the application from transient failures and rate limits, preventing thread queuing and server overload.
- **Cost & Latency Reduction:** Repeated user queries are answered in sub-second speeds from the Redis cache with zero model cost.
- **SLO Observability:** Centralized token counter, request counter, and latency metrics collection at the client level.

### Negative
- **Additional Dependency:** Introduces Redis as a runtime cache dependency.
- **State Complexity:** Circuit breaker and cache introduce state management overhead that must be carefully configured and unit-tested.
