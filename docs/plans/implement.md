# Phase 10: Deployment & Cloud Infrastructure

Deploy the Enterprise Knowledge Copilot in a production-like environment on GCP using GKE Autopilot, Cloud SQL, Artifact Registry, and Secret Manager — provisioned via Terraform and deployed via GitHub Actions + Kustomize. Includes automated cluster teardown, cost estimation, and Terraform lifecycle safeguards to demonstrate FinOps and defensive architecture competencies.

---

## Resolved Decisions

| Question | Decision |
|----------|----------|
| Redis strategy | Deploy Redis as a Deployment on GKE (cheapest, not HA) |
| Jaeger persistence | Ephemeral deployment on GKE (note Cloud Trace as future enhancement) |
| Monitoring stack | Deploy Prometheus + Grafana on GKE (preserves existing 5 dashboards) |
| Cost controls | Both: cost-estimation step (FinOps) + Terraform lifecycle rules (defensive architecture) |
| Cluster teardown | Add manual teardown workflow to GitHub Actions to prevent leaving infra running |

---

## Proposed Changes

### Epic 1: Production-Grade Dockerfiles
> Containerize all services with multi-stage builds, non-root users, health checks, and minimal image footprint.

#### [NEW] [Dockerfile](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/api/Dockerfile)
- Multi-stage Python 3.11-slim build
- Stage 1 (`builder`): install build tools, compile dependencies into a virtualenv
- Stage 2 (`runner`): copy only virtualenv + application code
- Non-root user `appuser` (UID 1001)
- `HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/health || exit 1`
- Copy only `apps/api`, `apps/worker`, `packages/`, `configs/`, `pyproject.toml`, `README.md`
- Expose port 8000
- Entrypoint: `uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000`

#### [NEW] [Dockerfile](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/worker/Dockerfile)
- Same multi-stage base as API
- Runs `celery -A apps.worker.celery_app worker --loglevel=info --concurrency=2`
- No exposed ports (worker is internal)
- Health check: `celery -A apps.worker.celery_app inspect ping --timeout 5`

#### [MODIFY] [Dockerfile](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/guardrails/Dockerfile)
- Convert from `python:3.11` to multi-stage `python:3.11-slim` build
- Add non-root user `appuser` (UID 1001)
- Add `HEALTHCHECK` instruction hitting `/health`
- Minimize image layers

#### [MODIFY] [Dockerfile](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/frontend/Dockerfile)
- Already has multi-stage build and non-root user — minor tweaks:
- Add `HEALTHCHECK --interval=30s CMD wget -qO- http://localhost:3000/ || exit 1`
- Verify `output: 'standalone'` is set in `next.config.ts`

#### [NEW] [.dockerignore](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/.dockerignore)
```
.git
.venv
.mypy_cache
.pytest_cache
.ruff_cache
__pycache__
*.egg-info
node_modules
data/
.env
.env.*
!.env.example
infra/
docs/
notebooks/
*.md
!README.md
```

---

### Epic 2: Terraform Infrastructure as Code
> Provision all GCP resources declaratively with lifecycle safeguards and cost estimation. Demonstrates both FinOps awareness and defensive IaC architecture.

#### [NEW] [main.tf](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/terraform/main.tf)
- `required_providers`: `google` (~> 6.0), `google-beta` (~> 6.0)
- `terraform` backend: GCS bucket for remote state (`ekc-terraform-state`)
- Enable required GCP APIs: `container.googleapis.com`, `sqladmin.googleapis.com`, `artifactregistry.googleapis.com`, `secretmanager.googleapis.com`, `compute.googleapis.com`, `servicenetworking.googleapis.com`

#### [NEW] [variables.tf](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/terraform/variables.tf)
- `project_id` — default `clean-carrier-500104-i0`
- `region` — default `us-central1`
- `environment` — `staging` | `prod`
- `db_tier` — default `db-f1-micro`
- `gke_cluster_name` — default `ekc-cluster`
- `enable_deletion_protection` — default `true` (lifecycle guard)
- Variable validations:
  ```hcl
  validation {
    condition     = contains(["db-f1-micro", "db-g1-small", "db-custom-2-4096"], var.db_tier)
    error_message = "db_tier must be one of: db-f1-micro, db-g1-small, db-custom-2-4096. Prevents accidental expensive tier."
  }
  ```

