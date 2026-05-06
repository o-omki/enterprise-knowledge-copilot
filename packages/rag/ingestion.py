import asyncio
import hashlib
import logging
import uuid
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from packages.rag.chunking import Chunk, chunk_text

logger = logging.getLogger(__name__)


class IngestionConfig(BaseSettings):
    # gemini-embedding-2 supports output_dimensionality. Recommended: 768, 1536, 3072.
    vector_size: int = 768
    qdrant_url: str = "http://localhost:6333"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # GCP Settings
    project_id: str = Field(alias="GCP_PROJECT_ID")
    location: str = Field(alias="GCP_LOCATION", default="global")
    embedding_model_name: str = Field(
        alias="GCP_EMBEDDING_MODEL", default="gemini-embedding-2")

    # AI Studio setting (optional)
    gemini_api_key: str | None = Field(alias="GEMINI_API_KEY", default=None)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    print("IngestionConfig loaded with:embedding_model_name =", embedding_model_name)


class Document(BaseModel):
    content: str
    metadata: dict = Field(default_factory=dict)
    path: Path


class IngestionPipeline:
    def __init__(self, config: IngestionConfig | None = None):
        self.config = config or IngestionConfig()
        self.client = AsyncQdrantClient(url=self.config.qdrant_url)

        print(
            f"model and location from config: {self.config.embedding_model_name}, {self.config.location}\n\n\n\n\n")

        # Initialize the new Google Gen AI SDK for Vertex AI
        self.genai_client = genai.Client(
            vertexai=True, project=self.config.project_id, location=self.config.location
        )
        print(
            f"GenAI Client initialized for model = {self.config.embedding_model_name}\n\n\n\n\n")

    async def list_corpora(self, official_docs_root: Path) -> list[Path]:
        """Lists each directory in official_docs as a separate corpus."""
        return [d for d in official_docs_root.iterdir() if d.is_dir()]

    def get_collection_name(self, corpus_path: Path) -> str:
        """Derives collection name from corpus folder (e.g., fastapi -> kb_fastapi)."""
        return f"kb_{corpus_path.name.lower()}"

    async def load_markdown_files(self, directory: Path) -> list[Document]:
        """Loads all markdown files from a directory."""
        documents = []
        for file_path in directory.glob("**/*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")
                doc = Document(
                    content=content, path=file_path, metadata={
                        "filename": file_path.name}
                )
                documents.append(doc)
            except Exception as e:
                logger.error(f"Failed to read file: {file_path}. Error: {e}")
        return documents

    async def process_documents(self, documents: list[Document]) -> list[Chunk]:
        """Chunks documents based on configuration."""
        all_chunks = []
        for doc in documents:
            chunks = chunk_text(
                doc.content, source=str(doc.path), chunk_size=self.config.chunk_size, chunk_overlap=self.config.chunk_overlap
            )
            all_chunks.extend(chunks)
        return all_chunks

    async def initialize_collection(self, collection_name: str):
        """Creates a Qdrant collection if it doesn't exist."""
        collections = await self.client.get_collections()
        exists = any(
            c.name == collection_name for c in collections.collections)

        if not exists:
            logger.info(f"Creating collection: {collection_name}")
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=self.config.vector_size, distance=models.Distance.COSINE
                ),
            )
        else:
            logger.info(f"Collection {collection_name} already exists.")

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        semaphore = asyncio.Semaphore(8)

        async def embed_one(text: str) -> list[float]:
            async with semaphore:
                response = await self.genai_client.aio.models.embed_content(
                    model=self.config.embedding_model_name,
                    contents=f"task: search result | text: {text}",
                    config=types.EmbedContentConfig(
                        output_dimensionality=self.config.vector_size,
                    ),
                )

                embedding = response.embeddings[0].values

                if len(embedding) != self.config.vector_size:
                    raise ValueError(
                        f"Embedding dimension mismatch: got {len(embedding)}, "
                        f"expected {self.config.vector_size}"
                    )

                return embedding

        return await asyncio.gather(*(embed_one(text) for text in texts))

    def generate_id(self, text: str, source: str) -> str:
        """Creates a deterministic UUID based on content and source."""
        hash_input = f"{source}_{text}"
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, hashlib.sha256(hash_input.encode()).hexdigest()))

    async def upsert_chunks(self, collection_name: str, chunks: list[Chunk]):
        """Embeds and uploads chunks to Qdrant."""
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i: i + batch_size]
            texts = [c.text for c in batch]

            # Get embeddings
            embeddings = await self.get_embeddings(texts)

            points = [
                models.PointStruct(
                    id=self.generate_id(chunk.text, chunk.source),
                    vector=embeddings[idx],
                    payload={
                        "text": chunk.text,
                        "source": chunk.source,
                        "filename": Path(chunk.source).name,
                        "chunk_index": chunk.index,
                        "corpus": collection_name,
                    }
                )
                for idx, chunk in enumerate(batch)
            ]

            await self.client.upsert(collection_name=collection_name, points=points)
            logger.info(
                f"Upserted batch {i // batch_size + 1} into {collection_name}")

    async def run(self, raw_docs_root: Path):
        """Executes the full ingestion pipeline for all corpora."""
        logger.info(f"Starting ingestion from {raw_docs_root}")

        corpora = await self.list_corpora(raw_docs_root)
        logger.info(
            f"Found {len(corpora)} corpora: {[c.name for c in corpora]}")

        for corpus_path in corpora:
            collection_name = self.get_collection_name(corpus_path)
            logger.info(
                f"Processing corpus: {corpus_path.name} -> {collection_name}")

            # 1. Load documents
            docs = await self.load_markdown_files(corpus_path)
            if not docs:
                logger.warning(f"No documents found in {corpus_path}")
                continue
            logger.info(
                f"Loaded {len(docs)} documents from {corpus_path.name}.")

            # 2. Chunk documents
            chunks = await self.process_documents(docs)
            logger.info(
                f"Generated {len(chunks)} chunks for {corpus_path.name}.")

            # 3. Initialize Qdrant collection
            await self.initialize_collection(collection_name)

            # 4. Embed and Upsert
            await self.upsert_chunks(collection_name, chunks)
            logger.info(f"Completed ingestion for {corpus_path.name}.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pipeline = IngestionPipeline()
    raw_dir = Path("data/raw/official_docs/fastapi")
    if raw_dir.exists():
        asyncio.run(pipeline.run(raw_dir))
    else:
        logger.error(f"Directory {raw_dir} not found.")
