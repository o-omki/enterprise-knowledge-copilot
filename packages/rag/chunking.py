from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    source: str
    index: int
    metadata: dict = field(default_factory=dict)
    parent_text: str | None = None


def chunk_text(
    text: str, source: str, chunk_size: int = 800, chunk_overlap: int = 0, metadata: dict = None
) -> list[Chunk]:
    if metadata is None:
        metadata = {}

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    step = chunk_size - chunk_overlap

    while start < len(text):
        end = start + chunk_size
        chunks.append(
            Chunk(text=text[start:end], source=source, index=idx, metadata=metadata.copy())
        )
        start += step
        idx += 1
    return chunks


def chunk_text_hierarchical(
    text: str,
    source: str,
    parent_chunk_size: int = 1500,
    child_chunk_size: int = 400,
    child_chunk_overlap: int = 100,
    metadata: dict = None,
) -> list[Chunk]:
    if metadata is None:
        metadata = {}

    child_chunks = chunk_text(
        text=text,
        source=source,
        chunk_size=child_chunk_size,
        chunk_overlap=child_chunk_overlap,
        metadata=metadata,
    )

    child_step = child_chunk_size - child_chunk_overlap

    for c_chunk in child_chunks:
        child_start = c_chunk.index * child_step

        total_padding = parent_chunk_size - child_chunk_size
        left_padding = total_padding // 2

        parent_start = max(0, child_start - left_padding)
        parent_end = min(len(text), parent_start + parent_chunk_size)

        if parent_end == len(text):
            parent_start = max(0, parent_end - parent_chunk_size)

        c_chunk.parent_text = text[parent_start:parent_end]

    return child_chunks
