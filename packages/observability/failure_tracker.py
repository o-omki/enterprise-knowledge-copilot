import structlog
from opentelemetry import metrics

logger = structlog.get_logger(__name__)

meter = metrics.get_meter("enterprise-knowledge-copilot")

system_failure_total = meter.create_counter(
    name="system.failure.total",
    description="Total number of system failures",
    unit="{failures}",
)

system_timeout_total = meter.create_counter(
    name="system.timeout.total",
    description="Total number of operation timeouts",
    unit="{timeouts}",
)

system_retry_total = meter.create_counter(
    name="system.retry.total",
    description="Total number of operation retries",
    unit="{retries}",
)


def classify_exception(e: Exception) -> str:
    """Classifies an exception into a standard error type string."""
    name = type(e).__name__
    msg = str(e).lower()

    if "rate" in msg or "quota" in msg or "exhausted" in msg or "429" in msg:
        return "rate_limit_error"
    if (
        "auth" in msg
        or "permission" in msg
        or "unauthenticated" in msg
        or "key" in msg
        or "401" in msg
        or "403" in msg
    ):
        return "authentication_error"
    if "timeout" in msg or "deadline" in msg or "timed out" in msg:
        return "timeout_error"
    if "connection" in msg or "unreachable" in msg or "connect" in msg:
        return "connection_error"
    if "invalid" in msg or "bad request" in msg or "400" in msg:
        return "invalid_request_error"
    if "500" in msg or "internal server" in msg or "service unavailable" in msg or "503" in msg:
        return "internal_server_error"

    # Match by exact class names
    if name in ("ResourceExhausted", "RateLimitError"):
        return "rate_limit_error"
    if name in ("Unauthenticated", "PermissionDenied", "AuthenticationError"):
        return "authentication_error"
    if name in (
        "DeadlineExceeded",
        "APITimeoutError",
        "TimeoutError",
        "TimeoutException",
        "ConnectTimeout",
    ):
        return "timeout_error"
    if name in ("APIConnectionError", "ServiceUnavailable", "HTTPStatusError"):
        return "connection_error"
    if name in ("InvalidArgument", "BadRequestError"):
        return "invalid_request_error"
    if name in ("InternalServerError", "InternalError"):
        return "internal_server_error"

    return "unknown_error"


class FailureTracker:
    @classmethod
    def record_failure(cls, component: str, error_type: str, details: str):
        """Increments error counter and logs structured error event."""
        logger.error(
            "system.failure.occurred",
            component=component,
            error_type=error_type,
            details=details,
        )
        system_failure_total.add(1, {"component": component, "error_type": error_type})

    @classmethod
    def record_timeout(cls, component: str, operation: str, timeout_sec: float, elapsed_sec: float):
        """Increments timeout counter and logs structured warning event."""
        logger.warning(
            "system.timeout.occurred",
            component=component,
            operation=operation,
            timeout_sec=timeout_sec,
            elapsed_sec=elapsed_sec,
        )
        system_timeout_total.add(1, {"component": component, "operation": operation})

    @classmethod
    def record_retry(cls, component: str, operation: str, attempt: int, max_retries: int):
        """Increments retry counter and logs structured info event."""
        logger.info(
            "system.retry.attempted",
            component=component,
            operation=operation,
            attempt=attempt,
            max_retries=max_retries,
        )
        system_retry_total.add(
            1,
            {
                "component": component,
                "operation": operation,
                "attempt": str(attempt),
            },
        )
