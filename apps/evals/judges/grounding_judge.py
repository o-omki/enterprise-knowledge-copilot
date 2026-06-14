"""Grounding / faithfulness judge.

Focuses exclusively on whether each claim in a generated answer is supported
by the retrieved context. Identifies individual claims and classifies them
as supported, unsupported, or contradicted.

This is a targeted complement to the broader :class:`AnswerJudge` — use it
when you need fine-grained hallucination analysis rather than aggregate scores.
"""

from __future__ import annotations

import logging

from google import genai
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from apps.evals.config import JudgeConfig

logger = logging.getLogger(__name__)


class ClaimVerification(BaseModel):
    claim: str = Field(..., description="A single factual claim extracted from the answer.")
    status: str = Field(
        ...,
        description="One of: 'supported', 'unsupported', 'contradicted'.",
    )
    evidence: str = Field(
        default="",
        description="The context passage snippet that supports or contradicts this claim, if any.",
    )


class GroundingResult(BaseModel):
    claims: list[ClaimVerification] = Field(
        default_factory=list,
        description="List of individual claims and their verification status.",
    )
    reasoning: str = Field(
        default="",
        description="Brief summary of the grounding analysis.",
    )


class GroundingVerdict(BaseModel):
    """Aggregated grounding scores for a single answer."""

    grounding_score: float = Field(
        ...,
        description="Fraction of claims that are supported (0.0-1.0).",
    )
    total_claims: int
    supported: int
    unsupported: int
    contradicted: int
    flagged_claims: list[dict]
    reasoning: str


class GroundingJudgeGCPConfig(BaseSettings):
    project_id: str = Field(alias="GCP_PROJECT_ID")
    location: str = Field(alias="GCP_LOCATION", default="global")
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


GROUNDING_SYSTEM_PROMPT = """\
You are a fact-checking judge for a Retrieval-Augmented Generation (RAG) system.

You will receive:
1. A generated answer
2. Context passages that were used to generate the answer

Your task:
1. Extract every distinct factual claim from the generated answer.
2. For each claim, determine if it is:
   - "supported": The claim is directly stated or clearly implied by the context passages.
   - "unsupported": The claim cannot be verified from the
        context passages (hallucinated or external knowledge).
   - "contradicted": The context passages state the opposite of this claim.
3. For supported/contradicted claims, cite the relevant evidence snippet.

Be thorough — extract ALL factual claims, including implicit ones.
Simple grammatical connectors or opinion phrases are not claims.
"""


class GroundingJudge:
    """Performs claim-level grounding analysis on generated answers."""

    def __init__(self, judge_config: JudgeConfig | None = None) -> None:
        self.judge_config = judge_config or JudgeConfig()
        self._gcp_config = GroundingJudgeGCPConfig()
        self._genai_client = None

    @property
    def genai_client(self):
        if self._genai_client is None:
            self._genai_client = genai.Client(
                vertexai=True,
                project=self._gcp_config.project_id,
                location=self._gcp_config.location,
            )
        return self._genai_client

    async def check_grounding(
        self,
        generated_answer: str,
        context: list[str],
    ) -> GroundingVerdict:
        """Analyze grounding of each claim in the generated answer.

        Parameters
        ----------
        generated_answer:
            The answer produced by the RAG system.
        context:
            The retrieved context passages.

        Returns
        -------
        GroundingVerdict with per-claim analysis and aggregate score.
        """
        context_str = "\n\n---\n\n".join(
            f"[Passage {i + 1}]\n{passage}" for i, passage in enumerate(context)
        )

        user_prompt = f"""\
**Generated Answer:**
{generated_answer}

**Context Passages:**
{context_str}
"""

        try:
            response = await self.genai_client.aio.models.generate_content(
                model=self.judge_config.model,
                contents=user_prompt,
                config={
                    "system_instruction": GROUNDING_SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_schema": GroundingResult,
                    "temperature": self.judge_config.temperature,
                    "max_output_tokens": self.judge_config.max_output_tokens,
                },
            )

            result: GroundingResult | None = response.parsed

            # Fallback: if structured parsing returned None, try manual JSON parse
            if result is None:
                import json as _json
                import re

                text = response.text or ""
                # Strip markdown code blocks if present
                clean_text = re.sub(r"^```(?:json)?\n|\n```$", "", text.strip(), flags=re.MULTILINE)

                try:
                    if clean_text:
                        raw = _json.loads(clean_text)
                        result = GroundingResult(**raw)
                    else:
                        raise ValueError("Empty response text")
                except Exception:
                    # Check if it was blocked by safety
                    finish_reason = "UNKNOWN"
                    if response.candidates and len(response.candidates) > 0:
                        finish_reason = getattr(response.candidates[0], "finish_reason", "UNKNOWN")

                    logger.warning(
                        "Grounding judge: manual parse failed. Fail reason: %s. Response text: %s",
                        finish_reason,
                        text[:200],
                    )
                    return GroundingVerdict(
                        grounding_score=0.0,
                        total_claims=0,
                        supported=0,
                        unsupported=0,
                        contradicted=0,
                        flagged_claims=[],
                        reasoning=(
                            f"Grounding judge: model returned unparseable response "
                            f"(Finish Reason: {finish_reason})."
                        ),
                    )

            supported = sum(1 for c in result.claims if c.status == "supported")
            unsupported = sum(1 for c in result.claims if c.status == "unsupported")
            contradicted = sum(1 for c in result.claims if c.status == "contradicted")
            total = len(result.claims)

            flagged = [
                {"claim": c.claim, "status": c.status, "evidence": c.evidence}
                for c in result.claims
                if c.status != "supported"
            ]

            return GroundingVerdict(
                grounding_score=round(supported / total, 4) if total else 1.0,
                total_claims=total,
                supported=supported,
                unsupported=unsupported,
                contradicted=contradicted,
                flagged_claims=flagged,
                reasoning=result.reasoning,
            )

        except Exception as e:
            logger.error("Grounding check failed: %s", e)
            return GroundingVerdict(
                grounding_score=0.0,
                total_claims=0,
                supported=0,
                unsupported=0,
                contradicted=0,
                flagged_claims=[],
                reasoning=f"Grounding judge error: {e}",
            )
