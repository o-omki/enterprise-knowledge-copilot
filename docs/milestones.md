# Milestones

## Overall Status
- Current phase: Phase 11 (Hardening and Showcase)
- Last completed phase: Phase 10 (Deployment & Cloud Infrastructure) — **Complete**
- Last updated: 2026-07-12

## Phase 0 Checklist
<!--  -->
### Planning and Scope
- [x] Project goal and roadmap defined ([docs/roadmap.md](roadmap.md))
- [x] Problem statement documented ([docs/problem_statement.md](problem_statement.md))
- [x] Product requirements documented ([docs/product_requirements.md](product_requirements.md))
- [x] Architecture overview documented ([docs/architecture_overview.md](architecture_overview.md))
- [x] Evaluation framework documented ([docs/evaluation_framework.md](evaluation_framework.md))
- [x] Deployment strategy documented ([docs/deployment.md](deployment.md))

### Repository and Data Setup
- [x] Repository initialized with baseline structure
- [x] Data directories scaffolded ([create_dirs.sh](../create_dirs.sh))
- [x] Corpus source folders prepared under [data/raw](../data/raw)

### Engineering Foundation
- [x] Python project scaffold added ([pyproject.toml](../pyproject.toml))
- [x] Makefile targets for install, lint, type-check, test, dev added ([Makefile](../Makefile))
- [x] Local Docker Compose stack added ([docker-compose.yml](../docker-compose.yml))
- [x] Pre-commit hook config added ([.pre-commit-config.yaml](../.pre-commit-config.yaml))
- [x] Base CI workflow added ([.github/workflows/ci.yml](../.github/workflows/ci.yml))
- [x] Minimal API skeleton added ([apps/api/app/main.py](../apps/api/app/main.py))
- [x] Minimal worker skeleton added ([apps/worker/app/main.py](../apps/worker/app/main.py))
- [x] Package skeletons added ([packages/rag](../packages/rag))

### Remaining for Phase 0 Exit
- [x] Finalize ADRs for unresolved decisions:
  - frontend framework: Flutter ([ADR 0004](adr/0004-frontend-choice.md))
  - queue technology: Redis/PubSub ([ADR 0006](adr/0006-queue-choice.md))
  - cloud/Kubernetes provider: GCP ([ADR 0005](adr/0005-cloud-provider-choice.md))
- [x] Record explicit Phase 0 sign-off in this file with owner/date (Signed off: April 21, 2026)

## Phase 0 Exit Criteria Status
- [x] Project goals are clear
- [x] Scope is realistic
- [x] Implementation order is documented
- [x] CI/CD is operational locally and on GitHub

## Phase 1: Baseline Retrieval System (Complete)
- [x] Implement document ingestion pipeline (Markdown/FastAPI docs)
- [x] Configure Qdrant collection for dense retrieval
- [x] Build initial retrieval-only benchmark
- [x] Create basic QA endpoint using top-k context

## Phase 2: Hybrid Retrieval and Retrieval Quality Improvements (Complete)
- [x] Implement sparse (BM25) embedding support
- [x] Configure Qdrant for Hybrid Search (RRF)
- [x] Implement hierarchical / parent-child chunking
- [x] Evaluate dense vs. sparse vs. hybrid on Recall@k metrics
- [x] Document Recall@k findings via ADR

## Sign-off Log
- [x] Phase 0 completion sign-off (April 21, 2026)
- [x] Phase 1 completion sign-off
- [x] Phase 2 completion sign-off
- [x] Phase 3 completion sign-off (May 16, 2026)
- [x] Phase 4 completion sign-off (May 18, 2026)
- [x] Phase 5 completion sign-off (May 28, 2026)
- [x] Phase 6 completion sign-off (June 9, 2026)
- [x] Phase 7 completion sign-off (June 15, 2026)
- [x] Phase 8 completion sign-off (June 16, 2026)
- [x] Phase 9 completion sign-off (June 21, 2026)
- [x] Phase 10 completion sign-off (July 12, 2026)

