from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMServingConfig(BaseSettings):
    default_backend: Literal["vertex_ai", "openai"] = Field(
        alias="LLM_DEFAULT_BACKEND", default="vertex_ai"
    )

    project_id: str = Field(alias="GCP_PROJECT_ID", default="")
    location: str = Field(alias="GCP_LOCATION", default="global")

    openai_api_key: str = Field(alias="OPENAI_API_KEY", default="")
    openai_base_url: str | None = Field(alias="OPENAI_BASE_URL", default=None)

    circuit_breaker_failure_threshold: int = Field(default=5)
    circuit_breaker_recovery_timeout_sec: int = Field(default=60)

    cache_ttl_sec: int = Field(default=3600)
    cache_enabled: bool = Field(default=True)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
