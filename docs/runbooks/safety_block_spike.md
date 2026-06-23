# Runbook: Safety Block Rate Spike

## Alert Description
Triggers when the rate of safety blocks (either inputs blocked as unsafe/off-topic, or outputs blocked as ungrounded) exceeds `0.5` blocks/sec over a 5-minute window.

---

## Step-by-Step Diagnostic Procedure

### Step 1: Identify Block Reasons in Logs
1. View the structured logs on the API or Guardrails containers to find `safety.blocked` or `guardrails.blocked` events:
   `docker compose logs api | grep "safety.blocked"`
   `docker compose logs guardrails | grep "guardrails.blocked"`
2. Inspect the fields in the structured log payload:
   - `reason`: jailbreak, off_topic, hallucination, or PII.
   - `is_safe`, `is_off_topic`, `is_grounded`.
   - `query` / `output` snippets.

### Step 2: Differentiate Attack vs. False Positives
1. **Adversarial / Injection Attack**:
   - Check if there is a burst of repetitive inputs from a single IP or API Key trying to bypass the system's instructions.
   - Look for common injection signatures (e.g. "Ignore previous instructions", "System override").
2. **False Positive Spike (Legitimate Queries Blocked)**:
   - Check if a new dataset/release contains domain terms that are falsely flagging the off-topic or PII rails.
   - Check if the LLM self-checking prompt is failing or hallucinating blocks.

### Step 3: Verify NeMo Guardrails Health
1. Make sure the `guardrails` container is running and not overloaded:
   `docker compose ps guardrails`
   `docker compose logs guardrails --tail=100`
2. Check if the guardrails service returns internal errors that default to fallback blocking (fail-safe mode).

---

## Mitigation Options

1. **API Key/IP Throttling**:
   - If a specific user or API key is conducting a prompt injection attack, revoke the API key or apply strict rate limits to their client ID.
2. **Adjust Colang Flows**:
   - If there is a high false positive rate, edit the Colang flows or self-checking prompts in the guardrails configuration.
   - Reload/restart the guardrails service to apply the new rules:
     `docker compose restart guardrails`
3. **Refine Grounding/Hallucination Thresholds**:
   - If output blocks are spiking, investigate if the chunking size or retrieval relevance is poor, leading to the generation of ungrounded responses.