#### [NEW] [outputs.tf](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/terraform/outputs.tf)
- GKE cluster endpoint, CA certificate
- Cloud SQL connection name, private IP
- Artifact Registry URL
- Service account emails
- **Estimated monthly cost summary** (static output block with per-resource estimates)

#### [NEW] [gke.tf](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/terraform/gke.tf)
- `google_container_cluster` — Autopilot mode, `us-central1`
- Private cluster with master authorized networks
- Workload Identity enabled
- Maintenance window: Saturday 02:00–06:00 UTC
- Release channel: `REGULAR`
- **Lifecycle safeguards**:
  ```hcl
  lifecycle {
    prevent_destroy = true  # Cannot accidentally destroy cluster
    ignore_changes  = [node_config]  # Autopilot manages nodes
  }
  ```
- Resource labels: `environment`, `project`, `managed-by = "terraform"`

#### [NEW] [database.tf](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/terraform/database.tf)
- `google_sql_database_instance` — PostgreSQL 16, `db-f1-micro`
- Private IP via VPC peering (no public IP)
- Automated daily backups, point-in-time recovery enabled
- **Lifecycle safeguards**:
  ```hcl
  lifecycle {
    prevent_destroy = true   # Never accidentally drop the database
  }
  deletion_protection = var.enable_deletion_protection
  ```
- `google_sql_database` — `knowledge_copilot`
- `google_sql_user` — application user (password from Secret Manager)

#### [NEW] [registry.tf](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/terraform/registry.tf)
- `google_artifact_registry_repository` — Docker format, `us-central1`, name `ekc-images`
- Cleanup policy: keep only last 10 image versions per tag (cost control)
- IAM binding for GKE service account to pull images

#### [NEW] [secrets.tf](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/terraform/secrets.tf)
- `google_secret_manager_secret` resources:
  - `ekc-gemini-api-key`
  - `ekc-jwt-secret-key`
  - `ekc-postgres-password`
  - `ekc-default-api-key`
- IAM: Workload Identity SA gets `roles/secretmanager.secretAccessor`
- **Lifecycle**: `prevent_destroy = true` on all secrets

#### [NEW] [iam.tf](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/terraform/iam.tf)
- GKE node SA with minimal roles (`roles/logging.logWriter`, `roles/monitoring.metricWriter`, `roles/artifactregistry.reader`)
- Workload Identity SAs for API/Worker/Guardrails
- Principle of least privilege throughout

#### [NEW] [network.tf](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/terraform/network.tf)
- VPC `ekc-vpc` with subnet `ekc-subnet` (secondary ranges for pods/services)
- Cloud NAT for outbound internet (Vertex AI API calls)
- Private services access for Cloud SQL
- Firewall rules: deny all ingress by default, allow only required

#### [NEW] [cost_estimation.tf](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/terraform/cost_estimation.tf)
- **FinOps cost estimation module** — outputs a human-readable cost breakdown:
  ```hcl
  output "estimated_monthly_cost" {
    description = "Estimated monthly cost breakdown (USD)"
    value = {
      gke_autopilot    = "~$74/mo (0.5 vCPU × $31 + 2 GB × $3.4 × 6 pods)"
      cloud_sql        = "~$8/mo (db-f1-micro, staging)"
      artifact_registry = "~$0.10/GB stored"
      secret_manager   = "~$0.24/mo (4 secrets × 10K accesses)"
      cloud_nat        = "~$1.50/mo"
      total_staging    = "~$85–100/mo"
      total_prod       = "~$180–250/mo (higher replicas + db tier)"
    }
  }
  ```
- Terraform `check` blocks (v1.5+) for cost guardrails:
  ```hcl
  check "cost_guard_db_tier" {
    assert {
      condition     = var.environment == "prod" || var.db_tier == "db-f1-micro"
      error_message = "WARNING: Non-prod environments should use db-f1-micro to minimize costs."
    }
  }
  ```

