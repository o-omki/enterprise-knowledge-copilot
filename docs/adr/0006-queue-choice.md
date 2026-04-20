# ADR 0006: Message Queue Choice

## Status
Proposed

## Context
The system requires an asynchronous messaging layer for ingestion jobs, background indexing, and potentially evaluation tasks.

## Decision
We will use **Redis (Pub/Sub or Streams)** as the message broker for Phase 1, with a path to migrate to **Google Cloud Pub/Sub** for production scale on GCP.

## Rationale
- **Simplicity:** Redis is lightweight and already likely to be used for caching or session management. It is easy to run in the local Docker Compose stack.
- **GCP Integration:** Cloud Pub/Sub is the native GCP serverless messaging solution, reducing operational overhead in production.
- **Scalability:** Google Cloud Pub/Sub provides massive scale for ingestion pipelines.

## Alternatives Considered
- **RabbitMQ:** Highly reliable but adds significant complexity to the local dev stack.
- **Kafka:** Overkill for the current scale and adds heavy operational burden.

## Consequences
- Local development will require a Redis container.
- Background worker (app/worker) will need a lightweight task consumer (e.g., Celery, RQ, or a custom Python stream consumer).
