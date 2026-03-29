---
applyTo: '**'
---

# Enterprise Knowledge Copilot — Development Instructions

## Project Overview

**Status:** Phase 0 (Foundation & Planning) — No implementation yet; scaffolding and comprehensive documentation complete.

**Purpose:** Build a production-grade enterprise knowledge assistant that retrieves answers from heterogeneous documentation sources using hybrid retrieval, cross-encoder reranking, multi-agent query planning, and safety guardrails with full observability.

**Reference Documentation:**
- [Problem Statement](../docs/problem_statement.md) — Motivation and success criteria
- [Architecture Overview](../docs/architecture_overview.md) — System design and request flow
- [Product Requirements](../docs/product_requirements.md) — Functional & non-functional requirements
- [Evaluation Framework](../docs/evaluation_framework.md) — Quality metrics and benchmarks
- [Deployment Strategy](../docs/deployment.md) — Infrastructure and cloud targets
- [Roadmap](../docs/roadmap.md) — 6-phase development plan (Phases 0–6)

## Core Design Principles

1. **Modularity**: Separate retrieval, ranking, generation, and safety concerns into independent packages/services.
2. **Evaluation-First**: Every change is measured. No feature ships without evaluation metrics and benchmark comparisons.
3. **Grounded Outputs**: All answers must cite sources. No hallucinations or unsourced claims.
4. **Reproducibility**: Experiments, evaluations, and deployments are fully reproducible via version control and data versioning.
5. **Cloud-Native**: Kubernetes-ready architecture from day one; design for multi-region deployment.
6. **Safety by Default**: PII detection, prompt injection prevention, and hallucination guards are non-negotiable.

## Technology Stack

### Backend & Core Services
| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **API Server** | Python FastAPI | Type-safe, async-ready, excellent for REST + WebSocket |
| **Vector DB** | Qdrant | Native hybrid search (BM25 + dense), excellent reranking support |
| **Sparse Search** | BM25 / Elasticsearch | Complement dense search; essential for keyword queries |
| **Model Serving** | vLLM | OpenAI-compatible, high throughput, speculative decoding |
| **Metadata DB** | PostgreSQL | Relational data for document hierarchy, citations, user context |
| **Message Queue** | [TBD] | For async jobs (ingestion, indexing, evaluation) |
| **Object Storage** | [TBD] | Raw documents, processed chunks, evaluation datasets |

### Deployment & Observability
| Component | Technology |
|-----------|-----------|
| **Container Orchestration** | Kubernetes (cloud provider: TBD) |
| **Infrastructure as Code** | Terraform + Helm |
| **Monitoring** | Prometheus + Grafana |
| **Logging** | Structured JSON logging + centralized aggregation (e.g., ELK) |
| **Tracing** | OpenTelemetry (vendor TBD) |
| **CI/CD** | GitHub Actions (planned) |

### Frontend & AI
| Component | Technology |
|-----------|-----------|
| **Frontend** | React or Flutter (TBD via ADR) |
| **LLM Inference** | OpenAI API or self-hosted vLLM |
| **Reranker** | Cross-encoder (e.g., Cohere, Jina, or local model) |
| **Embeddings** | Dense vectors from OpenAI, local model, or specialized service |

## Development Phases & Scope

Work is organized into **6 phases** with strict scope gates. Each phase has clear entry/exit criteria.

### Phase 0: Foundation & Planning (Current)
- ✅ Problem statement and product requirements defined
- ✅ Architecture and system design documented
- ✅ Data directory structure and raw documents scaffolded
- ⏳ Evaluation framework and metrics specified
- ⏳ ADRs for tech stack choices (K8s provider, frontend framework, message queue)

**Deliverable:** Executable plan for Phase 1 with CI/CD skeleton, dev environment setup, and baseline collection of test data.

### Phase 1: Baseline Retrieval System
**Scope:** Single-document QA with exact retrieval

