# Project Roadmap

## Goal
Build a production-grade enterprise knowledge copilot with hybrid RAG, multi-agent query planning, cross-encoder reranking, evaluation harness, safety filters, vLLM serving, Kubernetes deployment, and observability.

## Build Strategy
This project should be built in phases. Each phase must end with a working milestone, measurable outputs, and documentation updates. Avoid jumping into agents, Kubernetes, or vLLM too early. Build the narrowest working system first, then harden and scale it.

---

## Phase 0: Foundation and Planning

### Objective
Define the scope, architecture, corpus, and evaluation plan before implementation.

### Tasks
- finalize project name and repo structure
- define target users and primary use cases
- choose sample enterprise-style corpus
- define success metrics
- write initial docs:
  - problem statement
  - product requirements
  - architecture overview
  - roadmap
- set up monorepo structure
- configure linting, formatting, pre-commit hooks
- set up issue templates and CI skeleton

### Deliverables
- repo initialized
- docs folder created
- architecture draft completed
- base CI pipeline running

### Exit Criteria
- project goals are clear
- scope is realistic
- implementation order is documented

---

## Phase 1: Baseline Retrieval System

### Objective
Build the simplest end-to-end grounded QA system over a document corpus.

### Tasks
- build ingestion pipeline for PDFs, markdown, and text
- implement chunking and metadata preservation
- store corpus in a simple document store
- implement sparse retrieval baseline (BM25)
- implement dense retrieval baseline
- expose retrieval API
- generate answers with a single LLM call using retrieved context
- attach citations to answer output

### Deliverables
- ingest -> index -> retrieve -> answer flow
- first working API
- baseline demo

### Exit Criteria
- user can ask a question and get a citation-backed answer
- sparse and dense retrieval both work
- system works locally through Docker Compose

### Notes
This phase is about proving the end-to-end loop. Do not add agents yet.

---

## Phase 2: Hybrid Retrieval and Retrieval Quality Improvements

### Objective
Improve retrieval quality beyond the baseline.

### Tasks
- combine sparse and dense retrieval
- implement reciprocal rank fusion or weighted fusion
- add metadata-aware filtering
- experiment with chunking strategies
- add retrieval diagnostics
- evaluate recall@k and MRR across retrieval strategies
- document trade-offs

### Deliverables
- hybrid retriever
- retrieval evaluation scripts
- retrieval comparison report

### Exit Criteria
- hybrid retrieval outperforms a baseline on selected metrics
- retrieval experiments are reproducible

### Notes
This is where your system begins to look serious.

---

## Phase 3: Cross-Encoder Reranking

### Objective
Improve relevance before generation.

### Tasks
- add candidate reranking after retrieval
- compare top-k retrieval vs top-k reranked quality
- measure latency overhead
- evaluate impact on final answer quality
- add configuration to enable/disable reranking

### Deliverables
- reranker module
- reranking benchmarks
- updated quality metrics

### Exit Criteria
- reranking improves answer or retrieval quality enough to justify its cost
- latency impact is measured and documented

---

## Phase 4: Multi-Agent Query Planning

### Objective
Support harder user questions through structured planning.

### Tasks
- define query classes:
  - direct lookup
  - ambiguous query
  - multi-hop synthesis
  - comparative query
- add router/planner component
- implement query decomposition
- retrieve evidence per sub-question
- aggregate evidence before answer generation
- add tracing for planner decisions

### Deliverables
- planner agent
- retrieval agent/tool
- synthesis flow
- traces showing step-by-step execution

### Exit Criteria
- system handles multi-step queries better than single-pass retrieval
- planner failures are observable and debuggable

### Notes
Do not build five fancy agents at once. Start with a simple planner + retriever + synthesizer pattern.

## Phase 5: Safety and Guardrails

### Objective
Establish a production-grade, enterprise-aligned safety layer using NVIDIA NeMo Guardrails, Vertex AI (Gemini), and Private AI to mitigate prompt injection, redact PII, enforce conversational boundaries, and detect ungrounded answers/hallucinations.

