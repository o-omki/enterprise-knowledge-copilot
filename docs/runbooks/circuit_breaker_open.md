# Runbook: Model Serving Degraded (Circuit Breaker Open)

## Alert Description
Triggers when the `llm_circuit_breaker_state` gauge transitions to state `1` (HALF_OPEN) or `2` (OPEN), indicating that repeated consecutive requests to the LLM backend have failed.

---

## Step-by-Step Diagnostic Procedure

### Step 1: Check LLM Backend Health
1. Determine which backend is active by checking the logs or the model profile configuration.
2. If using **Vertex AI**, check the Google Cloud Service Health dashboard or check credentials configuration.
3. If using a local model container (e.g. **vLLM** or Ollama), check the container health status:
   `docker compose ps`
   and verify with container logs:
   `docker compose logs <service-name>`

### Step 2: Review Structured Failure Logs
1. Inspect the api service logs:
   `docker compose logs api | grep "llm.request.failed"`
2. Inspect the failure reasons, status codes, and error messages.
3. Common issues:
   - `429 Too Many Requests` (Quota exhaustion)
   - `401 Unauthorized` / `403 Forbidden` (Expired or misconfigured API key)
   - `503 Service Unavailable` or connection timeouts (Network/DNS issues)

### Step 3: Inspect Circuit Breaker Metrics
1. Open Prometheus UI (`http://localhost:9090`).
2. Query `system_failure_total{component="llm_client"}` to check the rate of errors.
3. Query `llm_circuit_breaker_state` to determine the breaker state timeline.

---

## Mitigation Options

1. **Verify / Rotate API Credentials**:
   - Check if `GEMINI_API_KEY` or `LLM_API_KEY` is set correctly in `.env`.
   - Update `.env` and restart the affected services:
     `docker compose up -d api worker`

2. **Configure Failover Routing**:
   - Adjust `configs/models.yaml` to route queries to a different model/backend if the primary serving endpoint is down or degraded.

3. **Check/Extend Caching**:
   - Make sure Redis is up and caching is working:
     `docker compose ps redis`
     `make observability-check`
   - Cache hits bypass the circuit breaker, which helps keep critical components online during an incident.

4. **Adjust Circuit Breaker Thresholds**:
   - If the breaker is too sensitive, adjust `CIRCUIT_BREAKER_FAILURE_THRESHOLD` or `CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SEC` in `.env`.
