import asyncio
import hashlib
import uuid
from pathlib import Path

import structlog
from fastembed import SparseTextEmbedding
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from packages.rag.chunking import Chunk, chunk_text_hierarchical

logger = structlog.get_logger(__name__)


class IngestionConfig(BaseSettings):
    vector_size: int = 768
    qdrant_url: str = "http://localhost:6333"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    parent_chunk_size: int = 1500
    child_chunk_size: int = 400
    child_chunk_overlap: int = 100

    project_id: str = Field(alias="GCP_PROJECT_ID")
    location: str = Field(alias="GCP_LOCATION", default="global")
    embedding_model_name: str = Field(alias="GCP_EMBEDDING_MODEL", default="gemini-embedding-2")

    gemini_api_key: str | None = Field(alias="GEMINI_API_KEY", default=None)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class Document(BaseModel):
    content: str
    metadata: dict = Field(default_factory=dict)
    path: Path


class IngestionPipeline:
    def __init__(self, config: IngestionConfig | None = None):
        self.config = config or IngestionConfig()
        self.client = AsyncQdrantClient(url=self.config.qdrant_url)

        self.genai_client = genai.Client(
            vertexai=True, project=self.config.project_id, location=self.config.location
        )

        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

    async def list_corpora(self, official_docs_root: Path) -> list[Path]:
        """Lists each directory in official_docs as a separate corpus."""
        return [d for d in official_docs_root.iterdir() if d.is_dir()]

    def get_collection_name(self, corpus_path: Path) -> str:
        """Derives collection name from corpus folder (e.g., fastapi -> kb_fastapi)."""
        return f"kb_{corpus_path.name.lower()}"

    def _parse_metadata_from_path(self, file_path: Path, root_path: Path) -> dict:
        """
        Extracts domain and doc_type from the file path.
        Example: data/raw/official_docs/fastapi/deployment.md
        - category: raw
        - doc_type: official_docs
        - domain: fastapi
        """
        try:
            parts = file_path.parts
            data_index = parts.index("data")
            doc_type = parts[data_index + 2] if len(parts) > data_index + 2 else "unknown"
            domain = parts[data_index + 3] if len(parts) > data_index + 3 else "unknown"
        except ValueError:
            doc_type = "unknown"
            domain = "unknown"

        return {
            "doc_type": doc_type,
            "domain": domain,
        }

    async def load_markdown_files(self, directory: Path) -> list[Document]:
        """Loads all markdown files from a directory."""
        documents = []
        for file_path in directory.glob("**/*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")

                # Extract metadata
                meta = self._parse_metadata_from_path(file_path, directory)
                meta["filename"] = file_path.name

                doc = Document(content=content, path=file_path, metadata=meta)
                documents.append(doc)
            except Exception as e:
                logger.error("ingestion.load_failed", file_path=str(file_path), error=str(e))
        return documents

    async def process_documents(self, documents: list[Document]) -> list[Chunk]:
        """Chunks documents based on configuration."""
        all_chunks = []
        for doc in documents:
            # We will use hierarchical chunking for finer retrieval but larger context mapping
            chunks = chunk_text_hierarchical(
                doc.content,
                source=str(doc.path),
                parent_chunk_size=self.config.parent_chunk_size,
                child_chunk_size=self.config.child_chunk_size,
                child_chunk_overlap=self.config.child_chunk_overlap,
                metadata=doc.metadata,
            )
            all_chunks.extend(chunks)
        return all_chunks

    async def initialize_collection(self, collection_name: str = "enterprise_knowledge"):
        """Creates the global Qdrant collection if it doesn't exist."""
        collections = await self.client.get_collections()
        exists = any(c.name == collection_name for c in collections.collections)

        if not exists:
            logger.info("ingestion.collection.initializing", collection=collection_name)
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=self.config.vector_size, distance=models.Distance.COSINE
                ),
                sparse_vectors_config={"sparse": models.SparseVectorParams()},
            )
            # Create payload indexes for faster filtering
            await self.client.create_payload_index(
                collection_name=collection_name,
                field_name="doc_type",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            await self.client.create_payload_index(
                collection_name=collection_name,
                field_name="domain",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        else:
            logger.info(
                "ingestion.collection.initialized", collection=collection_name, status="exists"
            )

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
            batch = chunks[i : i + batch_size]
            texts = [c.text for c in batch]

            embeddings = await self.get_embeddings(texts)

            sparse_embeddings = list(self.sparse_model.embed(texts))

            points = [
                models.PointStruct(
                    id=self.generate_id(chunk.text, chunk.source),
                    vector={
                        "": embeddings[idx],
                        "sparse": models.SparseVector(
                            indices=sparse_embeddings[idx].indices.tolist(),
                            values=sparse_embeddings[idx].values.tolist(),
                        ),
                    },
                    payload={
                        "text": chunk.text,
                        "parent_text": chunk.parent_text,
                        "source": chunk.source,
                        "filename": Path(chunk.source).name,
                        "chunk_index": chunk.index,
                        "doc_type": chunk.metadata.get("doc_type", "unknown")
                        if hasattr(chunk, "metadata") and chunk.metadata
                        else "unknown",
                        "domain": chunk.metadata.get("domain", "unknown")
                        if hasattr(chunk, "metadata") and chunk.metadata
                        else "unknown",
                    },
                )
                for idx, chunk in enumerate(batch)
            ]

            await self.client.upsert(collection_name=collection_name, points=points)
            logger.info(
                "ingestion.batch.completed",
                collection=collection_name,
                batch_index=i // batch_size + 1,
                batch_size=len(batch),
            )

    async def run(self, data_roots: list[Path]):
        """Executes the full ingestion pipeline for the global knowledge base."""
        logger.info("ingestion.run.started", data_roots=[str(r) for r in data_roots])
        collection_name = "enterprise_knowledge"

        await self.initialize_collection(collection_name)

        corpora = []
        for root in data_roots:
            if root.exists():
                corpora.extend(await self.list_corpora(root))

        logger.info(
            "ingestion.corpora_found", count=len(corpora), domains=[c.name for c in corpora]
        )

        for corpus_path in corpora:
            logger.info("ingestion.domain.started", domain=corpus_path.name)

            docs = await self.load_markdown_files(corpus_path)
            if not docs:
                logger.warning(
                    "ingestion.domain.no_documents", domain=corpus_path.name, path=str(corpus_path)
                )
                continue
            logger.info(
                "ingestion.domain.loaded_documents", domain=corpus_path.name, count=len(docs)
            )

            chunks = await self.process_documents(docs)
            logger.info(
                "ingestion.domain.generated_chunks", domain=corpus_path.name, count=len(chunks)
            )

            await self.upsert_chunks(collection_name, chunks)
            logger.info("ingestion.domain.completed", domain=corpus_path.name)


if __name__ == "__main__":
    from packages.observability import configure_logging

    configure_logging("ingestion", "INFO")
    pipeline = IngestionPipeline()
    raw_dir = Path("data/raw/official_docs/fastapi")
    if raw_dir.exists():
        asyncio.run(pipeline.run([raw_dir]))
    else:
        logger.error("ingestion.run.failed", reason="directory not found", path=str(raw_dir))
