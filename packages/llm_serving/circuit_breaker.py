import asyncio
import time

import structlog
from opentelemetry import trace

logger = structlog.get_logger(__name__)


class CircuitBreakerOpenException(Exception):
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = 0.0

    def record_success(self):
        if self.state in ("OPEN", "HALF_OPEN"):
            from_state = self.state
            self.state = "CLOSED"
            self.failures = 0
            logger.info(
                "circuit_breaker.state_change", from_state=from_state, to_state="CLOSED", failures=0
            )
            span = trace.get_current_span()
            if span and span.is_recording():
                span.add_event(
                    "circuit_breaker.state_change",
                    attributes={"from_state": from_state, "to_state": "CLOSED", "failures": 0},
                )
        else:
            self.failures = 0
            self.state = "CLOSED"

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        from_state = self.state
        if self.state == "CLOSED" and self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                "circuit_breaker.state_change",
                from_state=from_state,
                to_state="OPEN",
                failures=self.failures,
            )
            span = trace.get_current_span()
            if span and span.is_recording():
                span.add_event(
                    "circuit_breaker.state_change",
                    attributes={
                        "from_state": from_state,
                        "to_state": "OPEN",
                        "failures": self.failures,
                    },
                )
        elif self.state == "HALF_OPEN":
            self.state = "OPEN"
            logger.warning(
                "circuit_breaker.state_change",
                from_state=from_state,
                to_state="OPEN",
                failures=self.failures,
            )
            span = trace.get_current_span()
            if span and span.is_recording():
                span.add_event(
                    "circuit_breaker.state_change",
                    attributes={
                        "from_state": from_state,
                        "to_state": "OPEN",
                        "failures": self.failures,
                    },
                )

    def check_state(self):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                from_state = self.state
                self.state = "HALF_OPEN"
                logger.info(
                    "circuit_breaker.state_change",
                    from_state=from_state,
                    to_state="HALF_OPEN",
                    elapsed=time.time() - self.last_failure_time,
                )
                span = trace.get_current_span()
                if span and span.is_recording():
                    span.add_event(
                        "circuit_breaker.state_change",
                        attributes={
                            "from_state": from_state,
                            "to_state": "HALF_OPEN",
                            "elapsed_sec": time.time() - self.last_failure_time,
                        },
                    )
            else:
                raise CircuitBreakerOpenException("Circuit breaker is OPEN.")

    async def execute(self, func, *args, **kwargs):
        self.check_state()
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            self.record_failure()

            from packages.observability.failure_tracker import FailureTracker, classify_exception

            is_timeout = (
                isinstance(e, asyncio.TimeoutError | TimeoutError)
                or "timeout" in type(e).__name__.lower()
                or "timeout" in str(e).lower()
            )
            if is_timeout:
                FailureTracker.record_timeout(
                    component="circuit_breaker",
                    operation=func.__name__,
                    timeout_sec=0.0,
                    elapsed_sec=elapsed,
                )
            else:
                FailureTracker.record_failure(
                    component="circuit_breaker",
                    error_type=classify_exception(e),
                    details=str(e),
                )
            raise e

    async def execute_stream(self, func, *args, **kwargs):
        self.check_state()
        start_time = time.perf_counter()
        try:
            stream = func(*args, **kwargs)
            async for item in stream:
                yield item
            self.record_success()
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            self.record_failure()

            from packages.observability.failure_tracker import FailureTracker, classify_exception

            is_timeout = (
                isinstance(e, asyncio.TimeoutError | TimeoutError)
                or "timeout" in type(e).__name__.lower()
                or "timeout" in str(e).lower()
            )
            if is_timeout:
                FailureTracker.record_timeout(
                    component="circuit_breaker",
                    operation=func.__name__,
                    timeout_sec=0.0,
                    elapsed_sec=elapsed,
                )
            else:
                FailureTracker.record_failure(
                    component="circuit_breaker",
                    error_type=classify_exception(e),
                    details=str(e),
                )
            raise e