- **Ingest:** Parse official docs (FastAPI, Qdrant, Kubernetes, vLLM) into chunks
- **Index:** Build BM25 (sparse) and dense vector indexes
- **Retrieve:** Simple query → top-k retrieval pipeline
- **Answer:** Template-based QA ("The answer is found in: `<document>`")
- **Eval:** Recall@k, nDCG, MRR on retrieval benchmarks; citation accuracy

**Gate:** Retrieval recall >85% on synthetic benchmark before Phase 2.

### Phase 2: Hybrid Retrieval & Ranking
**Scope:** Multi-document retrieval with ranking and relevance

- Implement BM25 + dense hybrid search scoring
- Add cross-encoder reranking (top-100 → top-10)
- Evaluate ranking quality; optimize hyperparameters
- Build retrieval quality dashboard

**Gate:** Ranking nDCG@10 >0.75 on benchmark before Phase 3.

### Phase 3: Multi-Hop Query Planning
**Scope:** Agent-driven query decomposition and multi-step reasoning

- Query router: detect simple vs. complex queries
- Query planner: decompose into sub-queries
- Multi-agent orchestration for parallel retrieval + synthesis

**Gate:** Agentic evaluation pass >80% before Phase 4.

### Phase 4: Safety & Bias Mitigation
**Scope:** PII detection, prompt injection, factuality, and refusal policies

- PII redaction pipeline
- Prompt injection detection
- Hallucination detection and mitigation
- Implement refusal policy for out-of-scope queries

**Gate:** Safety test suite passes; zero undetected PII in 1K random samples.

### Phase 5: Observability & Analytics
**Scope:** Production-grade logging, tracing, metrics, and health checks

- Structured logging and trace propagation
- Real-time metrics (latency, throughput, error rates)
- Query quality dashboard and analytics
- Health checks and SLO monitoring

**Gate:** Observability dashboards operational; SLOs documented and tracked.

### Phase 6: Performance & Scale
**Scope:** Optimize latency, throughput, and cost; prepare for multi-region deployment

- **Performance targets:**
  - Latency: P50 < 4s, P95 < 8s per query
  - Cost target: < $0.10 per query (TBD)
  - Throughput: TBD based on requirements
- Load testing and bottleneck analysis
- K8s autoscaling configuration
- Multi-region deployment proof-of-concept

---

## Repository Structure

```
enterprise-knowledge-copilot/
├── .github/                          # GitHub Actions, templates, this file
│   └── copilot-instructions.md      # (You are here)
├── docs/                             # Architecture & decision documentation (read-only reference)
│   ├── architecture_overview.md
│   ├── deployment.md
│   ├── evaluation_framework.md
│   ├── observability.md
│   ├── problem_statement.md
│   ├── product_requirements.md
│   ├── roadmap.md
│   └── milestones.md                # Progress tracking (updated per phase)
├── data/                             # Raw, processed, and evaluation data
│   ├── raw/                         # Source documents (read-only during development)
│   │   ├── official_docs/          # Real-world reference docs (FastAPI, Qdrant, K8s, vLLM)
│   │   ├── release_notes/          # Changelogs and release history
│   │   └── synthetic/              # Enterprise-style synthetic data (internal wikis, runbooks, tickets)
│   ├── processed/                   # Output of ingestion pipeline (generated; .gitignore)
│   │   ├── parsed_documents/
│   │   ├── chunks/
│   │   ├── embeddings/
│   │   └── hybrid_indexes/
│   └── eval/                        # Evaluation datasets and results
│       ├── retrieval/               # Retrieval benchmarks
│       ├── generation/              # Answer quality benchmarks
│       ├── safety/                  # Safety test suites
│       └── agentic/                 # Multi-hop query tests
├── apps/                             # Application services (to be created in Phase 1)
│   ├── api/                         # FastAPI backend
│   ├── worker/                      # Background jobs (ingestion, indexing)
│   ├── evals/                       # Evaluation harness service
│   └── frontend/                    # React/Flutter UI (Phase TBD)
├── packages/                         # Shared libraries (to be created in Phase 1)
│   ├── shared/                      # Common DTOs, config, utilities
│   ├── rag/                         # Chunking, retrieval, ranking logic
│   ├── agents/                      # Query planner, router, tool definitions
│   ├── safety/                      # PII detection, prompt injection, policy
│   ├── observability/               # Tracing, logging, metrics
│   ├── llm_serving/                 # vLLM client, model routing
│   └── benchmark/                   # Load testing, latency analysis
├── project_structure.md              # Directory structure blueprint
├── create_dirs.sh                    # Bootstrap script (run once)
├── README.md                         # (Empty; will document for Phase 1)
├── pyproject.toml                    # Python dependencies (Phase 1)
├── package.json                      # Frontend dependencies (Phase TBD)
├── Makefile                          # Build, test, run targets (Phase 1)
├── docker-compose.yml                # Local dev stack (Phase 1)
├── Dockerfile                        # Container images (Phase 1)
├── .env.example                      # Environment variables template (Phase 1)
├── .gitignore                        # (Should exclude: /data/processed/*, __pycache__/, node_modules/, etc.)
└── terraform/                        # Infrastructure as Code (Phase 5+)
```

