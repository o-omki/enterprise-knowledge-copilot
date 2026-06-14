from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app
from packages.rag.generation import AnswerResponse
from packages.rag.search import SearchResult

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_gateway_middlewares():
    """Bypasses auth and rate limit middlewares for core API functional tests."""
    with (
        patch("apps.api.app.middleware.auth.MultiAuthMiddleware.dispatch") as mock_auth,
        patch(
            "apps.api.app.middleware.rate_limiter.RateLimiterMiddleware.dispatch"
        ) as mock_limiter,
    ):

        async def mock_auth_dispatch(request, call_next):
            request.state.api_key_id = "test-key-id"
            return await call_next(request)

        async def mock_limiter_dispatch(request, call_next):
            return await call_next(request)

        mock_auth.side_effect = mock_auth_dispatch
        mock_limiter.side_effect = mock_limiter_dispatch
        yield


@pytest.fixture(autouse=True)
def mock_db_session():
    """Fixture to mock database session and query results."""
    with patch("apps.api.app.main.async_session_maker") as mock_maker:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_session.execute.return_value = mock_result

        # Mock scalar_one_or_none and scalar_one methods
        mock_scalar_one = MagicMock()
        mock_scalar_one.id = "mock-session-id"
        mock_scalar_one.user_id = None
        mock_scalar_one.api_key_id = "test-key-id"

        mock_result.scalar_one_or_none.return_value = mock_scalar_one
        mock_result.scalar_one.return_value = mock_scalar_one

        mock_maker.return_value.__aenter__.return_value = mock_session
        yield mock_session


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("apps.api.app.main.search_service.search")
def test_search_endpoint(mock_search):
    # Mock return value for search_service.search
    mock_search.return_value = [SearchResult(text="test content", source="test.md", score=0.9)]

    # Test valid request
    response = client.post("/api/v1/search", json={"query": "what is fastapi"})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "what is fastapi"
    assert len(data["results"]) == 1
    assert data["results"][0]["text"] == "test content"

    # Verify mock call
    mock_search.assert_called_once_with(
        query="what is fastapi",
        limit=5,
        domain=None,
        doc_type=None,
        method="dense",
    )


@patch("apps.api.app.main.reranker_service.arerank")
@patch("apps.api.app.main.search_service.search")
def test_search_with_reranking(mock_search, mock_rerank):
    # Mock return values
    mock_search.return_value = [SearchResult(text="test content", source="test.md", score=0.9)]
    mock_rerank.return_value = [SearchResult(text="test content", source="test.md", score=0.95)]

    # Test request with rerank=true
    response = client.post("/api/v1/search", json={"query": "what is fastapi", "rerank": True})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "what is fastapi"
    assert len(data["results"]) == 1

    # Verify mock calls: limit * 2 when rerank=True
    mock_search.assert_called_once_with(
        query="what is fastapi",
        limit=10,
        domain=None,
        doc_type=None,
        method="dense",
    )
    mock_rerank.assert_called_once()


@patch("apps.api.app.main.orchestrator.answer_query")
def test_ask_endpoint(mock_answer_query):
    # Mock return value for orchestrator.answer_query
    mock_answer_query.return_value = AnswerResponse(
        answer="FastAPI is a modern web framework.",
        citations=[],
        context_passages=["FastAPI is cool."],
    )

    # Test ask request
    response = client.post("/api/v1/ask", json={"query": "what is fastapi"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "FastAPI is a modern web framework."

    # Verify mock call
    mock_answer_query.assert_called_once_with(
        query="what is fastapi",
        domain=None,
        doc_type=None,
        limit=5,
        method="dense",
        rerank=False,
        chat_history=[],
    )


def test_search_missing_query():
    response = client.post("/api/v1/search", json={})
    # FastAPI/Pydantic validation error for missing body field 'query'
    assert response.status_code == 422
