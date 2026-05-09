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

        prompt = f"""
            You are an expert enterprise knowledge assistant.

            Answer the user's question using ONLY the provided context.
            If the answer is not present in the context, say you do not know.

            When information from a source is used, include inline citations
            using the source number in brackets.

            Example:
            'FastAPI supports background tasks [1].'

            Context:
            {context_str}

            Question:
            {query}

            Answer:
            """.strip()

        try:
            response = await self.genai_client.aio.models.generate_content(
                model=self.config.generation_model_name,
                contents=prompt,
            )

        except Exception as e:
            logger.exception(f"Failed to generate answer for query: {query}")

            raise RuntimeError(f"Generation failed: {e}") from e

        else:
            return AnswerResponse(answer=response.text, citations=citations_meta)