### Data Directory Conventions

**Do NOT edit `/data/raw/`** — it contains reference documentation and synthetic test data. Changes should be merged back into source (official docs) or tracked in a separate datasets repository.

**`/data/processed/`** — Generated by ingestion pipeline. Add to `.gitignore` and only version-control via data versioning system (e.g., DVC, Hugging Face Datasets).

**`/data/eval/`** — Critical for reproducibility. Version-control human-curated benchmarks; auto-generated results stored separately.

---

## Development & Execution Commands (Phase 1+)

Once Phase 1 begins, implement these targets in `Makefile`:

```bash
# Environment setup
make install              # Install Python deps (pip) + pre-commit hooks
make install-docs        # Install documentation build dependencies
make dev-setup           # Create .env from .env.example, bootstrap compose

# Development
make dev                  # Run local stack (API + Qdrant + PostgreSQL + vLLM via Docker Compose)
make lint                 # Run flake8, pylint, black --check, isort --check
make format               # Auto-format with black + isort
make type-check           # Run mypy on apps/ and packages/

# Testing
make test                 # Run unit tests across apps/ and packages/
make test-integration     # Run integration tests (requires compose running)
make test-coverage        # Run tests with coverage report

# Data & Evaluation
make ingest-docs          # Run ingestion pipeline on /data/raw/ → /data/processed/
make seed-demo            # Populate vector DB with demo data
make run-evals            # Run all evaluation benchmarks
make eval-retrieval       # Run retrieval eval only
make eval-generation      # Run generation eval only

# Documentation & CI
make docs                 # Build documentation (if using Sphinx/MkDocs)
make build                # Build Docker images for all services
make push-images          # Tag and push to container registry
make deploy-dev           # Deploy to dev K8s cluster
make deploy-prod          # Deploy to prod K8s cluster
```

---

## Key Conventions & Patterns

### Naming & Organization

- **Packages (Python):** Lowercase with underscores (`rag_pipeline`, `safety_manager`)
- **Classes & Functions:** PascalCase for classes, snake_case for functions
- **Endpoints:** Plural nouns, semantic HTTP verbs (`POST /queries`, `GET /documents/{id}`)
- **Test files:** `test_<module>.py` (pytest convention)
- **Config files:** `.env` for secrets, `config.yaml` for structured config

### Code Quality Thresholds

- **Type coverage:** 80%+ (enforced by mypy)
- **Test coverage:** 75%+ for core packages; 60%+ for service code
- **Lint:** Zero style violations (enforce in CI)
- **Pre-commit hooks:** Autoformat, linting, type checking (optional but recommended)

