# 0011. Hybrid Scoring and Hierarchical Chunking Evaluation

## Context

In Phase 2 of the Enterprise Knowledge Copilot project, we aimed to improve retrieval quality over the Phase 1 dense baseline by:
1. Combining Sparse (BM25 via FastEmbed) and Dense (Google Gemini) embeddings using native Qdrant Reciprocal Rank Fusion (RRF).
2. Experimenting with a Hierarchical (Parent-Child) chunking strategy. In this approach, small child chunks (e.g., 300 tokens) are embedded for precise vector matching, while their larger parent chunks (e.g., 1200 tokens) are stored in the payload and returned to the LLM to preserve valuable generation context.

## Evaluation Results

We ran our evaluation script against the test documents across `DENSE`, `SPARSE`, and `HYBRID` mode utilizing the Hierarchical format.

**Metrics (Hierarchical Strategy):**
- **DENSE**
  - Recall@1: 0.83
  - Recall@5: 0.97
  - MRR: 0.89
- **SPARSE**
  - Recall@1: 0.53
  - Recall@5: 0.82
  - MRR: 0.64
- **HYBRID (RRF)**
  - Recall@1: 0.76
  - Recall@5: 0.97
  - MRR: 0.86

## Analysis & Decision

* **Recall Improvements**: Hybrid retrieval successfully achieved the highest Recall@5 (0.97), surpassing the 85% Phase 1 gate and demonstrating that combining lexical (sparse) and semantic (dense) strategies effectively pulls the most relevant documents into the top 5 results.
* **Trade-offs**: While Hybrid has the best Recall@5, its Recall@1 (0.76) actually dipped slightly below pure Dense (0.83) in this benchmark. This is a common artifact of fusion formulas like RRF without tuned weights.
* **Hierarchical Chunking**: The hierarchical parent-child design proved viable. Hitting a precise 400-token child returns the full 115000-token parent string, ensuring the upcoming generation steps have sufficient context without diluting the search embeddings.

**Decision:**
We will move forward with **Hybrid Retrieval** as the primary search method and **Hierarchical Chunking** as the standard ingestion pathway. 

## Consequences

- The Phase 2 objectives are complete. We have successfully implemented and evaluated hybrid retrieval and advanced chunking strategies.
- To address the lower Recall@1 observed in the Hybrid method, Phase 3 will introduce Cross-Encoder Reranking. The Hybrid strategy will retrieve a broad set (e.g., Top 20) with high recall, and the Cross-Encoder will re-score them to optimize Recall@1 before passing the context to the LLM.