For a comprehensive blueprint, directory structure, task breakdown, and exit SLA metrics, refer to the [Phase 5 Safety & Guardrails Implementation Plan](file:///home/omki/.gemini/antigravity/brain/64ab4120-512f-4fff-9f32-0115e723a103/phase5_safety_guardrails_plan.md).

### Core Tasks
- **Microservice Infrastructure**: Deploy NeMo Guardrails as an independent microservice container connected to Vertex AI (Gemini-3-flash).
- **PII Masking & DLP**: Integrate the Private AI engine to mask sensitive patterns in inputs/outputs, backed by zero-latency local regex pre-filters.
- **Input Guardrails**: Formulate Colang 2.0 flows and self-checking prompts to defend against jailbreaks, prompt injection, and off-topic requests.
- **Output Guardrails**: Implement entailment-based grounding checks (`self_check_facts`) to ensure answers are strictly backed by retrieved RAG evidence.
- **Refusal UX**: Set up safety gateway middleware in the FastAPI API layer with polite error schemas and offline graceful degradation fallbacks.
- **Adversarial Evaluation**: Compile a static attack dataset and construct an automated red-teaming harness driven by generative agents to test safety policies and produce scorecards.

### Deliverables
- Independent safety-guardrails microservice Uvicorn server and Docker configuration.
- Local safety package client SDK (`packages/safety`) and API gateway interceptors.
- Static and generative dynamic adversarial benchmark evaluation suites (`data/eval/safety`).
- Detailed safety baseline report scorecard showing deflection metrics, false-positive refusal rates, and latency overheads.

### Exit Criteria
- **100%** jailbreak deflection rate on standard static datasets and **>98%** on dynamic red-teaming.
- **0%** sensitive PII leakage under test validation.
- **>95%** ungrounded fact/hallucination deflection accuracy.
- **<2%** false-positive refusal rate on clean queries.
- **<800ms** P95 latency overhead introduced by the guardrails pipeline.
- Successful implementation of fail-safe degradation on microservice outage.

---

## Phase 6: Evaluation Harness

### Objective
Make the system measurable and regression-safe.

### Tasks
- define evaluation dataset
- build benchmark runner
- compute:
  - recall@k
  - MRR / nDCG
  - answer correctness
  - faithfulness
  - citation quality
  - latency
  - cost
- add LLM-as-judge where useful
- add regression suite for system changes
- generate scorecards per experiment

### Deliverables
- evaluation pipeline
- benchmark scripts
- versioned eval reports

### Exit Criteria
- any major retrieval or prompting change can be evaluated reproducibly
- baseline and improved systems can be compared side-by-side

---

## Phase 7: API and UI Productization

### Objective
Wrap the system into a usable product interface.

### Tasks
- finalize backend API contracts
- add session handling
- add frontend:
  - query input
  - answer display
  - citations panel
  - trace or reasoning summary view
  - latency/source diagnostics view
- add error states and loading flows
- add auth placeholder if needed

### Deliverables
- usable API
- working web UI
- demoable product experience

### Exit Criteria
- a user can interact with the system smoothly end-to-end
- answers, sources, and system states are visible

### Notes
React/Next.js is likely the easiest option. Flutter is acceptable if cross-platform matters to you.

---

## Phase 8: Serving and Inference Optimization

### Objective
Improve model serving realism and performance.

### Tasks
- integrate vLLM for generation serving
- compare against baseline model serving
- measure TTFT, throughput, and P95 latency
- tune prompt length and retrieval depth
- explore model routing options
- document inference cost/latency trade-offs

### Deliverables
- vLLM serving setup
- serving benchmark report
- optimized inference config

### Exit Criteria
- serving stack is production-like
- latency and throughput gains are measured

---

## Phase 9: Observability and Reliability

### Objective
Make the system inspectable and operationally mature.

### Tasks
- add structured logging
- add traces for ingestion, retrieval, reranking, planning, and generation
- publish Prometheus metrics
- build Grafana dashboards
- track failure rates and timeout patterns
- define alerts and runbooks

### Deliverables
- dashboards
- trace views
- alerts
- reliability docs

### Exit Criteria
- key pipeline stages are observable
- failures can be diagnosed without reading raw code

---

## Phase 10: Deployment and Cloud Infrastructure

### Objective
Deploy the system in a production-like environment.

### Tasks
- dockerize all services
- add Kubernetes manifests or Helm charts
- define staging and production environments
- provision infra with Terraform if desired
- configure secrets management
- deploy backend, worker, vector DB, and UI
- document setup and rollback procedures

### Deliverables
- cloud deployment
- Kubernetes manifests
- deployment guide
- environment configs

### Exit Criteria
- system can be deployed and demonstrated outside local development
- deployment steps are reproducible

---

## Phase 11: Hardening and Showcase

### Objective
Prepare the project for interviews, demos, and portfolio review.

### Tasks
- polish README
- add architecture diagrams
- add benchmark summary tables
- record demo video
- add screenshots
- write limitations and future work
- improve onboarding and setup docs

### Deliverables
- polished repo
- demo assets
- final documentation set

### Exit Criteria
- a reviewer can understand the project in under 10 minutes
- the repo clearly shows engineering depth, not just features

---

## Recommended Order Summary
1. Foundation
2. Baseline retrieval
3. Hybrid retrieval
4. Reranking
5. Query planning
6. Safety
7. Evaluation
8. API + UI
9. Serving optimization
10. Observability
11. Deployment
12. Hardening

## Important Principle
Build from simplest reliable core to advanced production concerns. Do not start with agents, Kubernetes, or complex cloud setup before the retrieval backbone works and is measurable.