### Evaluation Mindset

All code changes should include or justify:
1. **What metric does this improve?** (e.g., retrieval recall, latency, citation accuracy)
2. **Baseline vs. proposed:** Quantified before/after on a fixed benchmark
3. **Regression risk:** Did this change harm any other metric?

See [evaluation_framework.md](../docs/evaluation_framework.md) for benchmark details.

### Safety & Security

- Never hardcode secrets; use environment variables or secrets manager
- Log database queries but never log API keys, tokens, or PII
- All LLM generation must pass PII detection before returning to user
- Prompt injection tests must be part of the core eval suite (Phase 4)

### Documentation Standards

- **Code:** Docstrings for all public functions (Google or NumPy style)
- **APIs:** OpenAPI/Swagger auto-generated from FastAPI; include examples
- **Architecture:** ADRs in `docs/architecture_decisions/` for major decisions
- **Runbooks:** Operational guides in `docs/runbooks/` for deployment and troubleshooting

---

## Common Development Workflows

### Adding a New Retrieval Algorithm

1. **Implement** in `packages/rag/` with full unit tests
2. **Register** in `packages/rag/registry.py` (strategy pattern)
3. **Benchmark** against existing approaches using `eval_retrieval` benchmark
4. **Document** rationale and performance comparison in an ADR
5. **Integrate** into the pipeline via config, with feature flag for gradual rollout

### Adding a New Safety Check

1. **Implement** detector in `packages/safety/`
2. **Build** test suite in `data/eval/safety/` with false positive/negative targets
3. **Run** eval; document precision/recall
4. **Integrate** into `packages/safety/policy.py`
5. **Monitor** in prod via dashboard metrics

### Debugging Retrieval Quality Issues

1. Check `data/processed/chunks/` — are documents chunked correctly? (size, overlap, boundaries)
2. Inspect BM25 index — is tokenization/stemming working? (run `make test-bm25` diagnostic)
3. Check embeddings — are they aligned with query intent? (run embedding similarity checks)
4. Run reranker in isolation — what does top-100 → top-10 actually rank?
5. Compare to human relevance judgments in `data/eval/retrieval/`
6. File an issue with repro data; evaluate proposed fixes on the benchmark before merging

---

## Special Conventions & Gotchas

### ⚠️ Start Narrow; Expand Deliberately
Do not attempt to build the full system in Phase 1. Use a **single source document** (e.g., FastAPI docs) and prioritize:
1. Full ingestion pipeline end-to-end
2. Working retrieval + basic QA
3. Repeatable evaluation
4. Clean deployment

Only after Phase 1 gate is satisfied, add more documents, agents, reranking, etc.

### ⚠️ Latency is a Constraint, Not a Goal
- **Target:** P50 < 4s, P95 < 8s per query (including LLM inference)
- **Measure:** End-to-end latency in production-like conditions
- **Optimize:** Profile bottlenecks (retrieval? LLM? network?) before optimizing code
- Do not sacrifice accuracy for speed without explicit tradeoff analysis

### ⚠️ Cost is an Explicit Metric
- Track cost per query (include embeddings, LLM, storage, compute)
- Set a cost budget in Phase 6 and measure against it
- Self-hosted models (vLLM) vs. API calls (OpenAI) is an intentional tradeoff; evaluate both
- Document assumptions: inference cost, QPS, regional pricing, etc.

### ⚠️ No Hidden Assumptions in Data
- All synthetic data should be realistic (source from actual enterprise documents if possible)
- Version all benchmarks; don't quietly rebuild test sets
- Human-curated relevance judgments are gold-standard; don't only rely on LLM judges
- Reproducibility requires versioning docs and exactly specifying eval procedures

### ⚠️ Evaluation Bugs Are Bugs
- A faulty eval that says "new system is better" but isn't is a critical incident
- Always cross-check with human review on a sample
- Version control all eval code, seeds, data splits, and judge prompts
- Track eval reproducibility: can another engineer run the exact same eval and get the same results?

