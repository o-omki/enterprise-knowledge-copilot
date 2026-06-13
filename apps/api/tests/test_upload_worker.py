from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app

# Reset the middleware stack to force FastAPI to rebuild it.
# This prevents cached bound mock methods from other test files from leaking.
app.middleware_stack = None

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_middleware_stack():
    """
    Forces FastAPI to rebuild the middleware stack to clear cached mocks from other test files.
    """

    app.middleware_stack = None
    yield
    app.middleware_stack = None


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


@patch("apps.api.app.main.ingest_document")
def test_upload_document_success(mock_ingest_document, tmp_path):
    # Setup mock task
    mock_task = MagicMock()
    mock_task.id = "mock-job-id"
    mock_ingest_document.delay.return_value = mock_task

    # Prepare file data
    test_file_content = b"# Test Document\nSome content."
    files = {"file": ("test.md", test_file_content, "text/markdown")}
    data = {"domain": "fastapi", "doc_type": "official_docs"}

    # Execute request
    response = client.post("/api/v1/upload", data=data, files=files)

    assert response.status_code == 202
    res_data = response.json()
    assert res_data["job_id"] == "mock-job-id"
    assert res_data["status"] == "queued"
    assert "ingestion successfully queued" in res_data["message"]

    # Verify task was dispatched
    mock_ingest_document.delay.assert_called_once()
    args, kwargs = mock_ingest_document.delay.call_args
    assert "test.md" in args[0]
    assert args[1] == {"domain": "fastapi", "doc_type": "official_docs"}


def test_upload_document_invalid_extension():
    # Attempt uploading PNG file
    files = {"file": ("test.png", b"fake image content", "image/png")}
    data = {"domain": "fastapi", "doc_type": "official_docs"}

    response = client.post("/api/v1/upload", data=data, files=files)

    assert response.status_code == 400
    res_data = response.json()
    assert "Only .md and .txt files are supported" in res_data["detail"]


@patch("apps.api.app.main.AsyncResult")
def test_get_job_status_queued(mock_async_result):
    mock_res = MagicMock()
    mock_res.state = "PENDING"
    mock_async_result.return_value = mock_res

    response = client.get("/api/v1/jobs/mock-job-id")

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["job_id"] == "mock-job-id"
    assert res_data["status"] == "queued"
    assert res_data["result"] is None
    assert res_data["error"] is None


@patch("apps.api.app.main.AsyncResult")
def test_get_job_status_processing(mock_async_result):
    mock_res = MagicMock()
    mock_res.state = "STARTED"
    mock_async_result.return_value = mock_res

    response = client.get("/api/v1/jobs/mock-job-id")

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["job_id"] == "mock-job-id"
    assert res_data["status"] == "processing"
    assert res_data["result"] is None
    assert res_data["error"] is None


@patch("apps.api.app.main.AsyncResult")
def test_get_job_status_completed(mock_async_result):
    mock_res = MagicMock()
    mock_res.state = "SUCCESS"
    mock_res.result = {"chunks_indexed": 3, "source": "test.md"}
    mock_async_result.return_value = mock_res

    response = client.get("/api/v1/jobs/mock-job-id")

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["job_id"] == "mock-job-id"
    assert res_data["status"] == "completed"
    assert res_data["result"] == {"chunks_indexed": 3, "source": "test.md"}
    assert res_data["error"] is None


@patch("apps.api.app.main.AsyncResult")
def test_get_job_status_failed(mock_async_result):
    mock_res = MagicMock()
    mock_res.state = "FAILURE"
    mock_res.result = Exception("Mock parsing error")
    mock_async_result.return_value = mock_res

    response = client.get("/api/v1/jobs/mock-job-id")

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["job_id"] == "mock-job-id"
    assert res_data["status"] == "failed"
    assert res_data["result"] is None
    assert "Mock parsing error" in res_data["error"]
