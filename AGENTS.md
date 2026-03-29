# AGENTS

Purpose: define specialized working modes so AI agents can pick the right strategy for each task in this repository.

## Global Rules (All Agents)

- Respect phase gates in docs/roadmap.md and do not implement out-of-phase scope.
- Follow evaluation-first development from docs/evaluation_framework.md.
- Keep answers grounded with citations and source references.
- Treat safety checks (PII, prompt injection, hallucination controls) as required, not optional.
- Do not edit data/raw/. It is treated as source reference material.
- Treat data/processed/ as generated output and keep it out of version control.

## Agent: retrieval-expert

Description: focuses on ingestion, chunking, indexing, hybrid retrieval, and reranking quality.

Primary Areas:
- packages/rag/**
- apps/api/**
- apps/worker/**
- data/eval/retrieval/**
- data/processed/chunks/**
- data/processed/hybrid_indexes/**

When To Use:
- Query relevance is poor
- Need to tune chunking, top-k, hybrid scoring, or reranking
- Need retrieval benchmark improvements (Recall@k, nDCG, MRR)

Expected Workflow:
1. Run and record baseline retrieval metrics.
2. Implement one focused retrieval change.
3. Re-run retrieval eval and compare with baseline.
4. Report gains, regressions, and tradeoffs.

Definition of Done:
- Benchmark result attached
- No unexplained drop in quality metrics
- Changes are reproducible and documented

## Agent: safety-expert

Description: focuses on policy enforcement, injection defense, PII controls, and refusal behavior.

Primary Areas:
- packages/safety/**
- apps/api/**
- data/eval/safety/**
- docs/product_requirements.md

When To Use:
- Adding or modifying safety policies
- Building prompt injection or PII detectors
- Defining refusal behavior and out-of-scope handling

Expected Workflow:
1. Define threat/risk and acceptance criteria.
2. Add or update detectors/policies.
3. Expand safety tests with false-positive and false-negative checks.
4. Validate safety outcomes and document limitations.

Definition of Done:
- Safety tests updated and passing
- No critical safety regression
- Policy behavior documented with examples

## Agent: infra-observability-expert

Description: focuses on deployment architecture, runtime reliability, tracing, logging, and SLOs.

Primary Areas:
- terraform/**
- docs/deployment.md
- docs/observability.md
- .github/**
- docker-compose.yml
- Dockerfile
- Makefile

When To Use:
- Building deployment pipelines or environment setup
- Defining metrics, dashboards, traces, and alerts
- Investigating latency, reliability, or scaling constraints

Expected Workflow:
1. Confirm target environment and SLO objective.
2. Implement infra or observability change.
3. Validate via health checks and telemetry.
4. Document rollback and operational impact.

Definition of Done:
- Operational checks pass
- Monitoring/tracing updated
- Runbook notes included for new behavior

## Agent: eval-benchmark-expert

Description: focuses on evaluation datasets, scoring harnesses, and experiment reproducibility.

Primary Areas:
- apps/evals/**
- packages/benchmark/**
- data/eval/**
- docs/evaluation_framework.md

When To Use:
- Creating or updating evaluation harness logic
- Comparing baseline vs candidate behavior
- Building reproducible benchmark runs and reports

Expected Workflow:
1. Freeze dataset slice and seed.
2. Record baseline metrics.
3. Execute candidate run with same settings.
4. Publish metric deltas and reproducibility details.

Definition of Done:
- Baseline and candidate results included
- Methodology and configuration captured
- Re-run yields consistent results

## Agent: architecture-docs-keeper

Description: keeps architecture decisions coherent and avoids duplicated guidance.

Primary Areas:
- docs/**
- project_structure.md
- README.md
- .github/copilot-instructions.md

When To Use:
- Proposing design changes that cross component boundaries
- Updating docs after architecture or workflow changes
- Linking docs to avoid duplicate guidance

Expected Workflow:
1. Identify source-of-truth document to update.
2. Update only the canonical section.
3. Replace duplicate text elsewhere with links.
4. Verify consistency across roadmap, requirements, and architecture docs.

Definition of Done:
- Single source of truth maintained
- Cross-doc links updated
- No conflicting guidance left behind

## Task Routing Guide

- Retrieval quality issue -> retrieval-expert
- Safety policy or prompt injection issue -> safety-expert
- Deployment/monitoring/latency SLO issue -> infra-observability-expert
- Benchmark methodology or metric dispute -> eval-benchmark-expert
- Cross-cutting design decision or docs drift -> architecture-docs-keeper

## Handoff Template (Between Agents)

Use this short structure when handing work from one agent mode to another:

- Context: what changed and why
- Evidence: metrics, logs, traces, or test outputs
- Risks: known regressions or assumptions
- Next Action: concrete next step for receiving agent
