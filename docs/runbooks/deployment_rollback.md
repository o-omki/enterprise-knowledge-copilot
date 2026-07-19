# Runbook: Deployment Rollback Procedures

## Alert / Event Description
This runbook provides operators and developers with step-by-step procedures to revert/rollback system deployments when new software releases, database schema changes, or infrastructure updates cause system failures or regressions in the production or staging environments.

---

## Rollback Trigger Criteria
Initiate a rollback under the following conditions:
1. **Critical Health Failure**: The core FastAPI backend (`ekc-api`) fails to achieve a healthy state after deployment (evidenced by failing Kubernetes readiness/liveness probes or a rollout timeout).
2. **Elevated Error Rates**: A spike in API `5xx` responses, safety block spikes, or database query failures post-deployment.
3. **Database Migration Failures**: Failed database schema updates that leave the database in an inconsistent or locked state.
4. **Infrastructure Drift/Outage**: Provisioning failures or network partitioning introduced via Terraform updates.

---

## Scenario A: Kubernetes Workload Rollback

If a new container image deployment fails or introduces regressions, use native Kubernetes rolling update rollbacks.

### 1. Identify the Failing Deployment
Check the rollout status and retrieve the active revision history:
```bash
# Set target namespace (ekc-staging or ekc-prod)
export NAMESPACE="ekc-staging"

# Check rollout status
kubectl rollout status deployment/staging-ekc-api -n $NAMESPACE

# View revision history
kubectl rollout history deployment/staging-ekc-api -n $NAMESPACE
```

### 2. Execute the Rollback Command
Roll back the deployment to the immediately preceding revision:
```bash
kubectl rollout undo deployment/staging-ekc-api -n $NAMESPACE
```
To roll back to a specific older revision (e.g., revision 2):
```bash
kubectl rollout undo deployment/staging-ekc-api -n $NAMESPACE --to-revision=2
```

### 3. Verify Rollback Completion
Monitor the deployment rollout status to confirm the pods are successfully replaced:
```bash
kubectl rollout status deployment/staging-ekc-api -n $NAMESPACE
```

### 4. Repeat for Associated Services
If the release changed other services, undo the rollouts sequentially in reverse dependency order:
```bash
# Undo frontend
kubectl rollout undo deployment/staging-ekc-frontend -n $NAMESPACE

# Undo Celery worker
kubectl rollout undo deployment/staging-ekc-worker -n $NAMESPACE

# Undo Guardrails microservice
kubectl rollout undo deployment/staging-ekc-guardrails -n $NAMESPACE
```

---

## Scenario B: Database Migration Rollback (Alembic)

When a schema migration introduces breaking changes, the database schema must be downgraded using Alembic.

> [!WARNING]
> Rolling back database migrations that drop tables or columns can lead to irreversible data loss. Ensure a database backup snapshot exists before executing a downgrade in production.

### 1. Terminate or Pause Active Workers
To prevent active Celery workers or API pods from attempting query executions against a migrating/downgrading schema, scale down the workloads:
```bash
kubectl scale deployment/staging-ekc-api --replicas=0 -n $NAMESPACE
kubectl scale deployment/staging-ekc-worker --replicas=0 -n $NAMESPACE
```

### 2. Connect to the Migration Context
Run a temporary migration container or execute the downgrade via the virtual environment:
```bash
# Activate virtual environment
source .venv/bin/activate

# Check current migration head
alembic current
```

### 3. Execute the Downgrade
Downgrade the database schema by one step or to a specific revision:
```bash
# Downgrade by 1 revision
alembic downgrade -1

# Downgrade to a specific revision (e.g., e07a49875265)
alembic downgrade e07a49875265
```

### 4. Restore Workload Scale
Once the downgrade is complete, restore the application scaling configurations:
```bash
kubectl scale deployment/staging-ekc-api --replicas=2 -n $NAMESPACE
kubectl scale deployment/staging-ekc-worker --replicas=1 -n $NAMESPACE
```

---

## Scenario C: Terraform State Recovery

If a Terraform apply fails midway or locks the remote state, follow these recovery procedures.

### 1. Releasing a Locked State
If a previous deployment crashed or was canceled, you may encounter the following error:
`Error: Error acquiring the state lock...`

Find the **Lock Info ID** in the error output, then release the lock:
```bash
cd infra/terraform
terraform force-unlock <LOCK-ID>
```
> [!CAUTION]
> Only force-unlock the state if you are absolutely sure that no other Terraform process is currently modifying the infrastructure.

### 2. Recovering State from GCS Backups
The GCS backend GCS bucket (`ekc-terraform-state`) stores versioned state files.
If local or remote state files become corrupted:
1. **Navigate to the State GCS Bucket**: In the Google Cloud Console, navigate to `Storage` -> `Browser` -> `ekc-terraform-state`.
2. **Retrieve Version History**: Click on `default.tfstate` and view the version history.
3. **Restore Version**: Select and restore the last known healthy state file version.
4. **Synchronize Local State**:
   ```bash
   cd infra/terraform
   terraform init -reconfigure
   terraform refresh
   ```
5. **Verify Divergence**:
   Run a dry-run check to verify the restored state matches actual cloud infrastructure:
   ```bash
   terraform plan
   ```
