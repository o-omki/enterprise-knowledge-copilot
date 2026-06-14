import asyncio
from pathlib import Path

from celery import shared_task
from celery.utils.log import get_task_logger

from packages.rag.ingestion import Document, IngestionPipeline

logger = get_task_logger(__name__)


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
    logger.info(f"Ingesting file {file_path} with metadata: {metadata}")
    try:
        result = asyncio.run(_async_ingest(file_path, metadata))
        logger.info(f"Successfully completed ingestion for {file_path}. Result: {result}")
        return result
    except Exception as e:
        logger.exception(f"Error occurred during ingestion of {file_path}: {e}")
        raise self.retry(exc=e)
