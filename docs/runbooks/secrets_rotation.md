# Runbook: Secrets Rotation and Synchronization

## Alert / Event Description
This runbook describes the procedure to rotate or sync application secrets (such as API keys, JWT secrets, and database credentials) deployed on GCP/GKE using Google Cloud Secret Manager and the automated `sync_secrets.sh` utility.

---

## Prerequisites
- Authenticated `gcloud` CLI with access to the target GCP Project ID.
- Authenticated `kubectl` CLI pointing to the active GKE cluster in the target namespace (`ekc-staging` or `ekc-prod`).
- Secret Manager Admin permissions (`roles/secretmanager.admin`) to update secret values in Secret Manager.
- Kubernetes deployment access (`kubectl rollout restart` permissions).

---

## Step-by-Step Rotation Procedures

### Scenario A: Gemini API Key Rotation
Rotate the Gemini API Key used by the API and worker services for Vertex AI / Gemini API access.
1. **Retrieve New Key**: Obtain the new Gemini API Key from Google AI Studio or GCP Console.
2. **Update Secret Manager**:
   Add a new version to the GCP Secret Manager secret `ekc-gemini-api-key`:
   ```bash
   echo -n "YOUR_NEW_GEMINI_API_KEY" | gcloud secrets versions add ekc-gemini-api-key --data-file=- --project="clean-carrier-500104-i0"
   ```
3. **Synchronize to Kubernetes**:
   Run the sync script for the corresponding environment to update the local base manifest and push to GKE:
   ```bash
   # For Staging
   ./scripts/sync_secrets.sh --environment staging
   kubectl apply -k infra/k8s/overlays/staging

   # For Production
   ./scripts/sync_secrets.sh --environment prod
   kubectl apply -k infra/k8s/overlays/prod
   ```
4. **Trigger Rolling Restart**:
   ```bash
   kubectl rollout restart deployment/staging-ekc-api -n ekc-staging
   kubectl rollout restart deployment/staging-ekc-worker -n ekc-staging
   ```
5. **Verify**:
   Monitor rollout status and verify that services start up cleanly:
   ```bash
   kubectl rollout status deployment/staging-ekc-api -n ekc-staging
   ```

---

### Scenario B: JWT Secret Key Rotation
Rotate the secret key used for signing JWT auth tokens. 
> [!WARNING]
> Rotating the JWT secret key will immediately invalidate all existing user sessions and log out active users.

1. **Generate New Key**:
   Generate a secure, cryptographically random key:
   ```bash
   openssl rand -hex 32
   ```
2. **Update Secret Manager**:
   Add a new version to the GCP Secret Manager secret `ekc-jwt-secret-key`:
   ```bash
   echo -n "GENERATED_RANDOM_KEY" | gcloud secrets versions add ekc-jwt-secret-key --data-file=- --project="clean-carrier-500104-i0"
   ```
3. **Synchronize to Kubernetes**:
   ```bash
   # For Staging
   ./scripts/sync_secrets.sh --environment staging
   kubectl apply -k infra/k8s/overlays/staging
   ```
4. **Trigger Rolling Restart**:
   ```bash
   kubectl rollout restart deployment/staging-ekc-api -n ekc-staging
   ```
5. **Verify**:
   Ensure users can log in using the new token configuration.

---

### Scenario C: PostgreSQL Password Rotation
Rotate the password for the database application user `knowledge_copilot_user`.
1. **Update Cloud SQL User Password**:
   Update the password on the Cloud SQL database instance:
   ```bash
   # Generate a new random password
   NEW_DB_PASS=$(openssl rand -base64 18 | tr -dc 'a-zA-Z0-9')
   
   # Apply to Cloud SQL instance
   gcloud sql users set-password knowledge_copilot_user \
     --instance="ekc-db-staging" \
     --password="${NEW_DB_PASS}" \
     --project="clean-carrier-500104-i0"
   ```
2. **Update Secret Manager**:
   Add a new version to the GCP Secret Manager secret `ekc-postgres-password`:
   ```bash
   echo -n "${NEW_DB_PASS}" | gcloud secrets versions add ekc-postgres-password --data-file=- --project="clean-carrier-500104-i0"
   ```
3. **Synchronize to Kubernetes**:
   ```bash
   ./scripts/sync_secrets.sh --environment staging
   kubectl apply -k infra/k8s/overlays/staging
   ```
4. **Trigger Rolling Restart**:
   ```bash
   kubectl rollout restart deployment/staging-ekc-api -n ekc-staging
   kubectl rollout restart deployment/staging-ekc-worker -n ekc-staging
   ```
5. **Verify Connection Health**:
   Check the logs of the API container to verify connection health:
   ```bash
   kubectl logs -l app=ekc-api -n ekc-staging -c api --tail=50
   ```

---

### Scenario D: Default API Key Rotation
Rotate the default API key used for basic API authentication.
1. **Generate New API Key**:
   Generate a new API token:
   ```bash
   openssl rand -hex 24
   ```
2. **Update Secret Manager**:
   Add a new version to the GCP Secret Manager secret `ekc-default-api-key`:
   ```bash
   echo -n "GENERATED_API_KEY" | gcloud secrets versions add ekc-default-api-key --data-file=- --project="clean-carrier-500104-i0"
   ```
3. **Synchronize to Kubernetes**:
   ```bash
   ./scripts/sync_secrets.sh --environment staging
   kubectl apply -k infra/k8s/overlays/staging
   ```
4. **Trigger Rolling Restart**:
   ```bash
   kubectl rollout restart deployment/staging-ekc-api -n ekc-staging
   ```
5. **Verify**:
   Test API access with the new key.

---

## Troubleshooting & Rollback

### If Pods Crash After Sync
1. **Check Logs**:
   Check why the container failed to initialize or start:
   ```bash
   kubectl logs deployment/staging-ekc-api -n ekc-staging -c api
   ```
2. **Rollback to Previous Secret Version**:
   If the new secret is bad/invalid:
   - Revert by destroying the active version or setting the previous secret version to active.
   - Or quickly retrieve the old version value and add a new version with the old value in Secret Manager.
   - Run `./scripts/sync_secrets.sh --environment staging` again to revert the manifest configuration.
   - Re-apply and rollout restart the pods:
     ```bash
     kubectl apply -k infra/k8s/overlays/staging
     kubectl rollout restart deployment/staging-ekc-api -n ekc-staging
     ```