#### [NEW] [terraform.tfvars.example](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/terraform/terraform.tfvars.example)
- Example values (never committed with real secrets)

#### [NEW] [.gitignore](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/terraform/.gitignore)
- `.terraform/`, `*.tfstate*`, `*.tfvars`, `!terraform.tfvars.example`, `.terraform.lock.hcl`

---

### Epic 3: Kustomize Kubernetes Manifests
> Define all workloads using Kustomize `base/` + environment `overlays/` for staging and production.

#### Base Manifests (`infra/k8s/base/`)

#### [NEW] [kustomization.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/kustomization.yaml)
- Lists all base resources
- Common labels: `app.kubernetes.io/part-of: ekc`, `app.kubernetes.io/managed-by: kustomize`

#### [NEW] [namespace.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/namespace.yaml)
- `ekc` namespace with resource quotas

#### [NEW] [api-deployment.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/api-deployment.yaml)
- Deployment: `ekc-api`, 2 replicas
- Container: image from Artifact Registry, port 8000
- Resource requests/limits (CPU: 250m/1000m, Memory: 512Mi/1Gi)
- Liveness probe: `GET /health` every 15s, failure threshold 3
- Readiness probe: `GET /readiness` every 10s, initial delay 10s
- Environment from ConfigMap + Secret references
- ServiceAccount with Workload Identity annotation
- `topologySpreadConstraints` for zone spread
- Graceful shutdown: `terminationGracePeriodSeconds: 30`

#### [NEW] [api-service.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/api-service.yaml)
- ClusterIP service, port 8000
- Prometheus scrape annotations

#### [NEW] [api-hpa.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/api-hpa.yaml)
- HorizontalPodAutoscaler: min 2, max 10, target CPU 70%

#### [NEW] [worker-deployment.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/worker-deployment.yaml)
- Deployment: `ekc-worker`, 1 replica
- Celery worker command
- Resource requests/limits (CPU: 250m/500m, Memory: 512Mi/1Gi)
- Liveness: exec `celery inspect ping`

#### [NEW] [guardrails-deployment.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/guardrails-deployment.yaml)
- Deployment: `ekc-guardrails`, 1 replica, port 8001
- Liveness/readiness on `/health`

#### [NEW] [guardrails-service.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/guardrails-service.yaml)
- ClusterIP, port 8001

#### [NEW] [frontend-deployment.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/frontend-deployment.yaml)
- Deployment: `ekc-frontend`, 2 replicas, port 3000
- Resource requests/limits (CPU: 100m/500m, Memory: 128Mi/256Mi)

#### [NEW] [frontend-service.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/frontend-service.yaml)
- LoadBalancer service, port 80 → 3000

#### [NEW] [qdrant-statefulset.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/qdrant-statefulset.yaml)
- StatefulSet: 1 replica, 10Gi PVC (`pd-ssd`)
- Ports 6333 + 6334

#### [NEW] [qdrant-service.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/qdrant-service.yaml)
- Headless ClusterIP service

#### [NEW] [redis-deployment.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/redis-deployment.yaml)
- Deployment: `ekc-redis`, 1 replica, `redis:7-alpine`
- Resource limits (CPU: 100m/250m, Memory: 128Mi/256Mi)

#### [NEW] [redis-service.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/redis-service.yaml)
- ClusterIP, port 6379

#### [NEW] [jaeger-deployment.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/jaeger-deployment.yaml)
- `jaegertracing/all-in-one:latest`, ephemeral storage
- Ports: 16686, 4317, 4318

#### [NEW] [jaeger-service.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/jaeger-service.yaml)
- ClusterIP for OTLP + UI

#### [NEW] [prometheus-deployment.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/prometheus-deployment.yaml)
- `prom/prometheus:latest`, port 9090
- ConfigMap mount for `prometheus.yml` and `alert_rules.yml`

#### [NEW] [grafana-deployment.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/grafana-deployment.yaml)
- `grafana/grafana:latest`, port 3000
- ConfigMap mounts for provisioning + dashboards

#### [NEW] [monitoring-services.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/monitoring-services.yaml)
- ClusterIP for Prometheus (9090), Grafana (3001)

