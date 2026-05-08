from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    source: str
    index: int
    metadata: dict = field(default_factory=dict)


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