## Phase 3: Cross-Encoder Reranking (Complete)
- [x] Add `sentence-transformers` dependency (`pyproject.toml`)
- [x] Implement `packages/rag/reranker.py` (cross-encoder, async-safe, lazy model load)
- [x] Wire `rerank=true` opt-in param into `/search` and `/ask` endpoints
- [x] Extend `benchmarks/retrieval/eval_retrieval.py` with `hybrid+rerank` path and latency measurement
- [x] Record pre-reranking baseline (`data/eval/retrieval/baseline_phase3.json`)
- [x] Run benchmark and record results in `data/eval/retrieval/phase3_reranking_results.json`
- [x] Fill in ADR metric table ([ADR 0012](adr/0012-reranker-choice.md))
- [x] Confirm Phase 3 gate: `hybrid+rerank Recall@1 >= 0.83` — **PASSED**

## Phase 4: Multi-Agent Query Planning (Complete)
- [x] Define query classes (direct, ambiguous, multi-hop, comparative)
- [x] Add router/planner component
- [x] Implement query decomposition
- [x] Parallel retrieval of evidence per sub-question
- [x] Aggregate evidence before answer generation
- [x] Add tracing for planner decisions (OpenTelemetry spans)
- [x] Benchmark to prove multi-hop > single-pass
- [x] End of phase sign-off

## Phase 5: Safety and Guardrails (Complete)
- [x] Epic 1: NeMo Guardrails Microservice Infrastructure
  - [x] Task 1.1: Initialize `apps/guardrails` container scaffolding
  - [x] Task 1.2: Connect GCP Vertex AI (Gemini) as primary rail LLM
  - [x] Task 1.3: Add `guardrails` service to root `docker-compose.yml`
  - [x] Task 1.4: Implement service liveness & readiness health probes
- [x] Epic 2: Privacy & Data Loss Prevention (DLP)
  - [x] Task 2.1: Integrate Private AI PII detection/masking API
  - [x] Task 2.2: Implement local fast regex filters for common threat patterns (SSN, Email)
  - [x] Task 2.3: Configure input/output PII flows in NeMo `config.yml`
  - [x] Task 2.4: Integrate PII validation unit tests in CI/CD pipeline
- [x] Epic 3: Input Guardrails (Prompt Injection & Context Abuse)
  - [x] Task 3.1: Formulate input self-checking prompts in `config/prompts.yml`
  - [x] Task 3.2: Configure Colang 2.0 flows to identify and block off-topic queries
  - [x] Task 3.3: Implement jailbreak & instruction override protection flows
- [x] Epic 4: Output Guardrails (Hallucination Mitigation)
  - [x] Task 4.1: Formulate `self_check_facts` for RAG grounding verification
  - [x] Task 4.2: Implement local citation parser and verification heuristics
  - [x] Task 4.3: Define confidence thresholds for grounding refusal triggers
- [x] Epic 5: Refusal & Fallback User Experience (UX)
  - [x] Task 5.1: Write standard refusal and fallback dictionary response messages
  - [x] Task 5.2: Intercept core API routes via FastAPI safety middleware
  - [x] Task 5.3: Build offline graceful degradation mode with local regex checking
- [x] Epic 6: Adversarial Testing & Evaluation (Red Teaming)
  - [x] Task 6.1: Compile standard static adversarial dataset (`data/eval/safety/static_adversarial_dataset.json`)
  - [x] Task 6.2: Create dynamic automated red-teaming runner using generative agents
  - [x] Task 6.3: Generate safety baseline scorecards and performance metrics report
- [x] Epic 7: Documentation & ADR Integration
  - [x] Task 7.1: Write Architecture Decision Record for NeMo Guardrails integration
  - [x] Task 7.2: Finalize monorepo checklist validation and sign-off

## Phase 6: Evaluation Harness (Complete)
- [x] Build foundational testing harness
- [x] Implement eval metrics (Recall, nDCG, MRR)
- [x] Setup continuous automated evaluation
- [x] Baseline snapshot mechanism

## Phase 7: API & UI Productization — Task Tracker
### Epic 1: Backend API Contract Finalization
- [x] 1.1 Create `apps/api/app/schemas.py`
- [x] 1.2 Rewrite `apps/api/app/main.py`
- [x] 1.3 Update `apps/api/app/middleware/safety.py`
- [x] 1.4 Update `packages/agents/orchestrator.py`
- [x] 1.5 Update `packages/rag/generation.py`

