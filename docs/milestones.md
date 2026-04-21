# Milestones

## Overall Status
- Current phase: Phase 0 (Foundation and Planning)
- Target next phase: Phase 1 (Baseline Retrieval System)
- Last updated: 2026-03-29

## Phase 0 Checklist

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

## Phase 1: Baseline Retrieval System (In Progress)
- [ ] Implement document ingestion pipeline (Markdown/FastAPI docs)
- [ ] Configure Qdrant collection for dense retrieval
- [ ] Build initial retrieval-only benchmark
- [ ] Create basic QA endpoint using top-k context


## Sign-off Log
- Pending: Phase 0 completion sign-off
