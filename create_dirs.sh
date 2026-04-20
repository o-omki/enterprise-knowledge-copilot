#!/bin/bash

directories=(
  "data/raw/official_docs/vllm/"
  "data/raw/official_docs/qdrant/"
  "data/raw/official_docs/kubernetes/"
  "data/raw/official_docs/fastapi/"
  "data/raw/release_notes/vllm/"
  "data/raw/release_notes/qdrant/"
  "data/synthetic/internal_wiki/platform_overview/"
  "data/synthetic/internal_wiki/architecture_decisions/"
  "data/synthetic/runbooks/retrieval_debugging/"
  "data/synthetic/runbooks/model_serving/"
  "data/synthetic/support_tickets/retrieval/"
  "data/synthetic/support_tickets/latency/"
  "data/synthetic/incident_reports/postmortems/"
  "data/processed/parsed_documents/"
  "data/processed/chunks/"
  "data/processed/metadata/"
  "data/processed/embeddings/"
  "data/processed/hybrid_indexes/"
  "data/eval/retrieval/"
  "data/eval/generation/"
  "data/eval/safety/"
  "data/eval/agentic/"
)

for dir in "${directories[@]}"; do
  mkdir -p "$dir"
  echo "Created: $dir"
done

echo "--- Directory structure successfully created! ---"