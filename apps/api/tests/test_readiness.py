from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app


@pytest.fixture
def mock_dependencies():
    with (
        patch("apps.api.app.main.redis_client") as mock_redis,
        patch("apps.api.app.main.search_service") as mock_search,
        patch("apps.api.app.main.engine") as mock_engine,
        patch("httpx.AsyncClient.get") as mock_http_get,
    ):
        # Configure mock_redis
        mock_redis.ping = AsyncMock(return_value=True)

        # Configure mock_search config
        mock_search.config = MagicMock()
        mock_search.config.qdrant_url = "http://localhost:6333"

        # Configure mock_engine
        mock_connection = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_connection
        mock_connection.execute = AsyncMock()

        # Configure mock_http_get for Qdrant healthz
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_http_get.return_value = mock_resp

        yield {
            "redis": mock_redis,
            "search": mock_search,
            "engine": mock_engine,
            "http_get": mock_http_get,
        }


def test_readiness_healthy(mock_dependencies):
    # Ensure shutting_down is False
    app.state.shutting_down = False

    client = TestClient(app)
    response = client.get("/readiness")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["redis"] == "healthy"
    assert data["qdrant"] == "healthy"
    assert data["database"] == "healthy"


def test_readiness_redis_down(mock_dependencies):
    app.state.shutting_down = False
    mock_dependencies["redis"].ping.side_effect = Exception("Redis connection refused")

    client = TestClient(app)
    response = client.get("/readiness")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "unhealthy" in data["redis"]
    assert data["qdrant"] == "healthy"
    assert data["database"] == "healthy"


def test_readiness_qdrant_down(mock_dependencies):
    app.state.shutting_down = False
    mock_dependencies["http_get"].side_effect = Exception("Qdrant connection timeout")

    client = TestClient(app)
    response = client.get("/readiness")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["redis"] == "healthy"
    assert "unhealthy" in data["qdrant"]
    assert data["database"] == "healthy"


def test_readiness_qdrant_status_not_200(mock_dependencies):
    app.state.shutting_down = False
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_dependencies["http_get"].return_value = mock_resp

    client = TestClient(app)
    response = client.get("/readiness")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["redis"] == "healthy"
    assert "unhealthy: HTTP 500" in data["qdrant"]
    assert data["database"] == "healthy"


def test_readiness_database_down(mock_dependencies):
    app.state.shutting_down = False
    mock_dependencies["engine"].connect.side_effect = Exception("DB connection pool exhausted")

    client = TestClient(app)
    response = client.get("/readiness")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["redis"] == "healthy"
    assert data["qdrant"] == "healthy"
    assert "unhealthy" in data["database"]


def test_readiness_shutting_down(mock_dependencies):
    app.state.shutting_down = True

    client = TestClient(app)
    response = client.get("/readiness")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "shutting_down"
    assert data["redis"] == "healthy"
    assert data["qdrant"] == "healthy"
    assert data["database"] == "healthy"