---

## CI/CD & Deployment Checklist

### Before Merging to `main`:
- ✅ Tests pass (unit + integration)
- ✅ Linting and type checking pass
- ✅ New code is documented (docstrings + ADR if architectural)
- ✅ Eval metrics are reported (if applicable) with baseline comparison
- ✅ No hardcoded secrets or credentials

### Before Deploying to Staging:
- ✅ GitHub Actions CI pipeline passes
- ✅ Docker build succeeds; images pushed to registry
- ✅ K8s manifests are valid (helm lint, kubeval)
- ✅ Integration tests pass in staging environment
- ✅ Observability dashboards are operational

### Before Deploying to Production:
- ✅ Phase gate is satisfied (see Development Phases above)
- ✅ Load test passes with target SLA
- ✅ Rollback plan is documented
- ✅ On-call runbooks are current
- ✅ Security scan passes (dependency vulnerabilities, SAST)

---

## Links to Key Documentation

**Architecture & Design:**
- [Architecture Overview](../docs/architecture_overview.md) — System diagram and component interactions
- [Product Requirements](../docs/product_requirements.md) — Functional and non-functional constraints

**Development & Operations:**
- [Evaluation Framework](../docs/evaluation_framework.md) — Benchmark definitions, metrics, judge prompts
- [Deployment Strategy](../docs/deployment.md) — Infrastructure targets, multi-region setup, autoscaling
- [Observability](../docs/observability.md) — Logging, tracing, metrics, dashboards, alerting

**Planning & Progress:**
- [Roadmap](../docs/roadmap.md) — Phased development plan with timelines
- [Milestones](../docs/milestones.md) — Per-phase deliverables and completion status
- [Data Directory Reference](../project_structure.md) — Detailed structure and conventions

---

## Getting Help & Asking Good Questions

### For Architecture Questions:
- Reference the relevant `docs/*.md` file (this file links to them)
- Check existing ADRs in `docs/architecture_decisions/` for precedent
- If the answer isn't documented, propose an ADR and get stakeholder alignment before implementing

### For Evaluation & Benchmarking:
- See [evaluation_framework.md](../docs/evaluation_framework.md) for metric definitions and test data
- Run baseline on HEAD before proposing changes
- Provide quantified before/after results with confidence intervals if available

### For Debugging & Troubleshooting:
- Check `docs/runbooks/` for operational guides
- Inspect logs and traces in the observability stack (Grafana, tracing UI)
- If stuck, share: (1) exact steps to reproduce, (2) logs, (3) what you've tried
- Prefer filing well-documented issues over Slack; include repro data and context

---

## Example Development Session

### Scenario: You're tasked with improving retrieval recall in Phase 2

**Workflow:**
1. Read [Evaluation Framework](../docs/evaluation_framework.md) and identify retrieval recall metric (Recall@k)
2. Run baseline: `make eval-retrieval` → observe current Recall@10 = 0.78
3. Implement hybrid BM25 + dense search in `packages/rag/hybrid_scorer.py`
4. Add unit tests for scoring function
5. Integrate into pipeline config; test end-to-end in `make test-integration`
6. Run eval again: `make eval-retrieval` → new Recall@10 = 0.85 ✅
7. Document approach and hyperparameters in an ADR (`docs/architecture_decisions/0011-hybrid-scoring.md`)
8. Create PR with eval results, code, tests, and ADR
9. Get review; merge when CI passes and reviewer approves
10. Deploy to staging and monitor latency; if P95 < 8s, promote to production

This workflow ensures: ✅ Measurement (baseline → proposed), ✅ Reproducibility (tests + eval data), ✅ Documentation (ADR), ✅ Safety (CI + monitoring).

---

**Last Updated:** Phase 0  
**Next Review:** Phase 1 Entry Gate
