from enum import StrEnum

from pydantic import BaseModel, Field


class QueryType(StrEnum):
    DIRECT_LOOKUP = "direct_lookup"
    AMBIGUOUS_QUERY = "ambiguous_query"
    MULTI_HOP_SYNTHESIS = "multi_hop_synthesis"
    COMPARATIVE_QUERY = "comparative_query"


class RoutingDecision(BaseModel):
    query_type: QueryType = Field(description="The categorization of the query.")
    reasoning: str = Field(description="Explanation of why this query type was selected.")


class DecompositionResult(BaseModel):
    sub_queries: list[str] = Field(
        description="A list of distinct, standalone sub-queries required to answer the main query."
    )
    reasoning: str = Field(
        description="Explanation of why these specific sub-queries were created."
    )
