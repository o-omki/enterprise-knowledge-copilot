import logging
import os

import httpx

from packages.safety.fast_filters import contains_pii_local, redact_local_pii

logger = logging.getLogger("packages.safety.client")


class SafetyGuardrailsClient:
    """FastAPI-based client SDK to validate queries and answers against the Guardrails microservice.

    If the guardrails microservice is unreachable or errors, it falls back gracefully to local
    high-speed regex checking.
    """

    def __init__(self, service_url: str | None = None):
        self.service_url = (
            service_url or os.getenv("GUARDRAILS_SERVICE_URL", "http://localhost:8001")
        ).rstrip("/")

    async def validate_input(self, query: str) -> dict:
        """Sends query to /validate/input for input safety and PII masking checks."""
        url = f"{self.service_url}/validate/input"

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.post(url, json={"query": query})
                if response.status_code == 200:
                    return response.json()

                logger.error(
                    "Guardrails microservice returned status %d: %s",
                    response.status_code,
                    response.text,
                )
        except Exception as e:
            logger.error(f"Unreachable guardrails microservice at {self.service_url}: {e}")

        # Fail-safe local fallback
        logger.warning(
            "Unreachable/error guardrails microservice. Triggering fast local regex checking "
            "fallback."
        )

        # Local regex check for PII
        filtered_query = redact_local_pii(query)
        is_pii_detected = contains_pii_local(query)

        # Jailbreak heuristics
        is_safe = True
        refusal_message = None
        lower_query = query.lower()
        jailbreak_keywords = [
            "ignore previous instructions",
            "system prompt",
            "dan mode",
            "override policy",
        ]
        if any(kw in lower_query for kw in jailbreak_keywords):
            is_safe = False
            refusal_message = (
                "I cannot fulfill this request as it violates enterprise security policies."
            )

        return {
            "is_safe": is_safe,
            "is_off_topic": False,
            "is_pii_detected": is_pii_detected,
            "filtered_query": filtered_query,
            "refusal_message": refusal_message,
            "fallback_active": True,
        }

    async def validate_output(self, query: str, answer: str, context: list[str]) -> dict:
        """Sends generated answer and context chunks to /validate/output for grounding
        validation.
        """
        url = f"{self.service_url}/validate/output"

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.post(
                    url, json={"query": query, "response": answer, "context": context}
                )
                if response.status_code == 200:
                    return response.json()

                logger.error(
                    "Guardrails microservice returned status %d: %s",
                    response.status_code,
                    response.text,
                )
        except Exception as e:
            logger.error(f"Unreachable guardrails microservice at {self.service_url}: {e}")

        # Fallback for output grounding
        logger.warning(
            "Unreachable/error guardrails microservice. "
            "Passing through answer to maintain service continuity."
        )
        return {"is_grounded": True, "refusal_message": None, "fallback_active": True}