### Epic 2: Dual-Layer Session & Memory Architecture
- [x] 2.1 Add new dependencies to `pyproject.toml`
- [x] 2.2 Create `packages/shared/database.py`
- [x] 2.3 Create `packages/shared/orm_models.py`
- [x] 2.4 Create `packages/shared/models.py`
- [x] 2.5 Scaffold Alembic, configure async `env.py`
- [x] 2.6 Auto-generate initial migration
- [x] 2.7 Create `packages/shared/session.py`
- [x] 2.8 Verify: `alembic upgrade head` runs against PostgreSQL

### Epic 3: API Key Authentication & Rate Limiting
- [x] 3.1 Create auth middleware
- [x] 3.2 Create rate limiter
- [x] 3.3 Create demo key seeder
- [x] 3.4 Update `.env.example`

### Epic 4: Frontend Web Application
- [x] 4.1 Scaffold Next.js web app
- [x] 4.2 Create theme
- [x] 4.3 Create API config + services
- [x] 4.4 Create models
- [x] 4.5 Create providers
- [x] 4.6 Build ChatScreen + all widgets
- [x] 4.7 Build SettingsScreen
- [x] 4.8 Verify build

### Epic 5: Jaeger Trace Integration
- [x] 5.1 Wire trace_id extraction into orchestrator response

### Epic 6: User Feedback Loop
- [x] 6.1 Create `packages/shared/feedback.py`

### Epic 7: Async Ingestion Worker (Celery)
- [x] 7.1 Create `apps/worker/celery_app.py`
- [x] 7.2 Create `apps/worker/tasks.py`

### Epic 8: Infrastructure & Documentation
- [x] 8.1 Update `docker-compose.yml`
- [x] 8.2 Update `Makefile`
- [x] 8.3 Create ADR `docs/adr/0015-api-v1-contract.md`
- [x] 8.4 Update `docs/milestones.md`
- [x] 8.5 Create `apps/frontend/Dockerfile`
- [x] 8.6 Update eval runners/scripts for new POST API

## Phase 8: Serving & Inference Optimization (Complete)
- [x] Epic 1: Unified LLM Abstraction Layer (`packages/llm_serving`)
  - [x] Task 1.1: Standardize input/output interfaces (`LLMMessage`, `LLMRequest`, `LLMResponse`)
  - [x] Task 1.2: Implement `VertexAIBackend` and `OpenAICompatibleBackend` wrappers
  - [x] Task 1.3: Wrap client calls with a threshold-trip `CircuitBreaker`
  - [x] Task 1.4: Integrate Redis-backed `ResponseCache` for query memorization
- [x] Epic 2: Intelligent Model Router with SLO Enforcement
  - [x] Task 2.1: Create `configs/models.yaml` mapping capabilities and latency tiers
  - [x] Task 2.2: Implement dynamic model profile selection logic
  - [x] Task 2.3: Wire model routing selection in multi-agent planning pipelines
- [x] Epic 3: Prompt & Retrieval Depth Optimization
  - [x] Task 3.1: Centralize prompts in `configs/prompts.yaml` (baseline, concise, detailed)
  - [x] Task 3.2: Configure grid sweep testing matrix for parameters
  - [x] Task 3.3: Select Option B (`concise` prompt, `top_k: 3`) as system default
- [x] Epic 4: Serving Benchmark Harness
  - [x] Task 4.1: Implement `ServingRunner` targeting router, caching, and breaker behaviors
  - [x] Task 4.2: Register the runner in CLI and regression checking suites
  - [x] Task 4.3: Add Makefile target `eval-serving` and unit tests
- [x] Epic 5: Load Testing Infrastructure
  - [x] Task 5.1: Create Locust load testing script (`scripts/load_test.py`) with session tracking
  - [x] Task 5.2: Create compliance checker script (`scripts/load_test_report.py`) enforcing latency targets
  - [x] Task 5.3: Add Makefile targets for headless load testing
- [x] Epic 6: Inference Configuration & Environment
  - [x] Task 6.1: Add serving env variables in `.env` and `.env.example`
  - [x] Task 6.2: Configure interactive Locust service in `docker-compose.yml`
- [x] Epic 7: Documentation & ADR
  - [x] Task 7.1: Write ADR 0016 (LLM Abstraction Layer) and ADR 0017 (Model Routing Strategy)
  - [x] Task 7.2: Create developer guide `docs/model-serving.md`

