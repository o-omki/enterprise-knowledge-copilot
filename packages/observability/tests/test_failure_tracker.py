import httpx
import pytest

from packages.observability.failure_tracker import FailureTracker, classify_exception


def test_classify_exception():
    # Rate limit classification
    assert classify_exception(Exception("rate limit exceeded")) == "rate_limit_error"
    assert classify_exception(Exception("QuotaExhausted")) == "rate_limit_error"
    assert classify_exception(Exception("resource exhausted")) == "rate_limit_error"

    # Authentication classification
    assert classify_exception(Exception("unauthorized access")) == "authentication_error"
    assert classify_exception(Exception("invalid API key")) == "authentication_error"
    assert classify_exception(Exception("permission denied")) == "authentication_error"

    # Timeout classification
    assert classify_exception(TimeoutError("timed out")) == "timeout_error"
    assert classify_exception(Exception("deadline exceeded")) == "timeout_error"
    assert classify_exception(httpx.TimeoutException("httpx timeout")) == "timeout_error"

    # Connection classification
    assert classify_exception(ConnectionError("cannot connect to server")) == "connection_error"
    assert classify_exception(httpx.ConnectError("host unreachable")) == "connection_error"

    # Invalid request classification
    assert classify_exception(ValueError("invalid arguments")) == "invalid_request_error"
    assert classify_exception(Exception("bad request parameters")) == "invalid_request_error"

    # Internal server classification
    assert classify_exception(Exception("500 Internal Server Error")) == "internal_server_error"
    assert classify_exception(Exception("service unavailable")) == "internal_server_error"

    # Unknown fallback classification
    assert classify_exception(Exception("something completely random")) == "unknown_error"


def test_failure_tracker_recordings():
    # Calling record methods should execute without raising any exceptions
    try:
        FailureTracker.record_failure(
            component="test_component", error_type="test_error", details="some test details"
        )
        FailureTracker.record_timeout(
            component="test_component", operation="test_operation", timeout_sec=5.0, elapsed_sec=6.2
        )
        FailureTracker.record_retry(
            component="test_component", operation="test_operation", attempt=2, max_retries=3
        )
    except Exception as e:
        pytest.fail(f"FailureTracker record methods raised an exception: {e}")
