import logging

from google import genai
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.rag.search import SearchResult

logger = logging.getLogger(__name__)


class GenerationConfig(BaseSettings):
    project_id: str = Field(alias="GCP_PROJECT_ID")
    location: str = Field(alias="GCP_LOCATION", default="global")
    generation_model_name: str = Field(
        alias="GCP_GENERATION_MODEL", default="gemini-3.1-pro-preview"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class Citation(BaseModel):
    id: int
    source: str
    snippet: str


class AnswerResponse(BaseModel):
    answer: str
    citations: list[Citation]
    context_passages: list[str] = Field(default_factory=list)


class GenerationService:
    def __init__(self, config: GenerationConfig | None = None):
        self.config = config or GenerationConfig()
        self._genai_client = None

    @property
    def genai_client(self):
        """Lazy loader for the genai client."""
        if self._genai_client is None:
            self._genai_client = genai.Client(
                vertexai=True,
                project=self.config.project_id,
                location=self.config.location,
            )
        return self._genai_client

    async def generate_answer(
        self, query: str, search_results: list[SearchResult]
    ) -> AnswerResponse:
        """Generates an answer from search context and formats the citations."""
        if not search_results:
            return AnswerResponse(
                answer=(
                    "I could not find any relevant information in the"
                    "knowledge base to answer your question."
                ),
                citations=[],
            )

        context_parts = []
        citations_meta = []
        for idx, result in enumerate(search_results, start=1):
            context_parts.append(f"[Source {idx}] File: {result.source}\nContent:\n{result.text}\n")

            snippet = (
                result.text[:200].strip() + "..." if len(result.text) > 200 else result.text.strip()
            )

            citations_meta.append(Citation(id=idx, source=result.source, snippet=snippet))

        context_str = "\n".join(context_parts)

        system_instruction = """\
You are an enterprise knowledge assistant. You answer questions based \
STRICTLY on the provided source documents.

HARD RULES — violating any of these is a critical failure:
1. ONLY use information that is explicitly stated in the Context below.
2. NEVER add facts, explanations, examples, or details from your own knowledge, \
even if you know them to be correct.
3. EVERY factual sentence in your answer MUST end with an inline citation [N] \
referencing the source it came from. Multiple sources may be cited as [1][3].
4. If the Context does not contain enough information to answer the question, \
respond EXACTLY with: "I don't have enough information in the knowledge base \
to answer this question."
5. Stay close to the source wording. Do not heavily paraphrase or embellish.
6. Do NOT start your answer with "Based on the provided context" or similar \
meta-commentary. Answer the question directly.

CITATION FORMAT:
- Use [N] at the end of each sentence, where N is the Source number.
- Example: "FastAPI supports background tasks for long-running operations [1]. \
You can declare them as function parameters [2]."
"""

        user_prompt = f"""\
Context:
{context_str}

Question:
{query}

Answer:
"""

        try:
            response = await self.genai_client.aio.models.generate_content(
                model=self.config.generation_model_name,
                contents=user_prompt,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.2,
                    "max_output_tokens": 2048,
                },
            )

        except Exception as e:
            logger.exception(f"Failed to generate answer for query: {query}")

            raise RuntimeError(f"Generation failed: {e}") from e

        else:
            try:
                answer_text = (
                    response.text
                    or "I cannot answer this question due to safety policy restrictions."
                )
            except Exception:
                answer_text = "I cannot answer this question due to safety policy restrictions."

            return AnswerResponse(
                answer=answer_text,
                citations=citations_meta,
                context_passages=[r.text for r in search_results],
            )
