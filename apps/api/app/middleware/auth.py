import hashlib
import os

import jwt
import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from packages.shared.database import async_session_maker
from packages.shared.orm_models import ApiKey, User

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

if JWT_SECRET_KEY is None:
    raise ValueError("[ENCRYPTION ERROR] - JWT_SECRET_KEY is not set.")

if JWT_ALGORITHM is None:
    raise ValueError("[ENCRYPTION ERROR] - JWT_ALGORITHM is not set.")

logger = structlog.get_logger(__name__)


class MultiAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that verifies either a JWT Bearer token or an X-API-Key header.

    Bypasses authentication for health checks, docs, and auth endpoints.
    """

    def __init__(self, app):
        super().__init__(app)
        self.bypass_paths = {
            "/health",
            "/api/v1/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/metrics",
            "/metrics/",
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Bypass auth for diagnostic/doc paths and preflight CORS requests
        if path in self.bypass_paths or request.method == "OPTIONS":
            return await call_next(request)

        request.state.user_id = None
        request.state.api_key_id = None

        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")

        if not auth_header and not api_key_header:
            logger.warning("auth.missing", path=path)
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Missing authentication credentials",
                    "error_code": "UNAUTHORIZED",
                },
            )

        async with async_session_maker() as db:
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                    user_id: str = payload.get("sub")
                    if user_id is None:
                        raise ValueError("Invalid token payload")

                    query = select(User).where(User.id == user_id)
                    result = await db.execute(query)
                    user = result.scalar_one_or_none()
                    if not user:
                        raise ValueError("User not found")

                    request.state.user_id = user.id
                    logger.info("auth.authenticated", auth_type="jwt", user_id=user.id, path=path)
                except Exception as e:
                    logger.warning("auth.rejected", auth_type="jwt", error=str(e), path=path)
                    return JSONResponse(
                        status_code=401,
                        content={
                            "detail": "Invalid or expired JWT token",
                            "error_code": "UNAUTHORIZED",
                        },
                    )

            elif api_key_header:
                key_hash = hashlib.sha256(api_key_header.encode("utf-8")).hexdigest()
                try:
                    query = select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active)
                    result = await db.execute(query)
                    api_key_record = result.scalar_one_or_none()

                    if not api_key_record:
                        logger.warning(
                            "auth.rejected", auth_type="api_key", reason="invalid_key", path=path
                        )
                        return JSONResponse(
                            status_code=401,
                            content={"detail": "Invalid API key", "error_code": "UNAUTHORIZED"},
                        )

                    request.state.api_key_id = api_key_record.id
                    logger.info(
                        "auth.authenticated",
                        auth_type="api_key",
                        api_key_id=api_key_record.id,
                        path=path,
                    )
                except Exception as e:
                    logger.error("auth.error", auth_type="api_key", error=str(e), exc_info=True)
                    return JSONResponse(
                        status_code=500,
                        content={
                            "detail": "Internal server error during authentication",
                            "error_code": "INTERNAL_SERVER_ERROR",
                        },
                    )

        return await call_next(request)
