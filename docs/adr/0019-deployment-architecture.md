# ADR 0019: Deployment and Cloud Infrastructure Architecture

**Status:** Accepted
**Date:** 2026-07-12

## Context and Problem Statement

To transition the Enterprise Knowledge Copilot from a local-only Docker Compose prototype to a production-grade enterprise application, we require a scalable, secure, and reproducible deployment architecture on Google Cloud Platform (GCP). The deployment design must satisfy the following constraints and requirements:
1. **Production Realism**: Replicate the network topologies, security models, and orchestration mechanisms used in enterprise environments.
2. **Security & Isolation**: Enforce private networking, minimize public endpoints, eliminate static key files (credentials), and manage secrets securely.
3. **Environment Parity**: Support clean segregation between `staging` and `production` environments with minimal configuration drift.
4. **FinOps & Cost Optimization**: Prevent accidental provisioning of expensive resources and ensure cost-efficient infrastructure management, including complete teardown of non-persistent components when idle.
5. **Observability Integration**: Maintain compatibility with the Prometheus, Grafana, and Jaeger observability stack deployed alongside the services.

## Decision

We designed and implemented a cloud deployment system utilizing declarative infrastructure, native container orchestration, and automated delivery pipelines:

1. **Orchestration (GKE Autopilot)**: Provisioned a Google Kubernetes Engine (GKE) Autopilot cluster (`ekc-cluster` in `us-central1`). GKE Autopilot manages node provisioning, auto-scaling, OS upgrades, and security configurations natively, reducing operational overhead while preserving Kubernetes standard APIs.
2. **Infrastructure-as-Code (Terraform)**: Declaratively provisioned all resources using Terraform (v1.5+). Features include:
   - **Lifecycle Safeguards**: Enabled `prevent_destroy = true` on the GKE cluster, Cloud SQL database instances, and Secret Manager entries to prevent accidental infrastructure drops.
   - **Cost Controls**: Deployed a custom static `estimated_monthly_cost` module and introduced HCL `check` blocks that assert cost constraints (e.g., non-prod environments must use `db-f1-micro`).
3. **State & Database Storage**:
   - Deployed a private PostgreSQL 16 database using GCP **Cloud SQL** (`db-f1-micro` for staging, scaling up to `db-custom-2-4096` in production). Private IP integration is managed via Private Services Access (VPC peering), ensuring no public internet routes reach the database.
   - Vector databases (Qdrant) are deployed inside GKE via a **StatefulSet** with a 10Gi Google Persistent Disk SSD (`pd-ssd`) storage class to preserve indexing state.
   - Celery worker/broker state is backed by an ephemeral Redis instance running as a standard deployment in GKE.
4. **Secret Management & Identity**:
   - Used **GCP Secret Manager** as the single source of truth for application secrets.
   - Configured **OIDC Workload Identity Federation** in GKE. Kubernetes Service Accounts are annotated to bind directly to GCP IAM Service Accounts, eliminating the need to store static GCP key files inside GitHub repository secrets or container images.
   - Implemented a secure synchronization script (`sync_secrets.sh`) to fetch secrets from Secret Manager and populate Kubernetes Secrets configurations during deploy jobs.
5. **Declarative Workload Management (Kustomize)**: Structured all Kubernetes resources under `infra/k8s/` using Kustomize with a common `base/` manifest and environment-specific `overlays/` for staging and production, avoiding Helm template complexity.
6. **Continuous Delivery (GitHub Actions)**:
   - **CI/CD Pipeline**: Configured push-to-branch pipelines that compile Docker images using multi-stage builds, push them to a private Google Artifact Registry repository, sync secrets, apply Kustomize overlays, and verify rollout status.
   - **Automated Rollbacks**: Automatically triggers `kubectl rollout undo` and sends Slack notifications upon deployment failures.
   - **FinOps Teardown**: Implemented a manual workflow (`teardown.yml`) with safety confirmations (`DESTROY-INFRASTRUCTURE`) to clean up GKE workloads, destroy the cluster, and delete registry images to minimize idle billing.

## Consequences

### Positive
- **Reduced Operational Overhead**: GKE Autopilot manages node lifecycle, scaling, and pricing per pod, eliminating manual node pool configuration.
- **Enhanced Security Posture**: Services run on private IPs behind NAT; Secret Manager limits secret visibility; OIDC replaces vulnerable static credentials.
- **Configuration Consistency**: Kustomize overlays cleanly separate staging and production configuration variables, eliminating templating drift.
- **FinOps Compliance**: Static cost estimation in PR comments, Terraform cost assertions, and the manual teardown workflow together ensure strict budget management during development.
- **Rapid Recovery**: Automatic failure detection triggers rollback within minutes of a bad deployment.

### Negative
- **Autopilot Constraints**: GKE Autopilot restricts low-level cluster configurations (e.g., custom daemonsets, kernel tuning, or hostPath volumes).
- **Destruction Complexity**: Temporary destruction of resources via the teardown workflow requires HCL parsing modifications to temporarily bypass `prevent_destroy` constraints before running `terraform destroy`.
- **Latency Overhead**: Deploying and tearing down GKE Autopilot clusters from scratch takes approximately 8–10 minutes, slowing down manual testing cycles compared to local Docker Compose.
