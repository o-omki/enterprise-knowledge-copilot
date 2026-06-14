import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app
from packages.shared.orm_models import ApiKey

# Reset the middleware stack to force FastAPI to rebuild it.
# This prevents cached bound mock methods from test_api.py from leaking.
app.middleware_stack = None

# Use raise_server_exceptions=True to bubble up errors during debug
client = TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def reset_middleware_stack():
    """
    Forces FastAPI to rebuild the middleware stack to clear cached mocks from other test files.
    """

    app.middleware_stack = None
    yield
    app.middleware_stack = None


@pytest.fixture(autouse=True)
def mock_db_session():
    """Fixture to mock database session and query results."""
    with patch("apps.api.app.middleware.auth.async_session_maker") as mock_maker:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_session.execute.return_value = mock_result
        mock_maker.return_value.__aenter__.return_value = mock_session
        yield mock_result


@pytest.fixture(autouse=True)
def mock_redis_global():
    """Autouse fixture to mock Redis client globally for all tests in this file."""
    with patch("apps.api.app.middleware.rate_limiter.Redis") as mock_redis_cls:
        mock_client = AsyncMock()
        mock_redis_cls.from_url.return_value = mock_client

        # Mock pipeline as a synchronous MagicMock
        mock_pipeline = MagicMock()
        mock_client.pipeline = MagicMock(return_value=mock_pipeline)

        # Only execute is async
        mock_pipeline.execute = AsyncMock(return_value=[0, 1, 1, True])

        yield mock_client


def test_auth_bypass_paths():
    """Verify that doc and health endpoints bypass auth completely."""
    # Bypassed endpoints should return 200 without requiring X-API-Key
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_missing_key():
    """Verify requests fail if the X-API-Key header is missing."""
    response = client.post("/api/v1/search", json={"query": "test"})
    assert response.status_code == 401
    assert response.json() == {
        "detail": "Missing authentication credentials",
        "error_code": "UNAUTHORIZED",
    }


def test_auth_invalid_key(mock_db_session):
    """Verify requests fail if the API key is not in the database."""
    # Mock database to return None (invalid/not found key)
    mock_db_session.scalar_one_or_none.return_value = None

    response = client.post(
        "/api/v1/search", json={"query": "test"}, headers={"X-API-Key": "invalid_key"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid API key", "error_code": "UNAUTHORIZED"}


@patch("apps.api.app.main.search_service.search")
def test_auth_valid_key(mock_search, mock_db_session):
    """Verify requests succeed with a valid API key."""
    # Mock database to return an active ApiKey record
    mock_key = ApiKey(id="test-key-id", is_active=True, label="Test Key")
    mock_db_session.scalar_one_or_none.return_value = mock_key

    # Mock search service to avoid actual search engine dependency
    mock_search.return_value = []

    response = client.post(
        "/api/v1/search", json={"query": "test"}, headers={"X-API-Key": "valid_key"}
    )
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers


@patch("apps.api.app.main.search_service.search")
def test_rate_limiter_within_limit(mock_search, mock_db_session):
    """Verify rate limiter allows requests under the limit and appends headers."""
    # Mock valid API key
    mock_key = ApiKey(id="test-key-id", is_active=True, label="Test Key")
    mock_db_session.scalar_one_or_none.return_value = mock_key
    mock_search.return_value = []

    # Make request
    response = client.post(
        "/api/v1/search", json={"query": "test"}, headers={"X-API-Key": "valid_key"}
    )
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers
    assert int(response.headers["X-RateLimit-Limit"]) > 0


@pytest.mark.asyncio
@patch("apps.api.app.main.search_service.search")
async def test_rate_limiter_exceeded(mock_search, mock_db_session, mock_redis_global):
    """Verify rate limiter blocks requests exceeding the limit and provides Retry-After header."""
    # Mock valid API key
    mock_key = ApiKey(id="test-key-id", is_active=True, label="Test Key")
    mock_db_session.scalar_one_or_none.return_value = mock_key
    mock_search.return_value = []

    # Configure Redis mock to simulate rate-limit condition using MagicMock pipeline
    mock_pipeline = MagicMock()
    mock_redis_global.pipeline.return_value = mock_pipeline
    mock_pipeline.execute = AsyncMock(
        return_value=[0, 1, 61, True]
    )  # 61 requests in window (limit = 60)

    # Mock Redis zrange to return an oldest request timestamp
    mock_redis_global.zrange.return_value = [("random-uuid", time.time() - 10)]

    response = client.post(
        "/api/v1/search", json={"query": "test"}, headers={"X-API-Key": "valid_key"}
    )
    assert response.status_code == 429
    assert response.headers.get("Retry-After") in (
        "49",
        "50",
    )  # 60s window - 10s age = 50s wait (with potential 1s float diff)
    assert response.json() == {
        "detail": "Too many requests. Please try again later.",
        "error_code": "TOO_MANY_REQUESTS",
    }
