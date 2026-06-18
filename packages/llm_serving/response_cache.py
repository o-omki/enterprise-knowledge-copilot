import hashlib
import json

import redis.asyncio as redis

from packages.llm_serving.config import LLMServingConfig
from packages.llm_serving.types import LLMRequest, LLMResponse, UsageMetadata


class ResponseCache:
    def __init__(self, config: LLMServingConfig, redis_client: redis.Redis | None = None):
        self.config = config
        self.redis = redis_client

    def _generate_key(self, request: LLMRequest) -> str:
        data = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "system": request.system_instruction,
        }
        json_str = json.dumps(data, sort_keys=True)
        return "llm_cache:" + hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    async def get(self, request: LLMRequest) -> LLMResponse | None:
        if not self.config.cache_enabled or not self.redis:
            return None
        key = self._generate_key(request)
        cached = await self.redis.get(key)
        if cached:
            data = json.loads(cached)
            return LLMResponse(
                text=data.get("text", ""),
                usage=UsageMetadata(**data.get("usage", {})),
                parsed=data.get("parsed"),
            )
        return None

    async def set(self, request: LLMRequest, response: LLMResponse):
        if not self.config.cache_enabled or not self.redis:
            return
        key = self._generate_key(request)
        data = {
            "text": response.text,
            "usage": response.usage.model_dump(),
            "parsed": response.parsed,
        }
        await self.redis.set(key, json.dumps(data), ex=self.config.cache_ttl_sec)
