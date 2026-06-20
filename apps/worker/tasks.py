import asyncio
from pathlib import Path

import structlog
from celery import shared_task
from celery.signals import worker_process_init

from packages.observability import configure_logging, setup_tracing
from packages.observability.metrics import (
    ingestion_chunk_count,
    ingestion_duration,
    ingestion_total,
)
from packages.rag.ingestion import Document, IngestionPipeline

logger = structlog.get_logger(__name__)


@worker_process_init.connect(weak=False)
def init_worker_process(*args, **kwargs):
    import os

    configure_logging("worker", os.getenv("LOG_LEVEL", "INFO"))
    setup_tracing(service_name="worker")


async def _async_ingest(file_path_str: str, metadata: dict) -> dict:
    file_path = Path(file_path_str)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path_str}")

    suffix = file_path.suffix.lower()
    if suffix not in (".md", ".txt"):
        raise ValueError(f"Unsupported file format: {suffix}. Only .md and .txt are supported.")

    content = file_path.read_text(encoding="utf-8")

    doc_metadata = {
        "doc_type": metadata.get("doc_type", "unknown"),
        "domain": metadata.get("domain", "unknown"),
        "filename": file_path.name,
    }

    doc = Document(
        content=content,
        path=file_path,
        metadata=doc_metadata,
    )

    pipeline = IngestionPipeline()
    collection_name = "enterprise_knowledge"

    await pipeline.initialize_collection(collection_name)
    chunks = await pipeline.process_documents([doc])

    if chunks:
        await pipeline.upsert_chunks(collection_name, chunks)

    return {
        "status": "completed",
        "chunks_indexed": len(chunks),
        "source": file_path.name,
    }


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def ingest_document(self, file_path: str, metadata: dict) -> dict:
    """Ingest a single document into the Qdrant knowledge base.

    This runs the async pipeline using asyncio.run.
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        task_id=self.request.id,
        task_name=self.name,
        file_path=file_path,
    )

    import time

    start_time = time.perf_counter()
    logger.info("worker.ingest.started", metadata=metadata)
    try:
        result = asyncio.run(_async_ingest(file_path, metadata))
        duration = time.perf_counter() - start_time
        ingestion_duration.record(duration, {})
        ingestion_total.add(1, {"status": "completed"})

        chunks_count = result.get("chunks_indexed", 0)
        if chunks_count > 0:
            ingestion_chunk_count.add(chunks_count, {})

        logger.info(
            "worker.ingest.completed",
            chunks_indexed=chunks_count,
        )
        return result
    except Exception as e:
        duration = time.perf_counter() - start_time
        ingestion_duration.record(duration, {})
        ingestion_total.add(1, {"status": "failed"})

        logger.error(
            "worker.ingest.failed",
            error=str(e),
            retry_count=self.request.retries,
            exc_info=True,
        )
        raise self.retry(exc=e)
    finally:
        structlog.contextvars.clear_contextvars()
