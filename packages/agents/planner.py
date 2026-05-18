from google import genai
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.observability import get_tracer

from .schema import DecompositionResult

tracer = get_tracer(__name__)


class DecomposerConfig(BaseSettings):
    project_id: str = Field(alias="GCP_PROJECT_ID")
    location: str = Field(alias="GCP_LOCATION", default="global")
    decomposition_model_name: str = Field(
        alias="GCP_DECOMPOSITION_MODEL", default="gemini-3-flash-preview"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class DecomposerAgent:
    def __init__(self, config: DecomposerConfig | None = None):
        self.config = config or DecomposerConfig()
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

    async def decompose(self, query: str) -> DecompositionResult:
        """Break down a complex or comparative query into atomic, standalone sub-queries."""
        with tracer.start_as_current_span("decompose_query") as span:
            span.set_attribute("query", query)
            span.set_attribute("model", self.config.decomposition_model_name)

            system_instruction = """
            You are an expert query planning agent for a RAG system.
            The user has provided a complex query requiring multiple hops, synthesis, or comparison.
            Your task is to decompose this query into a list of atomic, self-contained sub-queries 
            that can be independently executed against a standard search engine.

            Rules:
            1. Ensure each sub-query contains enough context to be searched independently. 
               For example, to compare "Company A's policy on X vs Company B's",
               create two sub-queries:
               "What is Company A's policy on X?" and "What is Company B's policy on X?".
            2. Limit to 2-4 sub-queries if possible to avoid excessive retrieval overhead.
            3. Do not formulate sub-queries that depend directly on the execution results 
               of previous ones (we fire these in parallel).
            """

            try:
                response = await self.genai_client.aio.models.generate_content(
                    model=self.config.decomposition_model_name,
                    contents=query,
                    config={
                        "system_instruction": system_instruction,
                        "response_mime_type": "application/json",
                        "response_schema": DecompositionResult,
                        "temperature": 0.1,
                    },
                )

                decision: DecompositionResult = response.parsed

                span.set_attribute("decomposition.count", len(decision.sub_queries))
                span.set_attribute("decomposition.sub_queries", decision.sub_queries)
                span.set_attribute("decomposition.reasoning", decision.reasoning)

                return decision

            except Exception as e:
                span.record_exception(e)
                decision = DecompositionResult(
                    sub_queries=[query], reasoning=f"Fallback due to decomposition error: {str(e)}"
                )
                span.set_attribute("decomposition.count", 1)
                return decision
