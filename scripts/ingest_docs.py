import asyncio
import logging
from pathlib import Path

from packages.rag.ingestion import IngestionPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # Root directories for documentation
    data_roots = [Path("data/raw"), Path("data/synthetic")]

    pipeline = IngestionPipeline()
    await pipeline.run(data_roots)


if __name__ == "__main__":
    asyncio.run(main())
