from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.llm_serving import LLMClient, LLMMessage, LLMRequest
from packages.observability import get_tracer

from .schema import RoutingDecision

tracer = get_tracer(__name__)


class RouterConfig(BaseSettings):
    routing_model_name: str = Field(alias="GCP_ROUTING_MODEL", default="gemini-3.1-flash-lite")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class QueryRouter:
    def __init__(self, llm_client: LLMClient, config: RouterConfig | None = None):
        self.config = config or RouterConfig()
        self.llm_client = llm_client

    async def route(self, query: str) -> RoutingDecision:
        """Route the query to one of the defined QueryType categories."""
        with tracer.start_as_current_span("route_query") as span:
            span.set_attribute("query", query)
            prompt = """
            You are an intelligent query router for an enterprise knowledge assistant.
            Categorize the user query into exactly one of these buckets:
            - direct_lookup: A straightforward factual query requiring typical evidence retrieval.
            - ambiguous_query: A vague or under-specified query where the user intent is not clear.
            - multi_hop_synthesis: A complex query requiring multiple distinct retrieval
              steps to answer.
            - comparative_query: A query explicitly comparing two or more entities or concepts.
            """

            try:
                req = LLMRequest(
                    messages=[LLMMessage(role="user", content=query)],
                    model=self.config.routing_model_name,
                    temperature=0.1,
                    system_instruction=prompt,
                    response_mime_type="application/json",
                    response_schema=RoutingDecision,
                )
                response = await self.llm_client.generate(req)

                decision: RoutingDecision = response.parsed

                span.set_attribute("routing.result", decision.query_type)
                span.set_attribute("routing.reasoning", decision.reasoning)
                return decision

            except Exception as e:
                span.record_exception(e)
                decision = RoutingDecision(
                    query_type="direct_lookup",
                    reasoning=f"Fallback triggered due to routing execution error: {str(e)}",
                )
                span.set_attribute("routing.result", decision.query_type)
                return decision