#### [NEW] [configmap.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/configmap.yaml)
- `ekc-config` with non-secret env vars: `QDRANT_URL`, `REDIS_URL`, `OTEL_*`, `LOG_FORMAT`, `METRICS_ENABLED`, `PROMPT_VERSION`, `GCP_PROJECT_ID`, `GCP_LOCATION`, model names

#### [NEW] [secrets.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/secrets.yaml)
- K8s Secret placeholder `ekc-secrets` (values injected per environment via `sync_secrets.sh`)
- Keys: `GEMINI_API_KEY`, `JWT_SECRET_KEY`, `POSTGRES_DSN`, `DEFAULT_API_KEY`

#### [NEW] [service-account.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/service-account.yaml)
- K8s ServiceAccount `ekc-workload-sa` with Workload Identity annotation

#### [NEW] [network-policy.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/base/network-policy.yaml)
- Default deny-all ingress
- Allow: frontend → API, API → guardrails/qdrant/redis/jaeger, worker → qdrant/redis/jaeger, prometheus → all

#### Staging Overlay (`infra/k8s/overlays/staging/`)

#### [NEW] [kustomization.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/overlays/staging/kustomization.yaml)
- Namespace: `ekc-staging`, name prefix: `staging-`
- Image tags: `staging-<sha>` or `latest`
- Replica patches: API=1, frontend=1
- Lower resource limits

#### [NEW] [patches/replicas.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/overlays/staging/patches/replicas.yaml)
#### [NEW] [patches/resources.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/overlays/staging/patches/resources.yaml)
#### [NEW] [patches/configmap.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/overlays/staging/patches/configmap.yaml)
- `LOG_LEVEL=DEBUG`

#### Production Overlay (`infra/k8s/overlays/prod/`)

#### [NEW] [kustomization.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/overlays/prod/kustomization.yaml)
- Namespace: `ekc-prod`, name prefix: `prod-`
- Image tags: `v<semver>` or `prod-<sha>`
- Replica patches: API=3, frontend=2

#### [NEW] [patches/replicas.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/overlays/prod/patches/replicas.yaml)
#### [NEW] [patches/resources.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/overlays/prod/patches/resources.yaml)
#### [NEW] [patches/configmap.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/overlays/prod/patches/configmap.yaml)
- `LOG_LEVEL=WARNING`

#### [NEW] [pdb.yaml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/infra/k8s/overlays/prod/pdb.yaml)
- PodDisruptionBudget for API: `minAvailable: 2`

---

### Epic 4: Secrets Management & Workload Identity
> Configure GCP Secret Manager integration with GKE via Workload Identity Federation.

#### [NEW] [scripts/sync_secrets.sh](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/scripts/sync_secrets.sh)
- Shell script that reads secrets from GCP Secret Manager and creates/updates K8s Secrets
- Accepts `--environment staging|prod` flag
- Idempotent — safe to run multiple times
- Used in CI/CD deploy jobs and manual setup
- Validates all required secrets exist before applying

#### [NEW] [docs/runbooks/secrets_rotation.md](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/docs/runbooks/secrets_rotation.md)
- Step-by-step for rotating each secret:
  - Gemini API key: rotate in GCP Console → re-run `sync_secrets.sh` → rolling restart
  - JWT secret: update Secret Manager → sync → restart API pods
  - Postgres password: update Cloud SQL + Secret Manager → sync → restart
  - API keys: update Secret Manager → sync → restart

---

### Epic 5: CI/CD Pipeline & Cluster Teardown (GitHub Actions)
> Extend CI with build, push, deploy, and automated teardown workflows. The teardown workflow ensures you never accidentally leave billable infrastructure running.

#### [MODIFY] [ci.yml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/.github/workflows/ci.yml)
- Keep existing `python-checks` job (lint + test)
- Add `build-images` job (on push to `main` and tags `v*`):
  - Authenticate to GCP via Workload Identity Federation (OIDC, no key files)
  - Build 4 Docker images (api, worker, guardrails, frontend)
  - Push to Artifact Registry: `us-central1-docker.pkg.dev/clean-carrier-500104-i0/ekc-images/<service>:<sha>`
  - Tag with `${{ github.sha }}` and `latest`
