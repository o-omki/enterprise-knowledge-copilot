# Evaluation Framework

## Purpose
The system must be measurable. Evaluation is required to compare retrieval strategies, reranking, query planning approaches, and generation quality.

## Evaluation Layers

### 1. Retrieval Evaluation
Metrics:
- Recall@k
- Precision@k
- MRR
- nDCG

Questions:
- Did we retrieve the correct evidence?
- Does hybrid retrieval outperform sparse-only or dense-only retrieval?

### 2. Reranking Evaluation
Metrics:
- improvement in top-k relevance
- downstream answer quality change
- latency overhead

Questions:
- Does reranking improve evidence quality enough to justify extra cost?

### 3. Answer Quality Evaluation
Metrics:
- correctness
- groundedness
- faithfulness
- citation usefulness
- completeness

Questions:
- Is the answer supported by evidence?
- Does it omit important details?
- Does it overclaim?

### 4. Safety Evaluation
Metrics:
- prompt injection resilience
- unsupported claim rate
- PII leakage rate
- refusal/fallback appropriateness

### 5. Systems Evaluation
Metrics:
- P50/P95/P99 latency
- TTFT
- throughput
- token usage
- cost per query
- failure rate
- timeout rate

## Benchmark Dataset
The benchmark set should include:
- factual lookup questions
- procedural questions
- comparative questions
- multi-hop questions
- ambiguous questions
- adversarial questions

## Evaluation Workflow
1. define benchmark dataset
2. run retrieval and generation pipeline
3. score outputs with automated and human/LLM judges
4. compare variants
5. publish reports

## Required Outputs
- baseline scorecard
- variant comparison table
- failure case analysis
- regression report for major changes