import time

import structlog

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
            logger.info(
                "circuit_breaker.state_change", from_state=self.state, to_state="CLOSED", failures=0
            )
        self.failures = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.state == "CLOSED" and self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                "circuit_breaker.state_change",
                from_state="CLOSED",
                to_state="OPEN",
                failures=self.failures,
            )
        elif self.state == "HALF_OPEN":
            self.state = "OPEN"
            logger.warning(
                "circuit_breaker.state_change",
                from_state="HALF_OPEN",
                to_state="OPEN",
                failures=self.failures,
            )

    def check_state(self):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info(
                    "circuit_breaker.state_change",
                    from_state="OPEN",
                    to_state="HALF_OPEN",
                    elapsed=time.time() - self.last_failure_time,
                )
            else:
                raise CircuitBreakerOpenException("Circuit breaker is OPEN.")

    async def execute(self, func, *args, **kwargs):
        self.check_state()
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise e

    async def execute_stream(self, func, *args, **kwargs):
        self.check_state()
        try:
            stream = func(*args, **kwargs)
            async for item in stream:
                yield item
            self.record_success()
        except Exception as e:
            self.record_failure()
            raise e
