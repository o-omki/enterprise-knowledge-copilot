# 0012. Cross-Encoder Reranker Choice

## Context

Following Phase 2, hybrid retrieval (Qdrant RRF of dense + sparse) achieved the best Recall@5 (0.97) but its Recall@1 (0.76) dipped below pure dense retrieval (0.83). This happens because RRF fusion promotes broad recall without optimising rank position. The LLM generator receives the top-k results in ranked order, so a lower Recall@1 means the most relevant evidence is less likely to be at the top of the context window.

Phase 3 introduces a cross-encoder reranking step between retrieval and generation to fix this.

## Decision

**Use a cross-encoder reranker on top of hybrid retrieval.**

Specifically:
- **Library**: `sentence-transformers >= 3.0.0`
- **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Integration**: Two-stage pipeline — retrieve `top_k * 2` candidates via hybrid RRF, then rerank to `top_k` using the cross-encoder.
- **Interface**: Opt-in via `rerank=true` query parameter on `/search` and `/ask`. Off by default so existing integrations are unaffected.
- **Global toggle**: `RERANKER_ENABLED` env variable allows disabling reranking without a code deploy.

## Alternatives Considered

| Option | Why Rejected |
|--------|-------------|
| Bi-encoder reranking (e.g., re-embed with a finer model) | Lower accuracy than cross-encoder; doesn't jointly encode query+passage |
| Cohere Rerank API | Adds an external SaaS dependency and per-call cost; cross-encoder is free and local |
| Always-on reranking | Higher latency for callers that don't need it; opt-in gives control |
| Custom trained cross-encoder | Out of scope for Phase 3; ms-marco model generalises well to factual QA |

## Why `ms-marco-MiniLM-L-6-v2`

- Trained on MS MARCO passage ranking — directly applicable to enterprise factual QA.
- Runs on CPU with acceptable latency (see benchmark results below).
- 6-layer MiniLM architecture: fast enough for real-time use, much more accurate than bi-encoder reranking.
- No GCP credentials required — removes a dependency chain from the critical path.

## Evaluation Results

Benchmark run against `data/eval/retrieval/ground_truth.json` (top-k = 5, candidate multiplier = 2× for hybrid+rerank, 309 queries):

| Method | Recall@1 | Recall@5 | MRR | Avg Latency (ms) |
|--------|----------|----------|------|-----------------|
| Dense | 0.91 | 0.96 | 0.93 | 588.0 |
| Sparse | 0.84 | 0.93 | 0.88 | 3.7 |
| Hybrid | 0.91 | 0.97 | 0.94 | 550.8 |
| **Hybrid + Rerank** | **0.92** | **0.96** | **0.94** | **642.2** |

Phase 3 Gate: `hybrid+rerank Recall@1 >= 0.83` → **PASSED** (achieved 0.92).

Reranking adds ~91 ms average overhead over raw hybrid (642 − 551) for a +0.7 pp Recall@1 lift.

## Consequences

- Reranking adds latency (cross-encoder inference on CPU). This is measured and logged per query in `diagnostics.rerank_latency_ms` on each `SearchResult`.
- The `rerank=true` flag is off by default, meaning zero impact on callers that don't opt in.
- Phase 4 (Multi-Agent Query Planning) can leverage the improved top-1 precision: the planner can trust the first retrieved document more when building sub-queries.
- The reranker model (~80 MB) is downloaded from HuggingFace Hub on first use and cached locally. No additional infrastructure is required.
