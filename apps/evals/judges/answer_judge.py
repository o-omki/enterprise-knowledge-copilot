"""LLM-as-judge for scoring generated answer quality.

Uses Vertex AI Gemini to evaluate generated answers against reference answers
on five quality dimensions: correctness, faithfulness, completeness,
citation quality, and conciseness.

Scores are returned on a 1-5 scale and normalized to 0.0-1.0.
"""

from __future__ import annotations

import logging

from google import genai
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from apps.evals.config import JudgeConfig

logger = logging.getLogger(__name__)


class JudgeScores(BaseModel):
    """Scores assigned by the LLM judge, each on a 1-5 scale."""

    correctness: int = Field(
        ...,
        ge=1,
        le=5,
        description=(
            "Does the answer match the reference answer's key facts? "
            "(1=completely wrong, 5=fully correct)"
        ),
    )
    faithfulness: int = Field(
        ...,
        ge=1,
        le=5,
        description=(
            "Is every claim in the answer supported by the provided context? "
            "(1=fabricated, 5=fully grounded)"
        ),
    )
    completeness: int = Field(
        ...,
        ge=1,
        le=5,
        description=(
            "Does the answer cover all important aspects from the reference? "
            "(1=missing all key points, 5=comprehensive)"
        ),
    )
    citation_quality: int = Field(
        ...,
        ge=1,
        le=5,
        description=(
            "Are citations accurate, relevant, and properly attributed? "
            "(1=no/wrong citations, 5=perfect attribution)"
        ),
    )
    conciseness: int = Field(
        ...,
        ge=1,
        le=5,
        description=(
            "Is the answer free of unnecessary repetition or filler? "
            "(1=extremely verbose, 5=optimally concise)"
        ),
    )
    reasoning: str = Field(
        ...,
        description=("Brief reasoning for the scores, highlighting key strengths and weaknesses."),
    )


class JudgeVerdict(BaseModel):
    """Normalized scores (0.0–1.0) and raw scores for a single QA evaluation."""

    correctness: float
    faithfulness: float
    completeness: float
    citation_quality: float
    conciseness: float
    reasoning: str
    raw_scores: dict[str, int]

    @property
    def average(self) -> float:
        """Weighted average of all dimensions."""
        return round(
            (
                self.correctness
                + self.faithfulness
                + self.completeness
                + self.citation_quality
                + self.conciseness
            )
            / 5.0,
            4,
        )


class AnswerJudgeGCPConfig(BaseSettings):
    """GCP credentials for the judge LLM (reuses existing env vars)."""

    project_id: str = Field(alias="GCP_PROJECT_ID")
    location: str = Field(alias="GCP_LOCATION", default="global")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


JUDGE_SYSTEM_PROMPT = """\
You are an expert evaluation judge for a Retrieval-Augmented Generation (RAG) system.

You will be given:
1. A user question
2. A reference (gold-standard) answer
3. A generated (candidate) answer produced by the system
4. The retrieved context passages used to generate the answer

Your task is to score the generated answer on five quality dimensions,
each on a scale from 1 (worst) to 5 (best).

Scoring guidelines:

**Correctness** (1-5): Does the generated answer contain the same key facts as the reference answer?
- 5 = All key facts match
- 3 = Some facts correct, some missing or wrong
- 1 = Completely incorrect

**Faithfulness** (1-5): Is every claim in the generated answer supported by the provided context?
- 5 = Every claim is directly supported by context
- 3 = Some claims lack support
- 1 = Contains fabricated information not in context

**Completeness** (1-5): Does the generated answer cover all important points from the reference?
- 5 = Covers everything important
- 3 = Covers about half
- 1 = Misses all important points

**Citation Quality** (1-5): Are source citations accurate and useful?
- 5 = All claims properly cited with correct sources
- 3 = Some citations present but incomplete
- 1 = No citations or all citations wrong

**Conciseness** (1-5): Is the answer appropriately concise?
- 5 = Optimal length, no filler
- 3 = Somewhat verbose but acceptable
- 1 = Extremely verbose with excessive repetition

Provide brief reasoning explaining the scores.
Be strict but fair. A score of 3 means acceptable/average quality.
"""


