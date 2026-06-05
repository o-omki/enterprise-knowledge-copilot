from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.app.main import app
from packages.rag.generation import AnswerResponse
from packages.rag.search import SearchResult

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("apps.api.app.main.search_service.search")
def test_search_endpoint(mock_search):
    # Mock return value for search_service.search
    mock_search.return_value = [SearchResult(text="test content", source="test.md", score=0.9)]

    # Test valid request
    response = client.get("/search?q=what is fastapi")
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
    response = client.get("/search?q=what is fastapi&rerank=true")
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
    response = client.get("/ask?q=what is fastapi")
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
    )


def test_search_missing_query():
    response = client.get("/search")
    # FastAPI/Pydantic validation error for missing query param 'q'
    assert response.status_code == 422