## Phase 9: Observability and Reliability (Complete)
- [x] Epic 1: Structured Logging Overhaul
  - [x] Configure structlog with JSON renderer
  - [x] Create API request context middleware
  - [x] Update pipeline components to use structured logging
- [x] Epic 2: Distributed Tracing Instrumentation
  - [x] Instrument API, Guardrails, and Worker services with OTel
  - [x] Set up span attributes and error logging
- [x] Epic 3: Prometheus Metrics Exporter & Custom Application Counters
  - [x] Define counters and histograms for request, retrieval, reranking, generation, and safety layers
  - [x] Setup PrometheusMetricReader and mount /metrics route in FastAPI
- [x] Epic 4: Grafana Dashboards
  - [x] Build and auto-provision Grafana dashboards
  - [x] Add Prometheus and Grafana containers in docker-compose.yml
- [x] Epic 5: Failure Rate & Timeout Pattern Tracking
  - [x] Build FailureTracker class
  - [x] Wire timeout and retry tracking into pipeline components
- [x] Epic 6: Alerting Rules & Runbooks
  - [x] Define multi-tier alerts in `alert_rules.yml`
  - [x] Write operational runbooks in `docs/runbooks/`
- [x] Epic 7: Dependencies, Configuration, and Documentation
  - [x] Document observability architecture, dashboards, and Jaeger guides
  - [x] Write ADR 0018 (Observability Stack)
  - [x] Configure environment variables and Makefile targets

## Phase 10: Deployment and Cloud Infrastructure (Complete)

- [x] Epic 1: Production-Grade Dockerfiles
  - [x] Task 1.1: Multi-stage API Dockerfile with curl health check
  - [x] Task 1.2: Multi-stage Celery Worker Dockerfile with ping health check
  - [x] Task 1.3: Multi-stage Guardrails Dockerfile with slim python & health check
  - [x] Task 1.4: Multi-stage Frontend Dockerfile with wget health check
  - [x] Task 1.5: Optimized .dockerignore file exclusions
- [x] Epic 2: Terraform Infrastructure as Code (Complete)
  - [x] Task 2.1: Initialize provider, remote state, APIs enablement configuration (`main.tf`)
  - [x] Task 2.2: Implement configurable input variables & validation (`variables.tf`)
  - [x] Task 2.3: Expose resource endpoints and metadata attributes (`outputs.tf`)
  - [x] Task 2.4: Setup custom VPC, subnets, NAT, and database peering (`network.tf`)
  - [x] Task 2.5: Configure custom Node SA & Workload Identity bindings (`iam.tf`)
  - [x] Task 2.6: Create Artifact Registry repository with cleanup rules (`registry.tf`)
  - [x] Task 2.7: Define GCP Secret Manager placeholders and versioning (`secrets.tf`)
  - [x] Task 2.8: Provision Private GKE Autopilot cluster with lifecycle guards (`gke.tf`)
  - [x] Task 2.9: Provision private Postgres instance & DB user (`database.tf`)
  - [x] Task 2.10: Setup monthly cost breakdown and HCL check rules (`cost_estimation.tf`)
- [x] Epic 3: Kustomize Kubernetes Manifests (Complete)
- [x] Epic 4: Secrets Management & Workload Identity (Complete)
  - [x] Task 4.1: Implement shell script (`scripts/sync_secrets.sh`) to sync secrets from Secret Manager
  - [x] Task 4.2: Add operations runbook (`docs/runbooks/secrets_rotation.md`) for secrets rotation
- [x] Epic 5: CI/CD Pipeline & Cluster Teardown (GitHub Actions) (Complete)
  - [x] Task 5.1: Update CI workflow to build and push Docker images to Artifact Registry
  - [x] Task 5.2: Create deploy workflow for Staging and Production with automated rollback and alerts
  - [x] Task 5.3: Create Terraform workflow with PR planning, cost estimation, and automatic apply
  - [x] Task 5.4: Create manual teardown workflow with safety gates and resource destruction
- [x] Epic 6: Health Checks, Probes & Graceful Shutdown (Complete)
- [x] Epic 7: Deployment Documentation & Runbooks (Complete)
- [x] Epic 8: Integration, Environment Configs & Makefile (Complete)
