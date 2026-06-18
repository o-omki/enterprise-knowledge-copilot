# ADR 0017: Model Routing Strategy

**Status:** Accepted
**Date:** 2026-06-16

## Context and Problem Statement
 RAG and agent queries have highly diverse complexity levels and performance constraints:
1. **Simple Queries:** Basic direct lookups or routing selections do not require expensive frontier models (like `gemini-3.1-pro-preview`) and can run on fast, cheap models.
2. **Complex Queries:** Multi-hop synthesis, comparative questions, and multi-step reasoning fail on small models and require high-reasoning models.
3. **SLO Priorities:** Some request profiles prioritize low latency, some cost efficiency, and others absolute quality.

We need an intelligent model routing component that automatically matches the incoming query complexity and SLO constraints to the best-fit model profile without manual intervention.

## Decision
We implemented a dynamic `ModelRouter` in `packages/llm_serving/router.py` that selects models based on a central configuration ([models.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/configs/models.yaml)):

1. **Model Profiles:** Models are registered with capability lists (e.g. `routing`, `direct_lookup`, `complex_reasoning`) and pricing tier metadata.
2. **Eligibility Filtering:** When a service requests a model, it specifies the required capability (e.g. `complex_reasoning`) and an optional `SLOConfig` containing priority flags (`cost`, `latency`, `quality`).
3. **Priority-Based Sorting:** Eligible models are sorted and selected based on the SLO priority:
   - **Cost:** Sorts by lowest input cost.
   - **Latency:** Sorts by fastest latency tier (`ultra-fast` > `fast` > `standard`).
   - **Quality:** Sorts by reasoning capability / standard tier profile.

## Consequences

### Positive
- **Cost Optimization:** Automatically delegates simple tasks (like query routing or single-document lookups) to cheaper models (`gemini-3.1-flash-lite`), saving up to 80% in token costs.
- **Latency Acceleration:** Fast/interactive tasks bypass standard models, resolving in sub-second speeds.
- **Configurability:** Changing routing behavior or adding new models requires modifying only [models.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/configs/models.yaml) rather than changing application code.

### Negative
- **Dependency on Classification:** The orchestrator or agent must accurately determine the query type/capability beforehand for the router to operate optimally.
- **Context Management:** Different routed models have varying max token windows (e.g., 32k vs 1M), which the client must handle correctly to prevent out-of-context errors.
