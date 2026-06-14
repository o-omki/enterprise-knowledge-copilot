import logging
import os
import time

import httpx

from packages.safety.fast_filters import redact_local_pii

logger = logging.getLogger("packages.safety.private_ai")


class PrivateAIClient:
    """Async wrapper for the Private AI API to support robust PII de-identification.

    Includes an automatic local fail-safe regex fallback if the external API key
    is missing or if the service is unreachable.
    """

    def __init__(self, api_key: str | None = None, server_endpoint: str | None = None):
        self.api_key = api_key or os.getenv("PRIVATE_AI_API_KEY")
        self.endpoint = (
            server_endpoint or os.getenv("PRIVATE_AI_ENDPOINT", "https://api.private-ai.com/v3")
        ).rstrip("/")

    async def deidentify_text(self, text: str, entity_types: list[str] | None = None) -> str:
        """Sends text to Private AI for PII masking/redaction with fallback logic."""
        if not text:
            return text

        if not self.api_key or self.api_key == "replace-me":
            logger.warning(
                "Private AI API key is missing or placeholder. Falling back to local regex masking."
            )
            return redact_local_pii(text)

        if entity_types is None:
            entity_types = ["NAME", "EMAIL_ADDRESS", "PHONE_NUMBER", "SSN", "CREDIT_CARD"]

        payload = {
            "text": [text],
            "entity_detection": {
                "accuracy": "high",
                "entity_types": [{"type": et} for et in entity_types],
            },
        }

        url = f"{self.endpoint}/deidentify"

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    processed_text = data.get("processed_text", [])
                    if processed_text:
                        latency = round((time.perf_counter() - start_time) * 1000, 2)
                        logger.info(f"Private AI PII de-identification succeeded in {latency}ms")
                        return processed_text[0]

                logger.error(
                    f"Private AI API error: Status {response.status_code} - {response.text}"
                )
        except Exception as e:
            logger.error(f"Failed to communicate with Private AI API: {e}", exc_info=True)

        # Fallback
        logger.warning("Private AI API check failed. Triggering local regex fallback.")
        return redact_local_pii(text)