- Job dependency: `build-images` requires `python-checks` to pass

#### [NEW] [deploy.yml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/.github/workflows/deploy.yml)
- **Staging**: triggered on push to `main` after `build-images` completes
  - `gcloud container clusters get-credentials ekc-cluster --region us-central1`
  - `scripts/sync_secrets.sh --environment staging`
  - `kubectl apply -k infra/k8s/overlays/staging`
  - `kubectl rollout status deployment/staging-ekc-api -n ekc-staging --timeout=300s`
  - On failure: `kubectl rollout undo` + Slack notification
- **Production**: triggered on tag push `v*`
  - Same steps but targeting `prod` overlay
  - `environment: production` (requires manual approval in GitHub)

#### [NEW] [terraform.yml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/.github/workflows/terraform.yml)
- Triggered on changes to `infra/terraform/**`
- `plan` job on PRs: runs `terraform plan`, comments output on PR
- `apply` job on merge to `main`: `terraform apply -auto-approve`
- Both jobs include **cost estimation** step:
  ```yaml
  - name: Cost Estimation
    run: |
      terraform plan -out=tfplan
      terraform show -json tfplan > plan.json
      # Parse and display estimated costs from outputs
      terraform output -json estimated_monthly_cost
  ```

#### [NEW] [teardown.yml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/.github/workflows/teardown.yml)
- **Manual dispatch only** (`workflow_dispatch`) with required confirmation input
- Purpose: Fully tear down all cloud infrastructure when not needed (e.g., between interview prep sessions)
- Steps:
  1. **Delete K8s workloads**: `kubectl delete -k infra/k8s/overlays/staging --ignore-not-found`
  2. **Delete GKE cluster**: `gcloud container clusters delete ekc-cluster --region us-central1 --quiet`
  3. **Destroy Terraform-managed resources**: `terraform destroy -auto-approve` (with `prevent_destroy` temporarily overridden via `-target` flags)
  4. **Clean up Artifact Registry images**: `gcloud artifacts docker images delete` (optional, keep registry)
  5. **Preserve state**: Terraform remote state in GCS is retained for re-provisioning
- Safety gates:
  - Requires typing `DESTROY-INFRASTRUCTURE` as confirmation input
  - Logs all resources being destroyed
  - Outputs summary of what was deleted and estimated savings
- Companion **re-provision** instructions in `deployment.md`:
  ```
  # Re-create everything from scratch:
  terraform apply
  scripts/sync_secrets.sh --environment staging
  kubectl apply -k infra/k8s/overlays/staging
  ```

---

### Epic 6: Health Checks, Probes & Graceful Shutdown
> Ensure all services handle K8s lifecycle signals correctly.

#### [MODIFY] [main.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/api/app/main.py)
- Add `/readiness` endpoint that checks:
  - Redis: `await redis_client.ping()`
  - Qdrant: HTTP GET to Qdrant health endpoint
  - PostgreSQL: `SELECT 1` via SQLAlchemy
  - Returns 503 with details if any dependency is down
- Existing `/health` remains as lightweight liveness probe (no dependency checks)
- Add `SIGTERM` handler in lifespan: set a `shutting_down` flag, return 503 on `/readiness`, drain in-flight for `terminationGracePeriodSeconds`

#### [MODIFY] [main.py](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/apps/guardrails/main.py)
- Add `/readiness` endpoint (checks Vertex AI connectivity)
- Add graceful shutdown signal handling

---

### Epic 7: Deployment Documentation & Runbooks
> Comprehensive deployment guide covering local, staging, and production environments with teardown procedures.

#### [MODIFY] [deployment.md](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/docs/deployment.md)
Complete rewrite covering:
- **Prerequisites**: GCP project, `gcloud` CLI, `terraform`, `kubectl`, `kustomize`
- **Quick Start**: Local development with Docker Compose
- **Infrastructure Setup**: Terraform init/plan/apply with cost estimation review
- **Staging Deployment**: Manual and CI/CD flow
- **Production Deployment**: Tag-based release flow with approval gate
- **Teardown & Re-Provision**: How to use the teardown workflow, re-provision from scratch, cost impact
- **Rollback Procedures**: `kubectl rollout undo`, Terraform state rollback
- **Cost Management**: Monthly cost breakdown, tips for minimizing costs during idle periods
- **Troubleshooting**: Common failure modes and resolution steps
- **Architecture Diagram**: GKE topology with all services, databases, networking