class AnswerJudge:
    """Scores generated answers against reference answers using Vertex AI Gemini."""

    def __init__(self, judge_config: JudgeConfig | None = None) -> None:
        self.judge_config = judge_config or JudgeConfig()
        self._gcp_config = AnswerJudgeGCPConfig()
        self._genai_client = None

    @property
    def genai_client(self):
        """Lazy-load the Gemini client."""
        if self._genai_client is None:
            self._genai_client = genai.Client(
                vertexai=True,
                project=self._gcp_config.project_id,
                location=self._gcp_config.location,
            )
        return self._genai_client

    async def judge(
        self,
        question: str,
        reference_answer: str,
        generated_answer: str,
        citations: list[dict] | None = None,
        context: list[str] | None = None,
    ) -> JudgeVerdict:
        """Score a single generated answer against the reference.

        Parameters
        ----------
        question:
            The original user question.
        reference_answer:
            The gold-standard reference answer.
        generated_answer:
            The answer produced by the RAG system.
        citations:
            List of citation dicts from the generation response.
        context:
            The retrieved context passages used for generation.

        Returns
        -------
        JudgeVerdict with normalized scores (0.0-1.0).
        """
        citations_str = ""
        if citations:
            citation_parts = []
            for c in citations:
                src = c.get("source", "unknown")
                snippet = c.get("snippet", "")
                citation_parts.append(f"[{c.get('id', '?')}] {src}: {snippet[:200]}")
            citations_str = "\n".join(citation_parts)
        else:
            citations_str = "(No citations provided)"

        context_str = ""
        if context:
            context_str = "\n\n---\n\n".join(
                f"[Passage {i + 1}]\n{passage}" for i, passage in enumerate(context)
            )
        else:
            context_str = "(No context provided)"

        user_prompt = f"""\
**Question:**
{question}

**Reference Answer:**
{reference_answer}

**Generated Answer:**
{generated_answer}

**Citations in Generated Answer:**
{citations_str}

**Retrieved Context Passages:**
{context_str}
"""

        try:
            response = await self.genai_client.aio.models.generate_content(
                model=self.judge_config.model,
                contents=user_prompt,
                config={
                    "system_instruction": JUDGE_SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_schema": JudgeScores,
                    "temperature": self.judge_config.temperature,
                    "max_output_tokens": self.judge_config.max_output_tokens,
                },
            )

            scores: JudgeScores | None = response.parsed

            # Fallback: if structured parsing returned None, try manual JSON parse
            if scores is None:
                import json as _json
                import re

                text = response.text or ""
                clean_text = re.sub(r"^```(?:json)?\n|\n```$", "", text.strip(), flags=re.MULTILINE)

                try:
                    if clean_text:
                        raw = _json.loads(clean_text)
                        scores = JudgeScores(**raw)
                    else:
                        raise ValueError("Empty response text")
                except Exception:
                    finish_reason = "UNKNOWN"
                    if response.candidates and len(response.candidates) > 0:
                        finish_reason = getattr(response.candidates[0], "finish_reason", "UNKNOWN")

                    logger.warning(
                        "Answer judge: manual parse failed. Finish reason: %s. Response text: %s",
                        finish_reason,
                        text[:200],
                    )
                    return JudgeVerdict(
                        correctness=0.0,
                        faithfulness=0.0,
                        completeness=0.0,
                        citation_quality=0.0,
                        conciseness=0.0,
                        reasoning=(
                            "Answer judge error: unparseable response "
                            "(Finish Reason: {finish_reason})."
                        ),
                        raw_scores={
                            "correctness": 1,
                            "faithfulness": 1,
                            "completeness": 1,
                            "citation_quality": 1,
                            "conciseness": 1,
                        },
                    )

            return JudgeVerdict(
                correctness=round((scores.correctness - 1) / 4.0, 4),
                faithfulness=round((scores.faithfulness - 1) / 4.0, 4),
                completeness=round((scores.completeness - 1) / 4.0, 4),
                citation_quality=round((scores.citation_quality - 1) / 4.0, 4),
                conciseness=round((scores.conciseness - 1) / 4.0, 4),
                reasoning=scores.reasoning,
                raw_scores={
                    "correctness": scores.correctness,
                    "faithfulness": scores.faithfulness,
                    "completeness": scores.completeness,
                    "citation_quality": scores.citation_quality,
                    "conciseness": scores.conciseness,
                },
            )

        except Exception as e:
            logger.error("Judge evaluation failed: %s", e)
            # Return a pessimistic default rather than crashing the whole eval
            return JudgeVerdict(
                correctness=0.0,
                faithfulness=0.0,
                completeness=0.0,
                citation_quality=0.0,
                conciseness=0.0,
                reasoning=f"Judge error: {e}",
                raw_scores={
                    "correctness": 1,
                    "faithfulness": 1,
                    "completeness": 1,
                    "citation_quality": 1,
                    "conciseness": 1,
                },
            )
