# Runbook: Ingestion Failure Spike

## Alert Description
Triggers when the rate of ingestion task failures exceeds `0.3` tasks/sec over a 10-minute evaluation window.

---

## Step-by-Step Diagnostic Procedure

### Step 1: Inspect Celery Worker Logs
1. View the live logs from the worker container:
   `docker compose logs worker`
2. Search for tasks matching `ingest_document` that raised exceptions:
   `docker compose logs worker | grep -E "TASK-FAILURE|worker.ingest.failed"`
3. Retrieve the full traceback of the failure to identify the exact cause (e.g. out of memory, network failure, or parser errors).

### Step 2: Check Qdrant (Vector DB) Health
1. Verify if the Qdrant service is running and accessible:
   `curl -s http://localhost:6333/health`
2. Check Qdrant disk space: Qdrant defaults to read-only mode if disk space drops below threshold. Check host disk utilization.
3. Check worker network connectivity to Qdrant:
   `docker compose exec worker curl -s http://qdrant:6333/health`

### Step 3: Check Embedding API Status and Quotas
1. Look at worker logs for errors like `429 ResourceExhausted` or `QuotaExceeded` when calling Google GenAI/Vertex AI embedding models.
2. Check your current billing and API quotas on the Google Cloud Console.

### Step 4: Examine Ingestion Source Material
1. If the failure occurs on specific documents, verify if the files are formatted correctly (UTF-8 markdown or text files).
2. Look for abnormally large documents or malformed structures that might crash the text splitter or token counter.

---

## Mitigation Options

1. **Re-ingest Failed Documents**:
   - Fix any formatting issues and re-upload/re-ingest the files.
2. **Increase Ingestion Worker Pool**:
   - If the system is overloaded, scale up the number of worker threads or processes.
3. **Handle Quota Issues**:
   - Request a quota increase for the Google GenAI embedding models, or configure Celery with exponential backoff retries.
