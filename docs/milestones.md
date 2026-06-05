# Milestones

## Overall Status
- Current phase: Phase 6 (Evaluation Harness)
- Last completed phase: Phase 5 (Safety and Guardrails) — **Complete**
- Last updated: 2026-05-28

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



