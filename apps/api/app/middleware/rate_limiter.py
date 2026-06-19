import os
import time
import uuid
from collections.abc import Awaitable
from typing import cast

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Middleware that implements Redis-based sliding window rate limiting.

    Provides headers X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset.
    Returns 429 Too Many Requests when rate limits are exceeded.
    """

    def __init__(self, app):
        super().__init__(app)
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = Redis.from_url(redis_url, decode_responses=True)

        self.limits = {
            "/ask": int(os.getenv("RATE_LIMIT_ASK", "60")),
            "/api/v1/ask": int(os.getenv("RATE_LIMIT_ASK", "60")),
            "/search": int(os.getenv("RATE_LIMIT_SEARCH", "60")),
            "/api/v1/search": int(os.getenv("RATE_LIMIT_SEARCH", "60")),
            "/upload": int(os.getenv("RATE_LIMIT_UPLOAD", "10")),
            "/api/v1/upload": int(os.getenv("RATE_LIMIT_UPLOAD", "10")),
            "default": int(os.getenv("RATE_LIMIT_DEFAULT", "120")),
        }
        self.window_seconds = 60
        self.bypass_paths = {
            "/health",
            "/api/v1/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in self.bypass_paths:
            return await call_next(request)

        # Get rate limiting key identifier (prefer authenticated API Key ID, fallback to client IP)
        api_key_id = getattr(request.state, "api_key_id", None)
        if api_key_id:
            client_id = f"key:{api_key_id}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            client_id = f"ip:{client_ip}"

        # Resolve request limit based on endpoint path
        limit = self.limits.get(path, self.limits["default"])
        redis_key = f"rate_limit:{client_id}:{path}"
        now = time.time()

        try:
            # Atomic transaction using pipeline
            pipeline = self.redis.pipeline()
            pipeline.zremrangebyscore(redis_key, 0, now - self.window_seconds)
            pipeline.zadd(redis_key, {str(uuid.uuid4()): now})
            pipeline.zcard(redis_key)
            pipeline.expire(redis_key, self.window_seconds)

            # Execute pipeline and retrieve counts
            results = await cast(Awaitable[list], pipeline.execute())
            request_count = results[2]  # Result of zcard
            remaining = max(0, limit - request_count)
            reset_time = int(now + self.window_seconds)

            if request_count > limit:
                # Calculate precise Retry-After from the oldest timestamp in current window
                oldest_elements = await cast(
                    Awaitable[list], self.redis.zrange(redis_key, 0, 0, withscores=True)
                )
                if oldest_elements:
                    _, oldest_timestamp = oldest_elements[0]
                    retry_after = max(1, int(oldest_timestamp + self.window_seconds - now))
                else:
                    retry_after = 1

                logger.warning(
                    "rate_limiter.throttled",
                    key=client_id,
                    path=path,
                    limit=limit,
                    remaining=0,
                )
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                    content={
                        "detail": "Too many requests. Please try again later.",
                        "error_code": "TOO_MANY_REQUESTS",
                    },
                )

            logger.info(
                "rate_limiter.allowed",
                key=client_id,
                path=path,
                limit=limit,
                remaining=remaining,
            )
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            return response

        except RedisError as e:
            # Graceful degradation - fail-open if Redis is down
            logger.error("rate_limiter.redis_error", error=str(e), exc_info=True)
            return await call_next(request)