#### [NEW] [docs/adr/0019-deployment-architecture.md](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/docs/adr/0019-deployment-architecture.md)
- Decision: GKE Autopilot + Cloud SQL + Kustomize + GitHub Actions + Terraform lifecycle guards + teardown automation
- Rationale: Cost-optimized, interview-friendly, reproducible
- Alternatives considered, consequences

#### [NEW] [docs/runbooks/deployment_rollback.md](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/docs/runbooks/deployment_rollback.md)
- Kubernetes rollback procedures per service
- Terraform state recovery
- Database migration rollback via Alembic

---

### Epic 8: Integration, Environment Configs & Makefile
> Wire everything together with updated configs, Makefile targets, and environment files.

#### [MODIFY] [Makefile](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/Makefile)
Add targets:
- `docker-build` — builds all 4 service images locally
- `docker-push` — tags and pushes to Artifact Registry
- `tf-init` — `terraform -chdir=infra/terraform init`
- `tf-plan` — `terraform -chdir=infra/terraform plan` (includes cost output)
- `tf-apply` — `terraform -chdir=infra/terraform apply`
- `tf-destroy` — `terraform -chdir=infra/terraform destroy` (with confirmation prompt)
- `k8s-apply-staging` — `kubectl apply -k infra/k8s/overlays/staging`
- `k8s-apply-prod` — `kubectl apply -k infra/k8s/overlays/prod`
- `k8s-teardown-staging` — `kubectl delete -k infra/k8s/overlays/staging`
- `k8s-status` — shows deployment status, pod health across namespaces
- `k8s-logs` — tails logs from a specified service

#### [MODIFY] [.env.example](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/.env.example)
- Add `GKE_CLUSTER_NAME=ekc-cluster`
- Add `GCP_REGION=us-central1`
- Add `ARTIFACT_REGISTRY_URL=us-central1-docker.pkg.dev/clean-carrier-500104-i0/ekc-images`

#### [MODIFY] [docker-compose.yml](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/docker-compose.yml)
- Add `build:` context to `api` and `worker` services (opt-in with `docker compose --profile production`)
- Keep existing dev-mode with source volume mounts as the default profile

#### [MODIFY] [project_structure.md](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/project_structure.md)
- Add `infra/terraform/*.tf` file listing
- Add `infra/k8s/base/` and `infra/k8s/overlays/` structure
- Add new Dockerfiles, workflow files, scripts

#### [MODIFY] [milestones.md](file:///mnt/e_drive/Codes/enterprise-knowledge-copilot/docs/milestones.md)
- Add Phase 10 task tracker with all 8 epics and sub-tasks
- Mark current phase as "Phase 10 (In Progress)"

---

## Verification Plan

### Automated Tests

```bash
# 1. Docker builds succeed (no missing runtime deps)
make docker-build

# 2. Terraform validates and cost estimation renders
cd infra/terraform && terraform init && terraform validate
terraform plan -out=tfplan && terraform output estimated_monthly_cost

# 3. Kustomize builds render valid YAML
kubectl kustomize infra/k8s/overlays/staging | kubectl apply --dry-run=client -f -
kubectl kustomize infra/k8s/overlays/prod | kubectl apply --dry-run=client -f -

# 4. Existing unit tests still pass
make test

# 5. CI workflow lint
actionlint .github/workflows/*.yml
```

### Manual Verification
- `terraform plan` shows expected resources with cost estimates
- Docker images run locally and respond to `/health` and `/readiness`
- Staging deploy to GKE: all pods `Running`, health checks pass
- API responds behind K8s service LoadBalancer
- Grafana dashboards load with metrics from GKE stack
- Rollback restores previous version: `kubectl rollout undo`
- Teardown workflow destroys all resources cleanly
- Re-provision from scratch works within 10 minutes
