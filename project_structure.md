enterprise-knowledge-copilot/
├── README.md
├── LICENSE
├── .gitignore
├── .editorconfig
├── .env.example
├── Makefile
├── pyproject.toml
├── package.json                    # only if frontend JS/TS
├── docker-compose.yml
├── docs/
│   ├── index.md
│   ├── problem-statement.md
│   ├── product-requirements.md
│   ├── architecture-overview.md
│   ├── system-design.md
│   ├── retrieval-architecture.md
│   ├── agent-orchestration.md
│   ├── ingestion-pipeline.md
│   ├── data-model.md
│   ├── model-serving.md
│   ├── evaluation-framework.md
│   ├── safety-guardrails.md
│   ├── observability.md
│   ├── latency-cost-analysis.md
│   ├── failure-modes.md
│   ├── security-privacy.md
│   ├── deployment.md
│   ├── scalability-roadmap.md
│   ├── adr/
│   │   ├── 0001-monorepo.md
│   │   ├── 0002-vector-db-choice.md
│   │   ├── 0003-reranker-choice.md
│   │   ├── 0004-frontend-choice.md
│   │   ├── 0005-cloud-provider-choice.md
│   │   ├── 0006-queue-choice.md
│   │   ├── 0011-hybrid-scoring-evaluation.md
│   │   ├── 0012-reranker-choice.md
│   │   ├── 0015-api-v1-contract.md
│   │   ├── 0016-llm-abstraction-layer.md
│   │   ├── 0017-model-routing-strategy.md
│   │   ├── 0018-observability-stack.md
│   │   └── 003_nemo_guardrails_integration.md
│   ├── runbooks/
│   │   ├── high_p95_latency.md
│   │   ├── circuit_breaker_open.md
│   │   ├── ingestion_failures.md
│   │   ├── vector_db_connectivity.md
│   │   ├── safety_block_spike.md
│   │   └── secrets_rotation.md
│   ├── diagrams/
│   │   ├── high-level-architecture.png
│   │   ├── sequence-query-flow.png
│   │   ├── ingestion-flow.png
│   │   └── deployment-topology.png
│   └── demos/
│       └── demo-script.md
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── services/
│   │   │   ├── schemas/
│   │   │   └── middleware/
│   │   ├── tests/
│   │   └── Dockerfile
│   ├── worker/                     # ingestion/background jobs
│   │   ├── app/
│   │   ├── tests/
│   │   └── Dockerfile
│   ├── frontend/                   # Flutter or React
│   │   ├── src/ or lib/
│   │   ├── public/
│   │   ├── test/
│   │   └── Dockerfile
│   ├── evals/                      # evaluation harness service/UI
│   │   ├── runners/
│   │   ├── datasets/
│   │   ├── judges/
│   │   ├── reports/
│   │   └── tests/
│   └── gateway/                    # optional API gateway/BFF
├── packages/
│   ├── shared/                     # shared DTOs/config/utils
│   ├── rag/                        # retrieval, chunking, ranking
│   ├── agents/                     # planner, router, tool logic
│   ├── safety/                     # PII, prompt injection, policy
│   ├── observability/              # tracing/logging metrics
│   ├── llm_serving/                # vLLM client/model routing
│   └── benchmark/                  # latency/load test helpers
├── data/
│   ├── raw/
│   ├── processed/
│   ├── eval/
│   └── synthetic/
├── scripts/
│   ├── bootstrap.sh
│   ├── ingest_docs.py
│   ├── build_index.py
│   ├── run_evals.py
│   ├── load_test.py
│   ├── seed_demo_data.py
│   └── sync_secrets.sh
├── infra/
│   ├── docker/
│   ├── k8s/
│   │   ├── base/
│   │   │   ├── monitoring/
│   │   │   │   ├── prometheus/
│   │   │   │   │   ├── prometheus.yml
│   │   │   │   │   └── alert_rules.yml
│   │   │   │   └── grafana/
│   │   │   │       ├── provisioning/
│   │   │   │       │   ├── dashboards/
│   │   │   │       │   │   └── dashboard.yml
│   │   │   │       │   └── datasources/
│   │   │   │       │       └── prometheus.yml
│   │   │   │       └── dashboards/
│   │   │   │           ├── 01-request-health.json
│   │   │   │           ├── 02-retrieval-performance.json
│   │   │   │           ├── 03-generation-performance.json
│   │   │   │           ├── 04-safety.json
│   │   │   │           └── 05-system-failures.json
│   │   ├── overlays/dev/
│   │   ├── overlays/staging/
│   │   └── overlays/prod/
│   ├── terraform/
│   │   ├── .gitignore
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── network.tf
│   │   ├── iam.tf
│   │   ├── registry.tf
│   │   ├── secrets.tf
│   │   ├── gke.tf
│   │   ├── database.tf
│   │   ├── cost_estimation.tf
│   │   └── terraform.tfvars.example
│   └── helm/
├── configs/
│   ├── app.yaml
│   ├── retrieval.yaml
│   ├── models.yaml
│   ├── safety.yaml
│   └── evals.yaml
├── benchmarks/
│   ├── retrieval/
│   ├── generation/
│   ├── reranking/
│   └── serving/
├── notebooks/
│   ├── retrieval_experiments/
│   └── eval_analysis/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── backend.yml
│   │   ├── frontend.yml
│   │   ├── evals.yml
│   │   └── deploy.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
└── media/
    ├── screenshots/
    └── demo-video-link.md