import json
import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from packages.observability.metrics import active_requests, request_total

logger = structlog.get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that injects request correlation IDs and tracks latency.

    Extracts/generates `request_id` and parses `session_id` from query payload,
    binding them to the structlog contextvars for downstream logging.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        session_id = "none"
        path = request.url.path
        method = request.method

        # If it's a POST request to ask endpoint, parse session_id from body
        if method == "POST" and path in ("/api/v1/ask", "/ask"):
            body_bytes = await request.body()
            if body_bytes:
                try:
                    body_json = json.loads(body_bytes.decode("utf-8"))
                    session_id = body_json.get("session_id") or "none"
                except json.JSONDecodeError:
                    pass

                async def receive():
                    return {"type": "http.request", "body": body_bytes, "more_body": False}

                request._receive = receive

        request.state.session_id = session_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id, session_id=session_id, path=path, method=method
        )

        active_requests.add(1)
        start_time = time.perf_counter()
        logger.info("request.started")

        try:
            response = await call_next(request)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(
                "request.completed", status_code=response.status_code, latency_ms=latency_ms
            )
            request_total.add(
                1, {"endpoint": path, "method": method, "status": str(response.status_code)}
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error("request.failed", error=str(e), latency_ms=latency_ms, exc_info=True)
            request_total.add(1, {"endpoint": path, "method": method, "status": "500"})
            raise e
        finally:
            active_requests.add(-1)
            structlog.contextvars.clear_contextvars()
