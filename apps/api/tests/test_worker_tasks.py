from unittest.mock import MagicMock, patch

import pytest

from apps.worker.tasks import ingest_document


@patch("apps.worker.tasks._async_ingest")
def test_ingest_document_task_success(mock_async_ingest):
    mock_async_ingest.return_value = {
        "status": "completed",
        "chunks_indexed": 5,
        "source": "test.md",
    }

    mock_self = MagicMock()
    mock_self.request.id = "mock-task-id"
    mock_self.name = "apps.worker.tasks.ingest_document"
    mock_self.request.retries = 0

    result = ingest_document.__wrapped__.__func__(
        mock_self, "test.md", {"domain": "test", "doc_type": "test"}
    )

    assert result["status"] == "completed"
    assert result["chunks_indexed"] == 5
    mock_async_ingest.assert_called_once_with("test.md", {"domain": "test", "doc_type": "test"})


@patch("apps.worker.tasks._async_ingest")
def test_ingest_document_task_failure(mock_async_ingest):
    mock_async_ingest.side_effect = Exception("Mock ingestion failure")

    mock_self = MagicMock()
    mock_self.request.id = "mock-task-id"
    mock_self.name = "apps.worker.tasks.ingest_document"
    mock_self.request.retries = 0

    # Mock self.retry to verify retry behavior
    mock_self.retry.return_value = Exception("Retrying...")

    with pytest.raises(Exception, match="Retrying..."):
        ingest_document.__wrapped__.__func__(
            mock_self, "test.md", {"domain": "test", "doc_type": "test"}
        )

    mock_self.retry.assert_called_once()
