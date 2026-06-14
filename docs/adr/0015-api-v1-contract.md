# ADR 0015: API v1 Contract

**Status:** Accepted
**Date:** 2026-06-09

## Context and Problem Statement
With the addition of advanced session tracking, async document ingestion via Celery, and more robust querying (such as reranking and tracing), we need to solidify the API contract for the version 1 release of the Enterprise Knowledge Copilot. The API needs to serve both standard REST clients (like the frontend web application) and potential programmatic usage via scripts or third-party integrations.

## Decision
We will finalize the API contract under the `/api/v1` namespace with the following core endpoints:

1. **`POST /api/v1/search`**
   - **Purpose**: A global retrieval endpoint that performs dense/sparse/hybrid search with optional cross-encoder reranking.
   - **Request**: Accepts `SearchRequest` containing query, domain, doc_type, limit, method, and rerank flag.
   - **Response**: Returns `SearchResponse` containing the original query and a list of retrieved document chunks.

2. **`POST /api/v1/ask`**
   - **Purpose**: Primary conversational endpoint. Processes a query using the full RAG pipeline, maintains conversation history if a `session_id` is provided, and returns an answer along with citations.
   - **Request**: Accepts `AskRequest` (query, domain, doc_type, limit, method, rerank, stream, session_id).
   - **Response**: Returns `AskResponse` (answer, citations, metadata including trace_id). Streaming support will be implemented via Server-Sent Events (SSE) when `stream=True` is fully integrated.

3. **`GET /api/v1/sessions`**
   - **Purpose**: Lists all active sessions for the authenticated user or API key.
   - **Response**: Returns a list of `SessionResponse` objects ordered by last active time.

4. **`GET /api/v1/sessions/{session_id}/messages`**
   - **Purpose**: Retrieves the message history for a specific session.
   - **Response**: Returns a list of `MessageResponse` objects.

5. **`POST /api/v1/upload`**
   - **Purpose**: Async document ingestion endpoint. Accepts a file upload (`.md` or `.txt`) and queues it for processing via a Celery worker.
   - **Request**: Form data with `domain`, `doc_type`, and the `file`.
   - **Response**: Returns a 202 Accepted `UploadResponse` containing a `job_id`.

6. **`GET /api/v1/jobs/{job_id}`**
   - **Purpose**: Status checking for background tasks (e.g., document ingestion).
   - **Response**: Returns `JobStatusResponse` indicating whether the task is queued, processing, completed, or failed.

## Consequences

### Positive
- **Standardization**: Provides a clear, versioned contract (`/api/v1`) that frontend and external integrators can rely on.
- **Asynchronous Processing**: The upload endpoint defers heavy ingestion tasks to Celery, keeping the main API responsive and preventing timeouts on large files.
- **Session Management**: Native tracking of sessions and message history simplifies frontend state management and supports continuous conversations.

### Negative
- **Complexity**: Requires maintaining Celery workers and Redis for the ingestion pipeline.
- **Breaking Changes**: Moving existing endpoints to the `/api/v1` prefix requires updating any legacy consumer scripts, frontend components, and evaluation runners.

## Compliance and Security
- All endpoints are protected by `MultiAuthMiddleware`, requiring either a valid user session or API key.
- Endpoints are shielded by `RateLimiterMiddleware` and `SafetyGuardrailsMiddleware` to prevent abuse and ensure safe model outputs.
