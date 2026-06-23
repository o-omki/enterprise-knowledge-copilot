# Runbook: Vector DB Connectivity Failure

## Alert Description
Triggers when connection errors between the application services (API, workers) and the Qdrant database are detected.

---

## Step-by-Step Diagnostic Procedure

### Step 1: Check Qdrant Container Status
1. Check if the container is running and what its health/status is:
   `docker compose ps qdrant`
2. Check if the port `6333` is exposed and listening:
   `netstat -tuln | grep 6333` or `ss -tuln | grep 6333`

### Step 2: Review Qdrant System Logs
1. View logs for critical service events, indexing issues, or unexpected crashes:
   `docker compose logs qdrant`
2. Check if the database encountered an out-of-disk error or is doing a lengthy storage optimization.

### Step 3: Verify Network Partition / Internal Resolution
1. Test connectivity inside the API or worker container:
   `docker compose exec api curl -s http://qdrant:6333/health`
2. If this fails but the container is running, check the Docker network:
   `docker network ls`
   `docker network inspect enterprise-knowledge-copilot_default` (or matching network name)

---

## Mitigation and Recovery Procedure

1. **Restart Qdrant**:
   - Perform a clean restart of the Qdrant database service:
     `docker compose restart qdrant`
   - Wait 1 minute for Qdrant to load stored collections and indices from disk.

2. **Verify Collection and Index Health**:
   - List current collections to ensure they are loaded and active:
     `curl -s http://localhost:6333/collections`
   - Inspect the specific `enterprise_knowledge` collection state:
     `curl -s http://localhost:6333/collections/enterprise_knowledge`

3. **Check Data Volumes**:
   - Ensure the `qdrant_data` volume is mounted correctly and not corrupted.
