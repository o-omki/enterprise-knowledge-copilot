import logging
import time

logger = logging.getLogger(__name__)


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
            logger.info("Circuit breaker RECOVERED to CLOSED state.")
        self.failures = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.state == "CLOSED" and self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning("Circuit breaker OPENED after %d failures.", self.failures)
        elif self.state == "HALF_OPEN":
            self.state = "OPEN"
            logger.warning("Circuit breaker re-OPENED in HALF_OPEN state.")

    def check_state(self):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioned to HALF_OPEN state.")
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
