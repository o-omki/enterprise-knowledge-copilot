import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from apps.api.app.middleware.request_context import RequestContextMiddleware


@pytest.fixture
def app():
    fastapi_app = FastAPI()
    fastapi_app.add_middleware(RequestContextMiddleware)

    @fastapi_app.get("/test")
    async def get_test(request: Request):
        return {
            "request_id": getattr(request.state, "request_id", None),
            "session_id": getattr(request.state, "session_id", None),
        }

    @fastapi_app.post("/api/v1/ask")
    async def post_ask(request: Request):
        # Read request body to ensure body is readable downstream
        body = await request.json()
        return {
            "request_id": getattr(request.state, "request_id", None),
            "session_id": getattr(request.state, "session_id", None),
            "body_query": body.get("query"),
        }

    return fastapi_app


def test_request_context_middleware_generates_id(app):
    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200

    # Check that a correlation ID is generated and returned as header
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert request_id is not None

    # Check that request state contains the same ID
    data = response.json()
    assert data["request_id"] == request_id
    assert data["session_id"] == "none"


def test_request_context_middleware_propagates_id(app):
    client = TestClient(app)
    custom_id = "test-custom-request-id-123"
    response = client.get("/test", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200

    assert response.headers["X-Request-ID"] == custom_id
    data = response.json()
    assert data["request_id"] == custom_id


def test_request_context_middleware_parses_session_id(app):
    client = TestClient(app)
    payload = {"query": "What is enterprise RAG?", "session_id": "session-xyz-456"}
    response = client.post("/api/v1/ask", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["session_id"] == "session-xyz-456"
    assert data["body_query"] == "What is enterprise RAG?"
