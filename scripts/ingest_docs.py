import asyncio
import logging
from pathlib import Path

from packages.rag.ingestion import IngestionPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # Root directory for official documentation
    raw_docs_root = Path("data/raw/official_docs")

    pipeline = IngestionPipeline()
    await pipeline.run(raw_docs_root)


if __name__ == "__main__":
    asyncio.run(main())
