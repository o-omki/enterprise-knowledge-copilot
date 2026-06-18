from enum import StrEnum

from pydantic import BaseModel, Field


class SLOPriority(StrEnum):
    LATENCY = "latency"
    COST = "cost"
    QUALITY = "quality"


class SLOConfig(BaseModel):
    max_latency_sec: float | None = Field(default=None)
    max_cost_usd: float | None = Field(default=None)
    priority: SLOPriority = Field(default=SLOPriority.QUALITY)
